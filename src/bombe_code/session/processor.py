from __future__ import annotations

from . import crud
from .models import Message, TextPart, ToolPart


class TurnProcessor:
    def __init__(self, session_id: str, on_event=None) -> None:
        self.session_id = session_id
        self.on_event = on_event
        self.message = Message(session_id=session_id, role="assistant")
        crud.save_message(self.message)
        self._text: str = ""
        self._text_part: TextPart | None = None
        self._tool_parts: dict[str, ToolPart] = {}

    @property
    def text(self) -> str:
        return self._text

    @property
    def has_tools(self) -> bool:
        return bool(self._tool_parts)

    def emit(self, event: dict) -> None:
        if self.on_event:
            self.on_event(event)

    def add_text(self, delta: str) -> None:
        self._text += delta
        if self._text_part is None:
            self._text_part = TextPart(message_id=self.message.id, text=delta)
        else:
            self._text_part.text += delta

    def flush(self) -> None:
        if self._text_part is not None:
            crud.save_part(self.session_id, self._text_part)

    def start_tool(self, event: dict) -> ToolPart:
        self.flush()
        part = ToolPart(
            message_id=self.message.id,
            tool=event["name"],
            state="running",
            tool_call_id=event.get("id", ""),
            arguments=event.get("arguments", {}),
        )
        crud.save_part(self.session_id, part)
        self._tool_parts[part.id] = part
        return part

    def complete_tool(self, part: ToolPart, output: str, error: bool = False) -> None:
        part.state = "error" if error else "completed"
        part.output = output
        crud.save_part(self.session_id, part)

    def fail_tool(self, part: ToolPart, reason: str) -> None:
        part.state = "error"
        part.output = reason
        crud.save_part(self.session_id, part)

    def cleanup_aborted(self) -> None:
        self.flush()
        for part in self._tool_parts.values():
            if part.state in ("pending", "running"):
                self.fail_tool(part, "abortado")
