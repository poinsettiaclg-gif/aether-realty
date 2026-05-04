"""
AETHER WIT Compiler — Weighted Intent Token schema and compilation.
Extracted from hydra/aether/wit.py for standalone deployment.
"""

import math
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict

from aether_lite.wit_middleware import apply_compression

logger = logging.getLogger("aether.wit")


@dataclass
class WITSchema:
    """
    Weighted Intent Token schema — the DNA of an AETHER agent.
    Replaces verbose multi-paragraph persona prompts with a structured
    instruction set that compiles to ~50-80 tokens.
    """
    role: str
    domain: str = ""
    mode: str = "generate"
    voice: List[str] = field(default_factory=list)
    pov: str = ""
    constraints: List[str] = field(default_factory=list)
    kill_words: List[str] = field(default_factory=list)
    style_ref: str = ""
    focus: List[str] = field(default_factory=list)
    tone_target: str = ""
    output_schema: str = ""
    weights: Dict[str, float] = field(default_factory=dict)
    max_tokens: int = 600
    temperature_base: float = 0.7

    def effective_temperature(self) -> float:
        creativity = self.weights.get("creativity", self.temperature_base)
        return max(0.2, min(1.5, creativity * 1.5))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WITSchema":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def compile_wit(schema: WITSchema) -> str:
    """
    Compile a WIT schema into a compressed system instruction.
    ~50-80 tokens that steer the LLM with the same fidelity as
    a 200-500 token verbose persona prompt.
    """
    parts = []
    header = f"ROLE: {schema.role}"
    if schema.domain:
        header += f" | DOMAIN: {schema.domain}"
    parts.append(header)

    if schema.mode and schema.mode != "generate":
        parts.append(f"MODE: {schema.mode}")
    if schema.voice:
        parts.append(f"VOICE: {' | '.join(schema.voice)}")
    if schema.pov:
        parts.append(f"POV: {schema.pov}")
    if schema.style_ref:
        parts.append(f"STYLE: {schema.style_ref}")
    if schema.focus:
        parts.append(f"FOCUS: {', '.join(schema.focus)}")
    if schema.constraints:
        parts.append(f"CONSTRAINTS: {' | '.join(schema.constraints)}")
    if schema.kill_words:
        parts.append(f"NEVER USE: {', '.join(schema.kill_words)}")
    if schema.tone_target:
        parts.append(f"TONE: {schema.tone_target}")
    if schema.output_schema:
        parts.append(f"OUTPUT: {schema.output_schema}")
    if schema.weights:
        w_str = " | ".join(f"{k}={v}" for k, v in schema.weights.items())
        parts.append(f"PRIORITY: {w_str}")

    compiled = "\n".join(parts)
    compiled = apply_compression(compiled)
    return compiled


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)
