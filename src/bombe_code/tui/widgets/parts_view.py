"""Widgets para renderização de Parts de Mensagem na TUI."""

from __future__ import annotations

import json
import time
from typing import Any

from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widget import AwaitMount, Widget
from textual.widgets import Static

from ..tokens import TOKENS


class PartWidget(Static):
    """Renderiza uma Part individual com estilização do Design System."""

    def __init__(self, part_data: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.part_data = part_data
        self._is_streaming: bool = False
        self._last_render_time: float = 0.0

    def on_mount(self) -> None:
        self.update(self._get_renderable())

    def render(self) -> Any:
        return self._get_renderable()

    def update_stream(self, text: str) -> None:
        """Atualização de alta frequência durante streaming contínuo.

        Garante fluidez visual idêntica ao OpenCode original e previne congelamento
        da UI por re-parsing excessivo de Markdown na mesma frame de execução.
        """
        self.part_data["text"] = text
        self._is_streaming = True
        now = time.monotonic()
        # Atualiza a tela a no máximo ~25-30 FPS (~35ms), permitindo fluidez visual impecável
        # sem consumir 100% da CPU do event loop do Textual.
        if now - self._last_render_time >= 0.035:
            self._last_render_time = now
            self.update(self._get_renderable())

    def finalize_stream(self) -> None:
        """Finaliza o ciclo de streaming e consolida a renderização definitiva."""
        self._is_streaming = False
        self.update(self._get_renderable())

    def update_text(self, text: str) -> None:
        self.part_data["text"] = text
        self.update(self._get_renderable())

    def _get_renderable(self) -> Any:
        ptype = self.part_data.get("type", "text")

        if ptype == "text":
            content = self.part_data.get("text", "")
            return Markdown(content)

        elif ptype == "reasoning":
            content = self.part_data.get("text", "")
            title = (
                "[dim]⚡ Pensamento / Raciocínio (em tempo real...)[/dim]"
                if self._is_streaming
                else "[dim]Pensamento / Raciocínio[/dim]"
            )
            return Panel(
                Text(content, style=f"italic {TOKENS['text']} dim"),
                title=title,
                border_style=TOKENS["border"],
            )

        elif ptype == "tool":
            tool_name = self.part_data.get("tool", "unknown")
            state = self.part_data.get("state", "pending")
            output = self.part_data.get("output", "")
            args = self.part_data.get("arguments", {})

            if state == "completed":
                badge = f"[{TOKENS['success']}]✓ {tool_name}[/{TOKENS['success']}]"
            elif state == "running":
                badge = f"[{TOKENS['warning']}]⚡ {tool_name} (executando...)[/{TOKENS['warning']}]"
            elif state == "error":
                badge = f"[{TOKENS['error']}]✗ {tool_name} (erro)[/{TOKENS['error']}]"
            else:
                badge = (
                    f"[{TOKENS['text_muted']}]⏳ {tool_name} (pendente)[/{TOKENS['text_muted']}]"
                )

            body = Text()
            body.append_text(Text.from_markup(badge))
            if args:
                args_str = json.dumps(args, ensure_ascii=False)
                if len(args_str) > 80:
                    args_str = args_str[:77] + "..."
                body.append(f" args: {args_str}\n", style=f"{TOKENS['text_muted']}")
            if output:
                trunc = output if len(output) <= 300 else output[:297] + "..."
                body.append(f"\n{trunc}", style=TOKENS["text"])

            return Panel(body, title=f"Ferramenta: {tool_name}", border_style=TOKENS["border"])

        elif ptype == "patch":
            diff = self.part_data.get("diff", "")
            return Panel(
                Syntax(diff, "diff", theme="monokai", line_numbers=False),
                title="Patch Diff",
                border_style=TOKENS["border"],
            )

        elif ptype == "image":
            file_name = self.part_data.get("file_name", "imagem")
            mime = self.part_data.get("mime_type", "image")
            return Panel(
                Text(
                    f"📷 [Anexo de Imagem: {file_name} ({mime})]",
                    style=f"bold {TOKENS['secondary']}",
                ),
                title="Imagem",
                border_style=TOKENS["border"],
            )

        return Text(str(self.part_data))


class ChatView(VerticalScroll):
    """Contêiner do histórico de chat com rolagem e auto-follow inteligente.

    O usuário PODE rolar (roda do mouse, scrollbar, PageUp/PageDown): enquanto
    ele estiver longe do fim, o texto novo NÃO arrasta a tela. Ao voltar para
    o fim, o acompanhamento automático religa sozinho.
    """

    DEFAULT_CSS = f"""
    ChatView {{
        background: {TOKENS["bg"]};
        color: {TOKENS["text"]};
        padding: 1;
        overflow-y: scroll;
    }}
    """

    def on_mount(self) -> None:
        self._seguir = True

    def mount(
        self,
        *widgets: Widget,
        before: int | str | Widget | None = None,
        after: int | str | Widget | None = None,
    ) -> AwaitMount:
        res = super().mount(*widgets, before=before, after=after)
        self.seguir()
        return res

    def scroll_to_latest(self) -> None:
        """Acompanha o texto novo — só cola no fim se o usuário está no fim."""
        self.seguir()

    def seguir(self) -> None:
        if not self.is_attached:
            return
        if getattr(self, "_seguir", True):
            self.anchor()
            self.scroll_end(animate=False)
        else:
            self.anchor(False)

    # ── Controle do usuário: roda, scrollbar, teclado ──
    def pagina(self, direcao: str) -> None:
        if direcao == "up":
            self._seguir = False
            self.anchor(False)
            self.scroll_page_up(animate=False)
        elif direcao == "down":
            self.scroll_page_down(animate=False)
            self.call_after_refresh(self._atualizar_seguir)
        elif direcao == "top":
            self._seguir = False
            self.anchor(False)
            self.scroll_home(animate=False)
        else:
            # Usuário pediu o fim: auto-follow religa POR SEMÂNTICA (sem
            # depender da leitura de posição, que é assíncrona).
            self._seguir = True
            self.anchor()
            self.scroll_end(animate=False)

    def _atualizar_seguir(self) -> None:
        try:
            self._seguir = self.scroll_offset.y >= self.max_scroll_y - 2
        except Exception:  # noqa: BLE001 — layout pode não estar pronto
            self._seguir = True

    def on_scroll_up(self) -> None:
        self._seguir = False

    def on_scroll_down(self) -> None:
        self.call_after_refresh(self._atualizar_seguir)
