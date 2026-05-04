"""
SQLite persistence layer for leads and conversations.
Zero-config, file-based — perfect for MVP, migrates cleanly to Postgres later.
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "lake_region_leads.db")

# Whitelist of valid lead columns to prevent SQL injection from AI-extracted keys
VALID_LEAD_COLUMNS = {"intent", "timeline", "budget", "contact", "is_qualified"}

def get_connection():
    """Get a thread-safe SQLite connection as a context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    return conn

def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                intent TEXT DEFAULT 'unknown',
                timeline TEXT DEFAULT 'unknown',
                budget TEXT DEFAULT 'unknown',
                contact TEXT DEFAULT 'unknown',
                is_qualified BOOLEAN DEFAULT 0,
                notification_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_leads_session ON leads(session_id);
            CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads(is_qualified);
            CREATE INDEX IF NOT EXISTS idx_convos_session ON conversations(session_id);
        """)
        conn.commit()
    print(f"Database initialized at {DB_PATH}")

# ─── Lead Operations ──────────────────────────────────────────────────────────

def upsert_lead(session_id: str, extracted_data: dict) -> dict:
    """
    Insert or update a lead based on session_id.
    Only updates fields that have a non-'unknown' value.
    Returns the current lead state.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check if lead exists
        cursor.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,))
        existing = cursor.fetchone()

        intent = extracted_data.get("intent", "unknown")
        timeline = extracted_data.get("timeline", "unknown")
        budget = extracted_data.get("budget", "unknown")
        contact = extracted_data.get("contact", "unknown")
        is_qualified = extracted_data.get("is_qualified", False)

        if existing:
            # Only update fields that are better than what we have
            updates = {}
            if intent != "unknown":
                updates["intent"] = intent
            if timeline != "unknown":
                updates["timeline"] = timeline
            if budget != "unknown":
                updates["budget"] = budget
            if contact != "unknown":
                updates["contact"] = contact
            if is_qualified:
                updates["is_qualified"] = 1

            if updates:
                # Validate column names against whitelist to prevent SQL injection
                safe_updates = {k: v for k, v in updates.items() if k in VALID_LEAD_COLUMNS}
                safe_updates["updated_at"] = datetime.now().isoformat()
                set_clause = ", ".join(f"{k} = ?" for k in safe_updates.keys())
                values = list(safe_updates.values()) + [session_id]
                cursor.execute(
                    f"UPDATE leads SET {set_clause} WHERE session_id = ?",
                    values
                )
                conn.commit()
        else:
            cursor.execute(
                """INSERT INTO leads (session_id, intent, timeline, budget, contact, is_qualified)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, intent, timeline, budget, contact, int(is_qualified))
            )
            conn.commit()

        # Fetch and return current state
        cursor.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,))
        lead = cursor.fetchone()

    return dict(lead) if lead else {}

def mark_notification_sent(session_id: str):
    """Mark that we've already emailed the realtor about this lead."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE leads SET notification_sent = 1 WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()

def get_lead(session_id: str) -> dict:
    """Get a lead by session_id."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
    return dict(row) if row else {}

def get_all_qualified_leads() -> list[dict]:
    """Get all qualified leads, newest first."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM leads WHERE is_qualified = 1 ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

def get_all_leads() -> list[dict]:
    """Get all leads, newest first."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM leads ORDER BY created_at DESC")
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

def get_lead_stats() -> dict:
    """Get funnel stats for the dashboard."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        qualified = conn.execute("SELECT COUNT(*) FROM leads WHERE is_qualified = 1").fetchone()[0]
    return {
        "total_leads": total,
        "qualified_leads": qualified,
        "qualification_rate": round((qualified / total * 100), 1) if total > 0 else 0
    }

# ─── Conversation Operations ─────────────────────────────────────────────────

def save_message(session_id: str, role: str, message: str):
    """Save a single conversation message."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, message) VALUES (?, ?, ?)",
            (session_id, role, message)
        )
        conn.commit()

def get_conversation(session_id: str) -> list[dict]:
    """Get the full conversation history for a session."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT role, message, created_at FROM conversations WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

def get_conversation_transcript(session_id: str) -> str:
    """Get conversation as a formatted text transcript."""
    messages = get_conversation(session_id)
    lines = []
    for msg in messages:
        prefix = "Buyer" if msg["role"] == "user" else "Agent"
        lines.append(f"{prefix}: {msg['message']}")
    return "\n".join(lines)

# NOTE: init_db() is called by the server lifespan handler, not at import time.
