from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel

MAX_OUTPUT = 40_000

AskFn = Callable[..., str]
SubtaskFn = Callable[[str], str]


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[output truncated: {len(text)} chars total]"


class InvalidArgumentsError(Exception):
    pass


def _default_ask(permission: str, details: str = "") -> str:
    return "allow"


def _default_subtask(prompt: str) -> str:
    return ""


def _default_abort() -> bool:
    return False


@dataclass
class ToolContext:
    session_id: str = ""
    message_id: str = ""
    agent: str = "build"
    stage: str = "VIBE"
    project_dir: str = ""

    messages: list = field(default_factory=list)
    ask: AskFn = field(default_factory=lambda: _default_ask)
    run_subtask: SubtaskFn = field(default_factory=lambda: _default_subtask)
    metadata: Callable[[], dict] = field(default_factory=lambda: dict)
    abort: Callable[[], bool] = field(default_factory=lambda: _default_abort)


@dataclass
class ToolDef:
    id: str
    description: str
    parameters: type[BaseModel]
    execute: Callable[[dict, ToolContext], str]

    def json_schema(self) -> dict:
        return self.parameters.model_json_schema()
