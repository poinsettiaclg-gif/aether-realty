"""
AETHER Lite Base Agent — Lightweight agent base for deployment.
Extracted from hydra/agents/base_agent.py. Removes all Hydra DB,
Reaper, and Vertex AI config dependencies. Uses standard Gemini API.
"""

import os
import logging
from abc import ABC, abstractmethod
from google import genai

from aether_lite.wit import WITSchema, compile_wit, estimate_tokens

logger = logging.getLogger("aether.agent")


class BaseAgent(ABC):
    """
    Lightweight AETHER agent base class for standalone deployment.
    No Hydra database, no Vertex AI project config, no Reaper QA.
    Just the WIT compiler + Gemini API.
    """

    def get_client(self):
        """Initialize a Gemini client using API key from environment."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            logger.error(
                "GEMINI_API_KEY environment variable not set. "
                "Get one at https://aistudio.google.com/apikey"
            )
            raise ValueError("AI service is not configured. Please contact support.")
        client = genai.Client(api_key=api_key)
        return client

    def __init__(self, role, wit_schema, weights, agent_id=None,
                 generation=1, parent_id=None):
        self.id = agent_id or f"{role}_{generation}"
        self.role = role
        self.wit_schema = wit_schema
        self.weights = weights
        self.generation = generation
        self.parent_id = parent_id
        self.status = "active"

        # AETHER: compile the WIT schema into a system instruction
        self._compiled_prompt = compile_wit(self.wit_schema)
        self._prompt_tokens = estimate_tokens(self._compiled_prompt)

        # Token tracking
        self.tokens_used = 0
        self.calls_made = 0

        # Legacy compatibility
        self.persona = self._compiled_prompt

        logger.info(
            f"[SPAWN] Agent {self.id} initialized. "
            f"System prompt: {self._prompt_tokens} tokens"
        )

    @abstractmethod
    async def execute(self, task_input):
        """
        Run the agent's primary function.
        Must return a dict with at least:
            {"output": ..., "score": float 0.0-1.0, "metadata": {}}
        """
        pass

    @abstractmethod
    def calculate_score(self, task_result):
        """Calculate a performance score (0.0 - 1.0) for a completed task."""
        pass

    def get_dna(self):
        """Return the agent's full DNA configuration."""
        return {
            "id": self.id,
            "role": self.role,
            "wit_schema": self.wit_schema.to_dict(),
            "weights": self.weights,
            "generation": self.generation,
            "status": self.status,
            "tokens_used": self.tokens_used,
        }

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} id={self.id} role={self.role} "
            f"gen={self.generation} status={self.status}>"
        )
