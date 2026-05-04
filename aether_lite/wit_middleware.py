"""
AETHER WIT Middleware — Token compression pipeline.
Extracted from hydra/aether/wit_middleware.py for standalone deployment.
"""

import re
import logging

logger = logging.getLogger("aether.wit_middleware")

PHRASE_COMPRESSIONS = {
    r"\bin order to\b": "to",
    r"\bdue to the fact that\b": "because",
    r"\bfor the purpose of\b": "for",
    r"\bin the event that\b": "if",
    r"\bwith the exception of\b": "except",
    r"\bbased on the fact that\b": "since",
    r"\bhas the ability to\b": "can",
    r"\bmake a decision\b": "decide",
    r"\bcome to a conclusion\b": "conclude",
}

DOMAIN_TERMS = {
    r"\b[Aa]rtificial [Ii]ntelligence\b": "AI",
    r"\b[Mm]achine [Ll]earning\b": "ML",
    r"\b[Ll]arge [Ll]anguage [Mm]odels?\b": "LLM",
    r"\b[Ss]earch [Ee]ngine [Oo]ptimization\b": "SEO",
    r"\b[Rr]eturn [Oo]n [Ii]nvestment\b": "ROI",
    r"\b[Cc]all [Tt]o [Aa]ction\b": "CTA",
}

def compress_phrase_structures(text: str) -> str:
    for pattern, replacement in PHRASE_COMPRESSIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def compress_enumerations(text: str) -> str:
    text = re.sub(r",\s+(and|or)\s+(the|a|an)\s+", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r",\s+(and|or)\s+", ", ", text, flags=re.IGNORECASE)
    return text

def compress_domain_terms(text: str) -> str:
    for pattern, replacement in DOMAIN_TERMS.items():
        text = re.sub(pattern, replacement, text)
    return text

def apply_compression(text: str) -> str:
    """Pass the text through the AETHER token compression middleware."""
    if not text:
        return text
    text = compress_phrase_structures(text)
    text = compress_enumerations(text)
    text = compress_domain_terms(text)
    text = re.sub(r" {2,}", " ", text)
    return text
