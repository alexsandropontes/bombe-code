"""Modelos Pydantic tipados do Bombe Code SDK."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SessionModel(BaseModel):
    id: str
    title: str = ""
    slug: str = ""
    directory: str = ""
    agent: str | None = None
    model: str | None = None
    created_at: str = ""


class PromptResult(BaseModel):
    status: str
    text: str = ""


class SDKEvent(BaseModel):
    type: str
    session_id: str | None = None
    event_id: int | None = Field(default=None, alias="_event_id")
    raw: dict[str, Any] = Field(default_factory=dict)
