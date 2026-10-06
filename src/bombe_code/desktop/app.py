"""Shell Desktop pywebview para o Bombe Code."""

from __future__ import annotations

import os
import sys
from typing import Any


class DesktopApp:
    """Invólucro nativo de janela desktop usando pywebview."""

    def __init__(
        self,
        url: str = "http://127.0.0.1:4096",
        title: str = "Bombe Code Desktop",
        width: int = 1200,
        height: int = 800,
    ) -> None:
        self.url = url
        self.title = title
        self.width = width
        self.height = height

    def get_window_spec(self) -> dict[str, Any]:
        """Retorna parâmetros de inicialização da janela."""
        return {
            "title": self.title,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "min_size": (800, 600),
        }

    def is_display_available(self) -> bool:
        """Verifica se há display gráfico disponível para abrir janela desktop."""
        if sys.platform == "darwin" or sys.platform == "win32":
            return True
        # Linux / Unix
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def run_headless_safe(self) -> str:
        """Execução segura que não quebra se chamado em terminal/CI sem tela."""
        if not self.is_display_available():
            return "headless_mode_detected"

        try:
            import webview

            spec = self.get_window_spec()
            webview.create_window(**spec)
            webview.start()
            return "window_closed"
        except Exception as exc:  # noqa: BLE001 - pywebview pode lançar exceções de runtime GUI variadas
            return f"error: {exc}"
