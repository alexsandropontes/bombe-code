from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ..tools.registry import ToolRegistry, builtin_registry
from .bus import EventBus
from .questions import QuestionBroker


class AskRouter:
    """Ponte de perguntas do loop: question → QuestionBroker; demais → permissões."""

    def __init__(self, permissions: Any | None, questions: QuestionBroker) -> None:
        self._permissions = permissions
        self._questions = questions

    def ask(self, permission: str, details: str = "") -> str:
        if permission == "question":
            return self._questions.ask(details)
        if self._permissions is None:
            return "allow"
        return self._permissions.ask(permission, details)

    def __call__(self, permission: str, details: str = "") -> str:
        return self.ask(permission, details)

    def disabled_tools(self) -> set[str]:
        if self._permissions is None:
            return set()
        return self._permissions.disabled_tools()


@dataclass
class ServerDeps:
    adapter: Any
    project_dir: str
    permissions: Any | None = None
    registry: ToolRegistry = field(default_factory=builtin_registry)
    bus: EventBus = field(default_factory=EventBus)
    questions: QuestionBroker = field(default_factory=QuestionBroker)
    interrupts: dict[str, threading.Event] = field(default_factory=dict)
    running: set[str] = field(default_factory=set)
    _ask: AskRouter | None = field(default=None, repr=False)

    def ask_router(self) -> AskRouter:
        if self._ask is None:
            self._ask = AskRouter(self.permissions, self.questions)
        return self._ask
