"""Aplicação principal TUI (Textual) para o Bombe Code."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Label, Static

from .client import BombeClient
from .tokens import TOKENS
from .widgets.command_palette import CommandPalette
from .widgets.dialogs import PermissionDialog, QuestionDialog
from .widgets.help_dialog import HelpDialog
from .widgets.parts_view import ChatView, PartWidget
from .widgets.prompt_input import PromptInput
from .widgets.sidebar import Sidebar

logger = logging.getLogger(__name__)


class BombeTuiApp(App):
    """Aplicação Textual de Chat do Bombe Code conectada ao servidor via HTTP/SSE."""

    TITLE = "Bombe Code"
    SUB_TITLE = "Agentic Coding Environment"

    CSS = f"""
    Screen {{
        background: {TOKENS['bg']};
        color: {TOKENS['text']};
    }}

    #status-bar {{
        dock: top;
        height: 1;
        background: {TOKENS['surface_alt']};
        color: {TOKENS['text_muted']};
        padding: 0 1;
    }}

    #app-body {{
        width: 100%;
        height: 1fr;
    }}

    #chat-container {{
        width: 1fr;
        height: 100%;
    }}

    #main-container {{
        width: 100%;
        height: 1fr;
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "interrupt", "Interromper Turno", show=True),
        Binding("escape", "interrupt", "Interromper", show=False),
        Binding("ctrl+p", "command_palette", "Paleta de Comandos", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Painel Lateral", show=True),
        Binding("f1", "help", "Ajuda", show=True),
        Binding("ctrl+q", "quit", "Sair", show=True),
    ]

    def __init__(
        self,
        client: BombeClient,
        session_id: str | None = None,
        model: str | None = None,
        agent: str | None = None,
        project_dir: str = ".",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.client = client
        self.session_id = session_id
        self.model_name = model or "padrão"
        self.agent_name = agent or "padrão"
        self.project_dir = project_dir
        self._current_assistant_widget: PartWidget | None = None
        self._current_assistant_text: str = ""
        self._thinking_widget: Static | None = None
        self._sse_task: asyncio.Task | None = None
        self._is_active_turn: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(self._status_text(), id="status-bar")
        with Horizontal(id="app-body"):
            with Vertical(id="chat-container"):
                with Container(id="main-container"):
                    yield ChatView(id="chat-view")
                yield PromptInput(project_dir=self.project_dir, id="prompt-input")
            yield Sidebar(
                id="sidebar",
                project_dir=self.project_dir,
                session_id=self.session_id or "",
                model=self.model_name,
            )
        yield Footer()

    def action_toggle_sidebar(self) -> None:
        """Alterna a visibilidade da Sidebar vertical."""
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.toggle_class("hidden")
        except NoMatches:
            pass

    def _status_text(self) -> str:
        s_id = self.session_id or "conectando..."
        state = "ativo" if self._is_active_turn else "ocioso"
        return f"Sessão: {s_id} | Modelo: {self.model_name} | Agente: {self.agent_name} | Status: {state}"

    def update_status(self) -> None:
        try:
            bar = self.query_one("#status-bar", Label)
            bar.update(self._status_text())
        except (NoMatches, RuntimeError) as exc:
            logger.debug("Falha ao atualizar barra de status: %s", exc)

    async def on_mount(self) -> None:
        if not self.session_id:
            try:
                session_data = await self.client.create_session(title="TUI Session", directory=self.project_dir)
                self.session_id = session_data["id"]
                self.update_status()
                try:
                    sidebar = self.query_one("#sidebar", Sidebar)
                    sidebar.session_id = self.session_id
                    sidebar.update_metrics(title=session_data.get("title"), directory=self.project_dir)
                except NoMatches:
                    pass
            except (OSError, RuntimeError) as exc:
                chat = self.query_one("#chat-view", ChatView)
                await chat.mount(
                    Static(f"[{TOKENS['error']}]Erro ao conectar ao servidor: {exc}[/{TOKENS['error']}]")
                )
                return

        await self._load_history()
        self._sse_task = asyncio.create_task(self._listen_sse())
        try:
            self.query_one("#prompt-input", PromptInput).focus()
        except NoMatches:
            pass

    async def on_unmount(self) -> None:
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()

    async def _load_history(self) -> None:
        if not self.session_id:
            return
        chat = self.query_one("#chat-view", ChatView)
        try:
            history = await self.client.get_history(self.session_id)
            for msg in history:
                role = msg.get("role", "user")
                prefix = f"[{TOKENS['primary']} bold]Você:[/{TOKENS['primary']} bold]\n" if role == "user" else f"[{TOKENS['secondary']} bold]Agente:[/{TOKENS['secondary']} bold]\n"
                await chat.mount(Static(prefix))
                for part in msg.get("parts", []):
                    await chat.mount(PartWidget(part))
        except (OSError, RuntimeError, httpx.HTTPError) as exc:
            logger.warning("Falha ao carregar histórico: %s", exc)

    async def on_input_submitted(self, event: PromptInput.Submitted) -> None:
        if not self.session_id:
            return
        text = event.value.strip()
        if not text:
            return
        if isinstance(event.input, PromptInput):
            event.input.record_history(text)
        chat = self.query_one("#chat-view", ChatView)

        # Roteamento completo dos 28 comandos de barra (/) do OpenCode
        if text.startswith("/"):
            from .commands import handle_slash_command

            try:
                await handle_slash_command(self, text)
            except Exception as exc:
                from ..errors import record_exception

                err_file = record_exception(exc, context=f"slash_command: {text}")
                logger.exception("Erro ao processar slash command '%s'", text)
                await chat.mount(
                    Static(
                        f"[{TOKENS['error']} bold]❌ Erro ao executar '{text}':[/{TOKENS['error']} bold] "
                        f"[{TOKENS['error']}]{exc}[/{TOKENS['error']}]\n"
                        f"[dim]Detalhes técnicos gravados em: {err_file}[/dim]"
                    )
                )
            return

        await chat.mount(Static(f"\n[{TOKENS['primary']} bold]Você:[/{TOKENS['primary']} bold] {text}"))
        self._is_active_turn = True
        self.update_status()

        # Inicia prompt no background worker
        self._run_prompt_worker(text)

    @work(exclusive=True)
    async def _run_prompt_worker(self, text: str) -> None:
        try:
            model_to_send = self.model_name if self.model_name != "padrão" else None
            await self.client.send_prompt(self.session_id, text, model=model_to_send)
        except (OSError, RuntimeError, httpx.HTTPError) as exc:
            chat = self.query_one("#chat-view", ChatView)
            if isinstance(exc, httpx.TimeoutException):
                err_msg = f"Tempo limite de resposta esgotado ({type(exc).__name__}). O modelo pode estar sobrecarregado ou gerando uma resposta longa."
            else:
                err_msg = str(exc).strip() or type(exc).__name__
            await chat.mount(Static(f"[{TOKENS['error']}]Erro ao enviar prompt: {err_msg}[/{TOKENS['error']}]"))
        finally:
            self._is_active_turn = False
            self.update_status()

    async def _listen_sse(self) -> None:
        if not self.session_id:
            return
        last_id = 0
        while True:
            try:
                async for event in self.client.stream_events(self.session_id, last_event_id=last_id):
                    ev_id = event.get("_event_id")
                    if ev_id:
                        last_id = ev_id
                    await self._handle_event(event)
            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                logger.debug("Reconectando SSE após erro: %s", exc)
                await asyncio.sleep(1.0)

    async def _handle_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type")
        chat = self.query_one("#chat-view", ChatView)

        if etype == "prompt.started":
            self._is_active_turn = True
            self._current_assistant_text = ""
            self._current_assistant_widget = None
            if self._thinking_widget is not None:
                await self._thinking_widget.remove()
                self._thinking_widget = None
            self.update_status()
            await chat.mount(Static(f"\n[{TOKENS['secondary']} bold]Agente:[/{TOKENS['secondary']} bold]"))
            self._thinking_widget = Static(
                f"[{TOKENS['text_muted']} italic]⏳ Processando contexto e aguardando tokens do modelo...[/{TOKENS['text_muted']} italic]"
            )
            await chat.mount(self._thinking_widget)

        elif etype == "text-delta":
            if self._thinking_widget is not None:
                await self._thinking_widget.remove()
                self._thinking_widget = None
            delta = event.get("text", "")
            self._current_assistant_text += delta
            if self._current_assistant_widget is None:
                self._current_assistant_widget = PartWidget({"type": "text", "text": self._current_assistant_text})
                await chat.mount(self._current_assistant_widget)
            else:
                self._current_assistant_widget.update_text(self._current_assistant_text)
            chat.scroll_end(animate=False)

        elif etype == "tool-call" or etype == "tool-input":
            if self._thinking_widget is not None:
                await self._thinking_widget.remove()
                self._thinking_widget = None
            # nova tool invocada
            self._current_assistant_widget = None
            widget = PartWidget(
                {
                    "type": "tool",
                    "tool": event.get("tool", "ferramenta"),
                    "state": "running",
                    "arguments": event.get("arguments", {}),
                }
            )
            await chat.mount(widget)
            chat.scroll_end(animate=False)

        elif etype == "tool-result":
            if self._thinking_widget is not None:
                await self._thinking_widget.remove()
                self._thinking_widget = None
            widget = PartWidget(
                {
                    "type": "tool",
                    "tool": event.get("tool", "ferramenta"),
                    "state": "error" if event.get("error") else "completed",
                    "output": event.get("output", "") or event.get("error", ""),
                }
            )
            await chat.mount(widget)
            chat.scroll_end(animate=False)

        elif etype == "permission.asked":
            perm = event.get("permission", "ação")
            details = event.get("details", "")
            decision = await self.push_screen_wait(PermissionDialog(perm, details))
            if decision and self.session_id:
                await self.client.reply_permission(self.session_id, perm, details, decision)

        elif etype == "question.asked":
            question = event.get("question", "")
            answer = await self.push_screen_wait(QuestionDialog(question))
            if answer and self.session_id:
                await self.client.reply_question(self.session_id, question, answer)

        elif etype == "prompt.finished":
            if self._thinking_widget is not None:
                await self._thinking_widget.remove()
                self._thinking_widget = None
            self._is_active_turn = False
            self._current_assistant_widget = None
            self.update_status()

        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            if etype == "text-delta":
                delta_text = event.get("text", "")
                if delta_text:
                    sidebar.tokens_count += max(1, len(delta_text) // 4)
                    sidebar.cost = round((sidebar.tokens_count / 1_000_000) * 3.0, 4)
                    sidebar.context_percent = min(100, int((sidebar.tokens_count / 128_000) * 100))
                    sidebar.refresh_view()
            elif etype in ("tool-result", "prompt.finished"):
                sidebar.refresh_view()
        except NoMatches:
            pass

    async def action_interrupt(self) -> None:
        """Interrompe o turno ativo via client.interrupt."""
        if self.session_id and self._is_active_turn:
            try:
                await self.client.interrupt(self.session_id)
                chat = self.query_one("#chat-view", ChatView)
                await chat.mount(Static(f"[{TOKENS['warning']}]Turno interrompido pelo usuário.[/{TOKENS['warning']}]"))
            except (OSError, RuntimeError) as exc:
                logger.warning("Erro ao interromper turno: %s", exc)
            finally:
                self._is_active_turn = False
                self.update_status()

    def action_command_palette(self) -> None:
        """Abre a paleta de comandos modal."""
        def _on_command(cmd: str | None) -> None:
            if not cmd:
                return
            if cmd == "help":
                self.action_help()
            elif cmd == "clear":
                chat = self.query_one("#chat-view", ChatView)
                chat.remove_children()
            elif cmd == "quit":
                self.exit()
            elif cmd == "theme":
                self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"
            elif cmd == "sidebar":
                self.action_toggle_sidebar()

        try:
            self.push_screen(CommandPalette(), _on_command)
        except Exception:
            logger.exception("Erro ao abrir paleta de comandos")

    def action_help(self) -> None:
        """Abre o diálogo de ajuda modal."""
        self.push_screen(HelpDialog())

    def _fatal_error(self) -> None:
        """Encerra a aplicação de forma elegante sem despejar código/locals na tela do usuário."""
        from rich.segment import Segments

        from ..errors import format_error_panel, is_debug_mode, record_exception

        self.bell()
        err_file = record_exception(self._exception, context="Textual Fatal Error")

        if is_debug_mode():
            super()._fatal_error()
            return

        panel = format_error_panel(self._exception, err_file)
        self._exit_renderables.append(
            Segments(self.console.render(panel, self.console.options))
        )
        self._close_messages_no_wait()

