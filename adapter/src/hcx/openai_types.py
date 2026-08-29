"""OpenAI-compatible request/response models (subset Hermes needs)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    user: str | None = None


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "cursor"


class ModelsListResponse(BaseModel):
    object: str = "list"
    data: list[ModelCard]


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: dict[str, Any]
    finish_reason: str | None = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    version: str
    backend: str
    cursor_key_present: bool
    detail: str | None = None
