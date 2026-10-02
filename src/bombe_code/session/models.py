from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Session(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("ses"))
    slug: str = ""
    project_id: str | None = None
    parent_id: str | None = None
    title: str = ""
    directory: str = ""
    stage: str = "VIBE"
    agent: str | None = None

    model: str | None = None
    tokens: int = 0
    cost: float = 0.0
    summary: str | None = None
    created_at: str = Field(default_factory=_now)



class Message(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("msg"))
    session_id: str
    role: Literal["user", "assistant", "system"]
    created_at: str = Field(default_factory=_now)


class PartBase(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("prt"))
    message_id: str
    created_at: str = Field(default_factory=_now)


class TextPart(PartBase):
    type: Literal["text"] = "text"
    text: str


class ReasoningPart(PartBase):
    type: Literal["reasoning"] = "reasoning"
    text: str = ""


class ToolPart(PartBase):
    type: Literal["tool"] = "tool"
    tool: str
    state: Literal["pending", "running", "completed", "error"]
    tool_call_id: str = ""
    arguments: dict = Field(default_factory=dict)
    output: str = ""


class StepStartPart(PartBase):
    type: Literal["step-start"] = "step-start"


class StepFinishPart(PartBase):
    type: Literal["step-finish"] = "step-finish"


class FilePart(PartBase):
    type: Literal["file"] = "file"
    path: str = ""
    content: str = ""


class PatchPart(PartBase):
    type: Literal["patch"] = "patch"
    diff: str = ""


class SnapshotPart(PartBase):
    type: Literal["snapshot"] = "snapshot"
    hash: str = ""


class CompactionPart(PartBase):
    type: Literal["compaction"] = "compaction"
    summary: str = ""


class SubtaskPart(PartBase):
    type: Literal["subtask"] = "subtask"
    subtask_session_id: str = ""


Part = Annotated[
    TextPart
    | ReasoningPart
    | ToolPart
    | StepStartPart
    | StepFinishPart
    | FilePart
    | PatchPart
    | SnapshotPart
    | CompactionPart
    | SubtaskPart,
    Field(discriminator="type"),
]
