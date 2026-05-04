import uvicorn
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qualifier_agent import RealtorQualifierAgent
from database import (
    init_db, upsert_lead, save_message, get_lead,
    get_all_leads, get_all_qualified_leads, get_lead_stats,
    get_conversation_transcript, mark_notification_sent
)
from notifications import send_qualified_lead_notification

# Load .env file if present (for local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Session Store ────────────────────────────────────────────────────────────
# Per-session state: each user gets their own agent + conversation history
sessions: dict[str, dict] = {}
SESSION_TTL = 3600  # 1 hour timeout for idle sessions

def get_or_create_session(session_id: str) -> dict:
    """Get existing session or create a new one."""
    if session_id not in sessions:
        sessions[session_id] = {
            "agent": RealtorQualifierAgent(agent_id=f"realtor_{session_id}"),
            "history": [],
            "extracted_data": {},
            "last_active": time.time()
        }
    sessions[session_id]["last_active"] = time.time()
    return sessions[session_id]

def cleanup_stale_sessions():
    """Remove sessions that have been idle for longer than TTL."""
    now = time.time()
    stale = [sid for sid, s in sessions.items() if now - s["last_active"] > SESSION_TTL]
    for sid in stale:
        del sessions[sid]

# ─── Rate Limiting ────────────────────────────────────────────────────────────
rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_MAX = 15  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

def check_rate_limit(client_ip: str) -> bool:
    """Returns True if the client is within rate limits."""
    now = time.time()
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    # Prune old timestamps
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return False
    rate_limit_store[client_ip].append(now)
    return True

# ─── App Setup ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing deprecated @app.on_event."""
    print("AETHER Realtor Prototype Server starting...")
    # Initialize database
    init_db()
    # Validate that we can create an agent (checks imports, API key, etc.)
    try:
        test_agent = RealtorQualifierAgent(agent_id="startup_test")
        print(f"Agent validation passed. WIT schema compiled successfully.")
        del test_agent
    except Exception as e:
        print(f"⚠️  Agent validation failed: {e}")
        print("Server will start but chat requests may fail.")
    yield
    # Cleanup on shutdown
    sessions.clear()
    print("Server shutdown complete. Sessions cleared.")

app = FastAPI(title="Lake Region Realtor Agent API", lifespan=lifespan)

# Setup CORS — restricted to known origins
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
# Allow file:// protocol and any origin for dev mode
if os.environ.get("AETHER_DEV_MODE", "true").lower() == "true":
    ALLOWED_ORIGINS.append("*")

# Add production frontend URL if set
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ─── Request / Response Models ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str = Field(default="default", max_length=50)
    message: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    reply: str
    extracted_data: dict = {}
    is_qualified: bool = False

# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, req: Request):
    # Rate limit check
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    # Cleanup stale sessions periodically
    cleanup_stale_sessions()

    try:
        # Get or create session
        session = get_or_create_session(request.session_id)
        agent = session["agent"]

        # Build the task input dict that execute() expects
        task_input = {
            "message": request.message,
            "history": session["history"]
        }

        # Execute the agent
        result = await agent.execute(task_input)

        # Update in-memory conversation history
        session["history"].append(f"User: {request.message}")
        session["history"].append(f"Agent: {result['output']}")

        # ─── Persist to database ─────────────────────────────────────────
        save_message(request.session_id, "user", request.message)
        save_message(request.session_id, "agent", result["output"])

        # Store and persist extracted data
        extracted = result.get("extracted_data", {})
        session["extracted_data"] = extracted

        if extracted:
            lead = upsert_lead(request.session_id, extracted)

            # ─── Trigger notification if newly qualified ─────────────────
            if (extracted.get("is_qualified", False)
                    and lead.get("notification_sent", 0) == 0):
                transcript = get_conversation_transcript(request.session_id)
                notification_data = {**extracted, "session_id": request.session_id}
                sent = send_qualified_lead_notification(notification_data, transcript)
                if sent:
                    mark_notification_sent(request.session_id)
                    print(f"🔥 Qualified lead! Notification sent for session {request.session_id}")
                else:
                    print(f"🔥 Qualified lead! (notification not configured)")

        return ChatResponse(
            reply=result["output"],
            extracted_data=extracted,
            is_qualified=extracted.get("is_qualified", False)
        )
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            reply="I apologize for the hiccup. Could you try that again?",
            extracted_data={},
            is_qualified=False
        )

@app.post("/reset")
async def reset_session(request: dict):
    """Reset a session to start a fresh conversation."""
    session_id = request.get("session_id", "default")
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "ok", "message": "Session reset successfully."}

@app.get("/health")
async def health_check():
    stats = get_lead_stats()
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        **stats
    }

@app.get("/leads")
async def list_leads(qualified_only: bool = False):
    """Get all leads (for future dashboard)."""
    if qualified_only:
        leads = get_all_qualified_leads()
    else:
        leads = get_all_leads()
    return {"leads": leads, "count": len(leads)}

@app.get("/leads/stats")
async def lead_stats():
    """Get funnel stats."""
    return get_lead_stats()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting AETHER Realtor Server on port {port}...")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)
