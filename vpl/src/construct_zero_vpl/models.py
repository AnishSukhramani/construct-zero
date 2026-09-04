"""Data models for speech documents and navigation state."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NavPhase(str, Enum):
    PASSTHROUGH = "passthrough"
    ORIENT = "orient"
    MAP = "map"
    WAIT = "wait"
    DEEPEN = "deepen"
    DONE = "done"


class SourceSpan(BaseModel):
    start: int
    end: int


class ListItem(BaseModel):
    id: str
    text: str
    span: SourceSpan


class Bucket(BaseModel):
    id: str
    label: str
    items: list[ListItem] = Field(default_factory=list)


class SpeechDocument(BaseModel):
    full_text: str
    intro: str = ""
    items: list[ListItem] = Field(default_factory=list)
    buckets: list[Bucket] = Field(default_factory=list)
    layered: bool = False


class SessionState(BaseModel):
    session_id: str
    document: SpeechDocument
    phase: NavPhase = NavPhase.WAIT
    bucket_index: int | None = None
    item_index: int = 0
    last_speak_text: str = ""
    created_at: float = 0.0


class TurnResult(BaseModel):
    speak_text: str
    reply_full: str
    mode: str
    session_id: str | None = None
    buckets: list[dict[str, Any]] = Field(default_factory=list)
    nav_hint: str = ""
    layered: bool = False
