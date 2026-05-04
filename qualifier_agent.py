import os
import json

from aether_lite.wit import WITSchema
from aether_lite.base_agent import BaseAgent
from google.genai import types

class RealtorQualifierAgent(BaseAgent):
    def __init__(self, agent_id=None):
        schema = WITSchema(
            role="real_estate_qualifier",
            domain="lake_region_florida",
            voice=["professional", "helpful", "concise"],
            pov="1st_person",
            style_ref="concierge_assistant",
            focus=["lead_qualification", "local_knowledge", "intent_extraction"],
            constraints=["no_robotic_responses", "keep_it_under_3_sentences", "always_ask_a_follow_up_question"],
            kill_words=["do_not_promise_prices", "do_not_give_legal_advice"],
            weights={
                "data_collection": 0.9,
                "friendliness": 0.8,
                "conciseness": 0.7
            }
        )
        
        super().__init__(
            role="qualifier",
            wit_schema=schema,
            weights=schema.weights,
            agent_id=agent_id
        )

    async def execute(self, task_input):
        """
        Executes a single turn of conversation.
        task_input: dict {"message": str, "history": list}
        """
        client = self.get_client()
        
        message = task_input.get("message", "")
        history = task_input.get("history", [])
        
        # Build prompt with history
        history_text = "\n".join(history[-6:]) # keep last 6 interactions
        
        prompt = f"""
You are the Lake Region Real Estate Qualifier Agent.
Your current objective is to naturally ask questions to extract:
1. Are they buying or selling?
2. What is their timeline?
3. What is their budget/are they pre-approved?
4. What is their contact information (phone or email)?

Do NOT ask all questions at once. Ask them naturally one by one in conversation.

Conversation History:
{history_text}
User: {message}

Agent Reply:"""
        
        # 1. Generate Conversational Reply
        try:
            response = client.models.generate_content(
                model='gemini-1.5-pro',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self._compiled_prompt,
                    temperature=0.7,
                )
            )
            reply = response.text.strip()
        except Exception as e:
            reply = "I apologize, I'm having trouble connecting to my database. Could you repeat that?"
            print(f"Error calling Gemini for chat: {e}")
            
        # 2. Background Extraction Task (AETHER intent extraction)
        extraction_prompt = f"""
Analyze the following conversation and extract the lead qualification data.
Only mark 'is_qualified' as true if ALL four pieces of information (intent, timeline, budget, contact) are known.

Conversation:
{history_text}
User: {message}
Agent: {reply}

Return a raw JSON object matching this schema exactly:
{{
  "intent": "buying|selling|unknown",
  "timeline": "extracted timeline or unknown",
  "budget": "extracted budget or unknown",
  "contact": "extracted phone/email or unknown",
  "is_qualified": boolean
}}
"""
        extracted_data = {}
        try:
            extract_response = client.models.generate_content(
                model='gemini-1.5-flash', # use flash for fast extraction
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            extracted_data = json.loads(extract_response.text.strip())
        except Exception as e:
            print(f"Error calling Gemini for extraction: {e}")
            extracted_data = {
                "intent": "unknown", "timeline": "unknown", 
                "budget": "unknown", "contact": "unknown", "is_qualified": False
            }
        
        # Return standard BaseAgent result dict, including extracted data
        return {
            "output": reply,
            "extracted_data": extracted_data,
            "score": 1.0, # Dummy score for prototype
            "metadata": {"tokens": 0}
        }

    def calculate_score(self, task_result):
        return 1.0
