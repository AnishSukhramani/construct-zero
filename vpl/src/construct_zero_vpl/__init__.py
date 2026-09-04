"""Construct-Zero Voice Presentation Layer — layered spoken delivery without extra LLM calls."""

from construct_zero_vpl.config import VplConfig
from construct_zero_vpl.engine import PresentationEngine
from construct_zero_vpl.models import NavPhase, SessionState, SpeechDocument, TurnResult

__version__ = "0.1.0"

__all__ = [
    "NavPhase",
    "PresentationEngine",
    "SessionState",
    "SpeechDocument",
    "TurnResult",
    "VplConfig",
]
