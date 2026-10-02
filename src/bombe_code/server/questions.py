from __future__ import annotations

import threading


class QuestionBroker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[threading.Event, list[str]]] = {}
        self._answers: dict[str, str] = {}

    def ask(self, question: str, timeout: float = 30.0) -> str:
        with self._lock:
            if question in self._answers:
                return self._answers.pop(question)
            event = threading.Event()
            cell: list[str] = []
            self._pending[question] = (event, cell)
        event.wait(timeout)
        with self._lock:
            self._pending.pop(question, None)
        return cell[0] if cell else "timeout: sem resposta"

    def reply(self, question: str, answer: str) -> bool:
        with self._lock:
            pending = self._pending.get(question)
            if pending is None:
                self._answers[question] = answer
                return False
            event, cell = pending
            cell.append(answer)
            event.set()
            return True

    def pending(self) -> list[str]:
        with self._lock:
            return list(self._pending)
