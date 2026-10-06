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
        message: str = "",
        active: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__("", **kwargs)
        self.message = message
        self.active = active or bool(message)
        self._frame_idx = 0
        self._dot_idx = 0
        self._timer = None

    def on_mount(self) -> None:
        self._update_display()
        if self.active and self._timer is None:
            self._timer = self.set_interval(0.35, self._tick)

    def start(self, message: str = "Processando contexto e aguardando tokens do modelo") -> None:
        """Inicia a animação com mensagem específica."""
        self.message = message
        self.active = True
        self._frame_idx = 0
        self._dot_idx = 0
        self._update_display()
        if self._timer is None:
            self._timer = self.set_interval(0.35, self._tick)

    def set_message(self, message: str) -> None:
        """Atualiza a mensagem em exibição durante o processamento ativo."""
        self.message = message
        if not self.active:
            self.start(message)
        else:
            self._update_display()

    def stop(self) -> None:
        """Interrompe a animação e oculta o conteúdo da barra."""
        self.active = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        self.update("")

    def _tick(self) -> None:
        if not self.active:
            return
        self._frame_idx = (self._frame_idx + 1) % len(self.FRAMES)
        self._dot_idx = (self._dot_idx + 1) % len(self.DOTS)
        self._update_display()

    def _update_display(self) -> None:
        if not self.active or not self.message:
            self.update("")
            return
        from rich.markup import escape

        icon = self.FRAMES[self._frame_idx]
        dots = self.DOTS[self._dot_idx]
        self.update(
            f"[{TOKENS['secondary']} bold]{icon}[/] "
            f"[{TOKENS['text_muted']} italic]{escape(self.message)}{dots}[/]"
        )

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
