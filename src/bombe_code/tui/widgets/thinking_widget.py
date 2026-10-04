"""Widget animado de feedback para turnos e processamento de agentes na TUI."""

from __future__ import annotations

from typing import Any, ClassVar

from textual.widgets import Static

from ..tokens import TOKENS


class ThinkingWidget(Static):
    """Widget animado de feedback com ampulheta virando e pontinhos nascendo e sumindo."""

    FRAMES: ClassVar[list[str]] = ["⏳", "⌛"]
    DOTS: ClassVar[list[str]] = [".", "..", "...", ""]

    def __init__(
        self,
        message: str = "Processando contexto e aguardando tokens do modelo",
        **kwargs: Any,
    ) -> None:
        super().__init__("", **kwargs)
        self.message = message
        self._frame_idx = 0
        self._dot_idx = 0
        self._timer = None

    def on_mount(self) -> None:
        self._update_display()
        self._timer = self.set_interval(0.35, self._tick)

    def _tick(self) -> None:
        self._frame_idx = (self._frame_idx + 1) % len(self.FRAMES)
        self._dot_idx = (self._dot_idx + 1) % len(self.DOTS)
        self._update_display()

    def _update_display(self) -> None:
        icon = self.FRAMES[self._frame_idx]
        dots = self.DOTS[self._dot_idx]
        self.update(
            f"[{TOKENS['secondary']} bold]{icon}[/{TOKENS['secondary']} bold] "
            f"[{TOKENS['text_muted']} italic]{self.message}{dots}[/{TOKENS['text_muted']} italic]"
        )

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
