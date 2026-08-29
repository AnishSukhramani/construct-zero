"""HCX Voice Presentation Layer — layered spoken delivery without extra LLM calls."""

from hcx_vpl.config import VplConfig
from hcx_vpl.engine import PresentationEngine
from hcx_vpl.models import NavPhase, SessionState, SpeechDocument, TurnResult

__version__ = "0.1.0"

__all__ = [
    "NavPhase",
    "PresentationEngine",
    "SessionState",
    "SpeechDocument",
    "TurnResult",
    "VplConfig",
]
