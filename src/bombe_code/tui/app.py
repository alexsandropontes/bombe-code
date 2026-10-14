"""Aplicação principal TUI (Textual) para o Bombe Code."""

from __future__ import annotations

import asyncio
import logging
import os

# PARIDADE DE TERMINAL: o protocolo Kitty do Textual faz o terminal PARAR de
# interceptar Ctrl+Shift+C (copiar a seleção) e repassar a tecla ao app — que
# poderia agir por cima da seleção do usuário. Desligado: Ctrl+Shift+C volta a
# ser do TERMINAL (copia só o selecionado) e o mouse continua rolando o chat.
# Tem que ser setado ANTES do import do Textual.
os.environ.setdefault("TEXTUAL_DISABLE_KITTY_KEY", "1")
import os
from pathlib import Path
from typing import Any, ClassVar

import httpx
from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult, ScreenStackError
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
from .widgets.thinking_widget import ThinkingWidget

logger = logging.getLogger(__name__)


class BombeTuiApp(App):
    """Aplicação Textual de Chat do Bombe Code conectada ao servidor via HTTP/SSE."""

    TITLE = "Bombe Code"
    SUB_TITLE = "Agentic Coding Environment"

    _last_ctrl_c_ts: float = 0.0  # janela do Ctrl+C (1º copia, 2º sai)

    CSS = f"""
    Screen {{
        background: {TOKENS["bg"]};
        color: {TOKENS["text"]};
    }}

    #status-bar {{
        dock: top;
        height: 1;
        background: {TOKENS["surface_alt"]};
        color: {TOKENS["text_muted"]};
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

    #processing-status-bar {{
        height: 1;
        min-height: 1;
        max-height: 1;
        background: transparent;
        color: {TOKENS["text_muted"]};
        padding: 0 1;
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("shift+tab", "toggle_vibe_mode", "Alternar VIBE/FLOW", show=True),
        Binding("tab", "cycle_stage", "Alternar Etapa (FLOW)", show=True),
        # 1º Ctrl+C (ou Ctrl+Shift+C — o terminal entrega os dois como o
        # mesmo byte) = COPIA a transcrição · 2º aperto = sai com checkpoint.
        Binding("ctrl+c", "copy_or_quit", "Copiar tela / 2× sai", show=False),
        Binding("escape", "escape_press", "Interromper (2× ESC)", show=False),
        Binding("ctrl+p", "command_palette", "Paleta de Comandos", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Painel Lateral", show=True),
        Binding("f2", "copiar_tela", "Copiar tudo (F2)", show=True),
        Binding("f3", "copiar_selecao", "Copiar seleção (F3)", show=True),
        Binding("pageup", "chat_page_up", "Chat ↑ página", show=False, priority=True),
        Binding("pagedown", "chat_page_down", "Chat ↓ página", show=False, priority=True),
        Binding("home", "chat_page_top", "Chat início", show=False),
        Binding("end", "chat_page_bottom", "Chat fim", show=False),
        Binding("f1", "help", "Ajuda", show=True),
        Binding("ctrl+q", "quit", "Sair", show=True),
    ]

    WAVE_ZERO_STAGES: ClassVar[list[str]] = ["DISCOVERY", "INCEPTION"]
    DELIVERY_WAVE_STAGES: ClassVar[list[str]] = ["PLAN", "REFINEMENT", "EXECUTE", "VALIDATE"]
    WAVE_STAGES: ClassVar[list[str]] = [
        "DISCOVERY",
        "INCEPTION",
        "PLAN",
        "REFINEMENT",
        "EXECUTE",
        "VALIDATE",
    ]
    WAVE_STATIONS = WAVE_STAGES

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
        self.mode: str = "TDD"
        self.wave_station: str = "DISCOVERY"
        self._last_tdd_stage: str = "DISCOVERY"
        self._load_current_stage_from_db()
        self._current_assistant_widget: PartWidget | None = None
        self._current_assistant_text: str = ""
        self._current_reasoning_widget: PartWidget | None = None
        self._current_reasoning_text: str = ""
        self._processing_bar: ThinkingWidget | None = None
        self._thinking_widget: Static | None = None
        self._sse_task: asyncio.Task | None = None
        self._is_active_turn: bool = False
        os.environ["BOMBE_TUI_RUNNING"] = "1"

    def get_current_wave_stages(self) -> list[str]:
        """Retorna as etapas válidas para o Tab conforme a ontologia da onda ativa (Onda 0 vs Ondas de Entrega)."""
        try:
            from ..storage.project_db import ProjectDatabase

            db = ProjectDatabase(self.project_dir)
            saved = db.load_wave_state()
            if not saved:
                # Projeto recém-criado, sem estado persistido -> Onda 0 (Greenfield)
                return self.WAVE_ZERO_STAGES

            wave_id = str(saved.get("wave_id", "ONDA-000")).upper().strip()
            if wave_id in (
                "ONDA-0",
                "ONDA-00",
                "ONDA-000",
                "WAVE-0",
                "WAVE-00",
                "WAVE-000",
            ) or wave_id.startswith(("ONDA-000-", "WAVE-000-", "ONDA-0-", "WAVE-0-")):
                return self.WAVE_ZERO_STAGES
        except Exception:  # noqa: BLE001
            return self.WAVE_ZERO_STAGES

        return self.DELIVERY_WAVE_STAGES

    def _load_current_stage_from_db(self) -> None:
        """Carrega a etapa atual da ONDA persistida no banco SQLite local (.bombe-code/state.db)."""
        try:
            from ..storage.project_db import ProjectDatabase

            db = ProjectDatabase(self.project_dir)
            saved = db.load_wave_state()
            allowed = self.get_current_wave_stages()

            if saved and saved.get("state"):
                raw_state = str(saved["state"]).upper()
                if raw_state == "VIBE":
                    self.mode = "VIBE"
                    self.wave_station = "VIBE"
                else:
                    self.mode = "TDD"
                    # Normalização caso venha de terminologia anterior
                    if raw_state == "DISCUSS":
                        raw_state = "DISCOVERY" if "DISCOVERY" in allowed else "PLAN"
                    elif raw_state not in allowed and raw_state != "COMPLETED":
                        raw_state = allowed[0]

                    self.wave_station = raw_state
                    self._last_tdd_stage = raw_state
            else:
                self.wave_station = allowed[0]
                self._last_tdd_stage = allowed[0]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Não foi possível carregar estado da onda no boot da TUI: %s", exc)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(self._status_text(), id="status-bar")
        with Horizontal(id="app-body"):
            with Vertical(id="chat-container"):
                with Container(id="main-container"):
                    yield ChatView(id="chat-view")
                yield ThinkingWidget(id="processing-status-bar")
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

    def action_toggle_vibe_mode(self) -> None:
        """Alterna autônomamente entre Modo TDD e Modo VIBE via Shift+Tab."""
        old_mode = self.mode
        allowed = self.get_current_wave_stages()
        default_stage = allowed[0]

        if self.mode == "VIBE":
            self.mode = "TDD"
            self.wave_station = (
                self._last_tdd_stage if self._last_tdd_stage in allowed else default_stage
            )
        else:
            self._last_tdd_stage = (
                self.wave_station if self.wave_station in allowed else default_stage
            )
            self.mode = "VIBE"
            self.wave_station = "VIBE"

        self.update_status()

        # 1. Persiste no banco SQLite local do projeto
        try:
            from ..storage.project_db import ProjectDatabase

            db = ProjectDatabase(self.project_dir)
            saved = db.load_wave_state() or {}
            default_wave = "ONDA-000" if "DISCOVERY" in allowed else "ONDA-001"
            wave_id = saved.get("wave_id", default_wave)
            autonomy = saved.get("autonomy_mode", "AUTO")
            eng = "vibe-code" if self.mode == "VIBE" else "tdd-code"
            db.save_wave_state(
                wave_id=wave_id,
                state=self.wave_station,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao salvar modo VIBE/TDD no SQLite: %s", exc)

        # 2. Notifica o backend HTTP via API
        if self.session_id:
            asyncio.create_task(self._sync_stage_to_server(self.wave_station))

        # 3. Notifica visualmente no chat
        self._notify_mode_switch(old_mode, self.mode)

    def action_cycle_stage(self) -> None:
        """Alterna ciclicamente entre as etapas da ONDA respeitando a ontologia ativa (apenas em modo TDD)."""
        if self.mode == "VIBE":
            # No modo VIBE não existem sub-etapas; o Tab não cicla
            return

        allowed = self.get_current_wave_stages()
        old_stage = self.wave_station

        # Normalizações de compatibilidade/transição
        normalized = self.wave_station
        if "DISCOVERY" in allowed:
            # Estamos na Onda 0 (DISCOVERY ➔ INCEPTION)
            if normalized in ("DISCUSS", "PLAN", "INCEPTION", "FOUNDATION"):
                normalized = (
                    "INCEPTION"
                    if normalized in ("PLAN", "INCEPTION", "FOUNDATION")
                    else "DISCOVERY"
                )
        else:
            # Estamos nas Ondas Subsequentes (PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE)
            if normalized in ("DISCUSS", "DISCOVERY"):
                normalized = "PLAN"
            elif normalized in ("INCEPTION", "FOUNDATION"):
                normalized = "REFINEMENT"

        if normalized in allowed:
            idx = (allowed.index(normalized) + 1) % len(allowed)
            self.wave_station = allowed[idx]
        else:
            self.wave_station = allowed[0]

        self._last_tdd_stage = self.wave_station
        self.update_status()

        # 1. Persiste no banco SQLite local do projeto
        try:
            from ..storage.project_db import ProjectDatabase

            db = ProjectDatabase(self.project_dir)
            saved = db.load_wave_state() or {}
            default_wave = "ONDA-000" if "DISCOVERY" in allowed else "ONDA-001"
            wave_id = saved.get("wave_id", default_wave)
            autonomy = saved.get("autonomy_mode", "AUTO")
            eng = saved.get("engineering_mode", "tdd-code")
            db.save_wave_state(
                wave_id=wave_id,
                state=self.wave_station,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao salvar wave_state no SQLite: %s", exc)

        # 2. Notifica o backend HTTP via API
        if self.session_id:
            asyncio.create_task(self._sync_stage_to_server(self.wave_station))

        # 3. Notifica visualmente o usuário no chat
        self._notify_stage_switch(old_stage, self.wave_station)

    async def _sync_stage_to_server(self, stage: str) -> None:
        try:
            await self.client.set_stage(self.session_id, stage)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao sincronizar stage com servidor: %s", exc)

    def _notify_mode_switch(self, old_mode: str, new_mode: str) -> None:
        try:
            chat = self.query_one("#chat-view", ChatView)
            if new_mode == "VIBE":
                msg = (
                    "\n🔥 [bold #ff0000]MODO VIBE CODE ATIVADO (Shift+Tab):[/] "
                    "[dim]Modo livre ativado. Sem amarras formais ou travas de etapa: a LLM atende suas ordens com agilidade total.[/dim]"
                )
            else:
                msg = (
                    f"\n🛡️ [{TOKENS['primary']} bold]MODO VIBE FLOW ATIVADO (Shift+Tab):[/] "
                    f"[dim]Retomando governança estruturada da ONDA na etapa [bold]{self.wave_station}[/bold]. Pressione Tab para alternar etapas.[/dim]"
                )
            chat.mount(Static(msg))
            chat.seguir()
        except Exception:  # noqa: BLE001, S110
            pass

    def _notify_stage_switch(self, old_stage: str, new_stage: str) -> None:
        stage_guides = {
            "DISCOVERY": "Descoberta & Viabilidade (Onda 0) — Pesquisa de mercado, briefing e visão de produto em docs/",
            "INCEPTION": "Lean Inception & Sequenciador (Onda 0) — Canvas MVP, personas, jornadas e fatiamento em docs/",
            "FOUNDATION": "Lean Inception & Sequenciador (Onda 0) — Canvas MVP, personas, jornadas e fatiamento em docs/",
            "DISCUSS": "Concepção & Escopo — Escrita de código bloqueada; permitido briefings em docs/",
            "PLAN": "Planejamento da Onda — Arquitetura técnica, ADRs e contratos da fatia em docs/",
            "REFINEMENT": "Refinamento PBB — Decomposição em ai-stories e tarefas atômicas em docs/backlog/",
            "EXECUTE": "Construção TDD — Escrita totalmente liberada em src/, tests/ e docs/",
            "VALIDATE": "Qualidade & Validação — Homologação, relatórios em docs/reports/ e testes E2E",
            "COMPLETED": "Onda Concluída — Pronto para a próxima onda",
        }
        guide = stage_guides.get(new_stage, "")
        try:
            chat = self.query_one("#chat-view", ChatView)
            msg = (
                f"\n⚡ [{TOKENS['primary']} bold]Etapa alternada (Tab):[/] "
                f"[{TOKENS['secondary']} bold]{old_stage}[/] ➔ [{TOKENS['accent']} bold]{new_stage}[/]\n"
                f"[{TOKENS['text_muted']}]{guide}[/]"
            )
            chat.mount(Static(msg))
            chat.seguir()
        except Exception:  # noqa: BLE001, S110
            pass

    def action_cycle_station(self) -> None:
        self.action_cycle_stage()

    def _status_text(self) -> str:
        s_id = self.session_id or "conectando..."
        state = "ativo" if self._is_active_turn else "ocioso"
        if self.mode == "VIBE":
            mode_badge = "[bold #ff0000]VIBE CODE[/]"
        else:
            mode_badge = f"[{TOKENS['primary']} bold]VIBE FLOW ({self.wave_station})[/]"

        return (
            f"Modo: {mode_badge} | "
            f"Sessão: {s_id} | Modelo: {self.model_name} | Agente: {self.agent_name} | Status: {state}"
        )

    def update_status(self) -> None:
        try:
            bar = self.query_one("#status-bar", Label)
            bar.update(self._status_text())
        except (NoMatches, RuntimeError, ScreenStackError) as exc:
            logger.debug("Falha ao atualizar barra de status: %s", exc)

    async def on_mount(self) -> None:
        # Título da ABA do terminal (paridade do setTerminalTitle do opencode):
        # "BC | Projeto - Onda <id> - <Nome da Onda>"; sem onda: "BC | Projeto";
        # sem nada configurado ainda: "BC | Projeto sem nome". Poll leve para
        # acompanhar configure/ONDA no meio da sessão.
        self._atualizar_titulo()
        self.set_interval(10.0, self._atualizar_titulo)
        # Mouse da TUI ATIVO: roda do mouse, scrollbar e cliques rolam o chat.
        # Seleção nativa de texto = Shift+arrastar (o terminal VTE ignora a
        # captura do app quando Shift está pressionado). Copiar: Ctrl+Shift+C
        # do terminal (seleção) | F2 / /copy (transcrição completa).
        if not self.session_id:
            try:
                session_data = await self.client.create_session(
                    title="TUI Session", directory=self.project_dir
                )
                self.session_id = session_data["id"]
                if session_data.get("stage"):
                    s_stage = str(session_data["stage"]).upper()
                    if s_stage in self.WAVE_STAGES or s_stage == "COMPLETED":
                        self.wave_station = s_stage
                self.update_status()

                try:
                    sidebar = self.query_one("#sidebar", Sidebar)
                    sidebar.session_id = self.session_id
                    tokens_reais = int(session_data.get("tokens", 0) or 0)
                    custo_real = float(session_data.get("cost", 0) or 0)
                    sidebar.update_metrics(
                        title=session_data.get("title"),
                        directory=self.project_dir,
                        tokens=tokens_reais,
                        percent=min(100, int(tokens_reais / 128_000 * 100)),
                        cost=custo_real,
                    )
                except NoMatches:
                    pass
            except (OSError, RuntimeError) as exc:
                chat = self.query_one("#chat-view", ChatView)
                await chat.mount(
                    Static(
                        f"[{TOKENS['error']}]Erro ao conectar ao servidor: {exc}[/{TOKENS['error']}]"
                    )
                )
                return

        await self._load_history()
        self._sse_task = asyncio.create_task(self._listen_sse())
        try:
            self._processing_bar = self.query_one("#processing-status-bar", ThinkingWidget)
        except NoMatches:
            pass
        try:
            self.query_one("#prompt-input", PromptInput).focus()
        except NoMatches:
            pass

    async def on_unmount(self) -> None:
        os.environ.pop("BOMBE_TUI_RUNNING", None)
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()

    async def _load_history(self) -> None:
        if not self.session_id:
            return
        chat = self.query_one("#chat-view", ChatView)
        try:
            history = await self.client.get_history(self.session_id)
            partes_puladas = 0
            for msg in history:
                role = msg.get("role", "user")
                prefix = (
                    f"[{TOKENS['primary']} bold]Você:[/{TOKENS['primary']} bold]\n"
                    if role == "user"
                    else f"[{TOKENS['secondary']} bold]Agente:[/{TOKENS['secondary']} bold]\n"
                )
                await chat.mount(Static(prefix))
                for part in msg.get("parts", []):
                    # ISOLAMENTO POR PARTE: uma parte antiga com markup cru
                    # (eras anteriores à fuga de escape) é PULADA — jamais
                    # derruba o boot da TUI.
                    try:
                        await chat.mount(PartWidget(part))
                    except Exception as exc:  # noqa: BLE001
                        partes_puladas += 1
                        logger.debug("Parte de histórico pulada (markup inválido): %s", exc)
            if partes_puladas:
                logger.warning(
                    "%d parte(s) do histórico puladas por markup inválido", partes_puladas
                )
            if not history:
                lines = [
                    f"[{TOKENS['primary']} bold]╔════════════════════════════════════════════════════════════════╗[/{TOKENS['primary']} bold]",
                    f"[{TOKENS['primary']} bold]║                    ⚡ BOMBE CODE RUNTIME ⚡                    ║[/{TOKENS['primary']} bold]",
                    f"[{TOKENS['primary']} bold]╚════════════════════════════════════════════════════════════════╝[/{TOKENS['primary']} bold]",
                    "",
                    f"[bold]Modo:[/] {self.mode} | [bold]Etapa:[/] {self.wave_station} | [bold]Autonomia:[/] AUTO | [bold]Workspace:[/] {self.project_dir}",
                    "",
                    f"[{TOKENS['secondary']} bold]Comandos da ONDA de Engenharia:[/{TOKENS['secondary']} bold]",
                    "  • [cyan]/wave discuss <demanda>[/cyan] [dim]- Concepção, viabilidade (@meira) e PRD (@grace)[/dim]",
                    "  • [cyan]/wave plan[/cyan]             [dim]- Arquitetura (@ieru, @codd) e decomposição PBB (@caroli)[/dim]",
                    "  • [cyan]/wave execute[/cyan]          [dim]- Implementação TDD fullstack (@barbara, @ada, @fowler)[/dim]",
                    "  • [cyan]/wave validate[/cyan]         [dim]- Homologação e testes E2E (@edith, @nina)[/dim]",
                    "  • [cyan]/wave status[/cyan]           [dim]- Status da ONDA ativa, gates de qualidade e Kanban[/dim]",
                    "  • [cyan]/wave resume[/cyan]           [dim]- Retoma a ONDA exatamente do checkpoint onde parou[/dim]",
                    "  • [cyan]/wave audit [ONDA-xxx][/cyan] [dim]- Contra-Auditoria Forense do validate (@hoare)[/dim]",
                    "",
                    "[dim]Copiar: F2 copia tudo | Selecione com o mouse + F3 copia trecho | Shift+Tab: modo (VIBE FLOW / VIBE CODE) | /help: comandos[/dim]",
                ]
                await chat.mount(Static("\n".join(lines)))
            chat.scroll_to_latest()
        except (OSError, RuntimeError, httpx.HTTPError) as exc:
            logger.warning("Falha ao carregar histórico: %s", exc)

    async def on_prompt_input_submitted(self, event: PromptInput.Submitted) -> None:
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
            self._run_slash_command_worker(text)
            return

        lines = text.splitlines()
        if len(lines) > 8:
            preview = escape("\n".join(lines[:5]))
            formatted_text = f"{preview}\n[dim]... (+{len(lines) - 5} linhas coladas)[/dim]"
        else:
            formatted_text = escape(text)

        await chat.mount(
            Static(f"\n[{TOKENS['primary']} bold]Você:[/{TOKENS['primary']} bold] {formatted_text}")
        )
        chat.scroll_to_latest()

        # No modo TDD, toda entrada de texto livre passa obrigatoriamente pelo Motor de Intenções do Turing
        if self.mode == "TDD":
            from pathlib import Path

            from ..turing.waiter import TuringWaiter

            waiter = TuringWaiter()
            prd_file = Path(self.project_dir) / "docs" / "briefings" / "PRD.md"
            is_greenfield = "DISCOVERY" in self.get_current_wave_stages() or not prd_file.exists()
            action = await waiter.attend(text, stage=self.wave_station, is_greenfield=is_greenfield)

            if action.command and action.command.startswith("/"):
                first_line_cmd = action.command.splitlines()[0][:100]
                await chat.mount(
                    Static(
                        f"[{TOKENS['secondary']} bold]🎯 [TURING MOTOR DE INTENÇÕES - {action.intention.upper()}][/]\n"
                        f"[dim]Roteando deterministicamente para o comando da ONDA: {first_line_cmd}[/dim]"
                    )
                )
                chat.scroll_to_latest()
                self._run_slash_command_worker(action.command)
                return

        self._is_active_turn = True
        self.update_status()

        # Inicia prompt no background worker
        self._run_prompt_worker(text)

    @work(exclusive=True)
    async def _run_prompt_worker(self, text: str) -> None:
        try:
            model_to_send = self.model_name if self.model_name != "padrão" else None
            await self.client.send_prompt(
                self.session_id, text, model=model_to_send, stage=self.wave_station
            )

        except (OSError, RuntimeError, httpx.HTTPError) as exc:
            chat = self.query_one("#chat-view", ChatView)
            if isinstance(exc, httpx.TimeoutException):
                err_msg = f"Tempo limite de resposta esgotado ({type(exc).__name__}). O modelo pode estar sobrecarregado ou gerando uma resposta longa."
            else:
                err_msg = str(exc).strip() or type(exc).__name__
            await chat.mount(
                Static(f"[{TOKENS['error']}]Erro ao enviar prompt: {err_msg}[/{TOKENS['error']}]")
            )
        finally:
            self._is_active_turn = False
            if self._processing_bar is not None:
                self._processing_bar.stop()
            self.update_status()

    @work(exclusive=False)
    async def _run_slash_command_worker(self, text: str) -> None:
        from .commands import handle_slash_command

        chat = self.query_one("#chat-view", ChatView)
        self._is_active_turn = True
        cmd_name = text.split()[0] if text else "comando"
        if self._processing_bar is not None:
            self._processing_bar.start(f"Executando {cmd_name} da ONDA...")
        self.update_status()
        try:
            await handle_slash_command(self, text)
        except Exception as exc:
            from ..errors import record_exception

            err_file = record_exception(exc, context=f"slash_command: {text[:100]}")
            logger.exception("Erro ao processar slash command '%s'", text[:100])
            await chat.mount(
                Static(
                    f"[{TOKENS['error']} bold]❌ Erro ao executar '{cmd_name}':[/{TOKENS['error']} bold] "
                    f"[{TOKENS['error']}]{exc}[/{TOKENS['error']}]\n"
                    f"[dim]Detalhes técnicos gravados em: {err_file}[/dim]"
                )
            )
        finally:
            self._is_active_turn = False
            if self._processing_bar is not None:
                self._processing_bar.stop()
            self.update_status()

    async def _listen_sse(self) -> None:
        if not self.session_id:
            return
        last_id = 0
        while True:
            try:
                async for event in self.client.stream_events(
                    self.session_id, last_event_id=last_id
                ):
                    ev_id = event.get("_event_id")
                    if ev_id:
                        last_id = ev_id
                    await self._handle_event(event)
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001 — reconexão SSE resiliente por design
                logger.debug("Reconectando SSE após erro: %s", exc)
                await asyncio.sleep(1.0)

    async def _handle_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type")
        chat = self.query_one("#chat-view", ChatView)

        if etype == "prompt.started":
            self._is_active_turn = True
            self._current_assistant_text = ""
            self._current_assistant_widget = None
            self._current_reasoning_text = ""
            self._current_reasoning_widget = None
            if self._processing_bar is not None:
                self._processing_bar.start("Processando contexto e aguardando tokens do modelo")
            self.update_status()
            await chat.mount(
                Static(f"\n[{TOKENS['secondary']} bold]Agente:[/{TOKENS['secondary']} bold]")
            )
            chat.scroll_to_latest()

        elif etype == "reasoning-delta":
            if self._processing_bar is not None:
                self._processing_bar.set_message("Raciocinando / Analisando contexto")
            delta = event.get("text", "")
            self._current_reasoning_text += delta
            if self._current_reasoning_widget is None:
                self._current_reasoning_widget = PartWidget(
                    {"type": "reasoning", "text": self._current_reasoning_text}
                )
                await chat.mount(self._current_reasoning_widget)
            else:
                self._current_reasoning_widget.update_stream(self._current_reasoning_text)
            chat.seguir()

        elif etype == "text-delta":
            if self._current_reasoning_widget is not None:
                self._current_reasoning_widget.finalize_stream()
                self._current_reasoning_widget = None
            if self._processing_bar is not None:
                self._processing_bar.set_message("Recebendo resposta da LLM")

            delta = event.get("text", "")
            self._current_assistant_text += delta
            if self._current_assistant_widget is None:
                self._current_assistant_widget = PartWidget(
                    {"type": "text", "text": self._current_assistant_text}
                )
                await chat.mount(self._current_assistant_widget)
            else:
                self._current_assistant_widget.update_stream(self._current_assistant_text)
            chat.seguir()

        elif etype in ("tool-call", "tool-input"):
            tool_name = event.get("tool", "ferramenta")
            # Arquivo gravado/editado pela sessão → sidebar (projetos sem git)
            if any(k in tool_name.lower() for k in ("write", "edit", "apply")):
                args_ev = event.get("arguments") or {}
                caminho = ""
                if isinstance(args_ev, dict):
                    caminho = str(args_ev.get("path") or args_ev.get("file_path") or "")
                elif isinstance(args_ev, str):
                    import json as _json

                    try:
                        dados = _json.loads(args_ev)
                        caminho = str(dados.get("path") or dados.get("file_path") or "")
                    except (ValueError, TypeError):
                        caminho = ""
                if caminho:
                    try:
                        sidebar = self.query_one("#sidebar", Sidebar)
                        sidebar.registrar_arquivo(caminho)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("Sidebar indisponível para arquivo: %s", exc)
            if self._processing_bar is not None:
                self._processing_bar.set_message(f"Executando ferramenta: {tool_name}")
            if self._current_reasoning_widget is not None:
                self._current_reasoning_widget.finalize_stream()
                self._current_reasoning_widget = None
            if self._current_assistant_widget is not None:
                self._current_assistant_widget.finalize_stream()
                self._current_assistant_widget = None

            widget = PartWidget(
                {
                    "type": "tool",
                    "tool": tool_name,
                    "state": "running",
                    "arguments": event.get("arguments", {}),
                }
            )
            await chat.mount(widget)
            chat.seguir()

        elif etype == "tool-result":
            if self._processing_bar is not None:
                self._processing_bar.set_message("Processando resultado da ferramenta")
            widget = PartWidget(
                {
                    "type": "tool",
                    "tool": event.get("tool", "ferramenta"),
                    "state": "error" if event.get("error") else "completed",
                    "output": event.get("output", "") or event.get("error", ""),
                }
            )
            await chat.mount(widget)
            chat.seguir()

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
            if self._processing_bar is not None:
                self._processing_bar.stop()
            if self._current_reasoning_widget is not None:
                self._current_reasoning_widget.finalize_stream()
                self._current_reasoning_widget = None
            if self._current_assistant_widget is not None:
                self._current_assistant_widget.finalize_stream()
                self._current_assistant_widget = None
            self._is_active_turn = False
            self.update_status()

        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            if etype == "usage":
                # USO REAL do provedor (zera a estimativa por deltas)
                total = int(event.get("input_tokens", 0) or 0) + int(
                    event.get("output_tokens", 0) or 0
                )
                if total:
                    sidebar.tokens_count = total
                    sidebar.context_percent = min(100, int(total / 128_000 * 100))
                    sidebar.refresh_view()
            elif etype in ("text-delta", "reasoning-delta"):
                # estimativa leve apenas ENTRE chunks (o evento usage corrige)
                delta_text = event.get("text", "")
                if delta_text:
                    if sidebar.tokens_count == 0:
                        sidebar.tokens_count += max(1, len(delta_text) // 4)
                        sidebar.context_percent = min(
                            100, int((sidebar.tokens_count / 128_000) * 100)
                        )
                    sidebar.refresh_view()
            elif etype in ("tool-result", "prompt.finished"):
                sidebar.refresh_view()
        except NoMatches:
            pass

    _last_escape_ts: float = 0.0

    def _atualizar_titulo(self) -> None:
        """Título da ABA do terminal: 'BC | <Projeto> - Onda <id> - <Nome>'.

        Projeto = nome salvo no project configure (.bombeconfig). Onda ativa =
        wave_state do banco; Nome da Onda = tabela de ondas do PRD
        (docs/briefings/PRD.md). Sem projeto configurado: 'BC | Projeto sem
        nome'. Sem onda: só o projeto. A sequência OSC 2 é emitida DIRETO no
        stdout (invisível ao renderer — mesmo mecanismo do setTerminalTitle
        do opencode original)."""
        try:
            from bombe_code.config.project_config import ProjectConfigManager

            mgr = ProjectConfigManager(self.project_dir)
            projeto = ""
            if mgr.config_path.is_file():
                projeto = (mgr.load().name or "").strip()

            wave_id, wave_nome = "", ""
            import sqlite3 as _sq

            db_path = Path(self.project_dir) / ".bombe-code" / "state.db"
            if db_path.exists():
                con = _sq.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1.0)
                try:
                    linha = con.execute("SELECT wave_id FROM wave_state LIMIT 1").fetchone()
                    wave_id = (linha[0] if linha else "") or ""
                finally:
                    con.close()
            if wave_id:
                prd = Path(self.project_dir) / "docs" / "briefings" / "PRD.md"
                if prd.exists():
                    cache = getattr(self, "_titulo_wave_cache", ("", ""))
                    if cache[0] != wave_id:
                        from bombe_code.domain.wave.sequencer import WaveSequencer

                        achado = next(
                            (
                                plano
                                for plano in WaveSequencer.from_markdown(
                                    prd.read_text(encoding="utf-8", errors="replace")
                                )
                                if plano.wave_id == wave_id
                            ),
                            None,
                        )
                        self._titulo_wave_cache = (wave_id, (achado.name if achado else ""))
                    wave_nome = self._titulo_wave_cache[1]

            titulo = f"BC | {projeto}" if projeto else "BC | Projeto sem nome"
            if wave_id:
                titulo += f" - Onda {wave_id}"
                if wave_nome:
                    titulo += f" - {wave_nome}"

            self.title = titulo
            import sys as _sys

            _sys.stdout.write(f"\x1b]2;{titulo}\x07")
            _sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001 — título é cosmético
            logger.debug("Título do terminal não definido: %s", exc)

    def _chat_view(self) -> ChatView | None:
        try:
            return self.query_one("#chat-view", ChatView)
        except Exception:  # noqa: BLE001 — tela pode não estar montada
            return None

    def action_chat_page_up(self) -> None:
        chat = self._chat_view()
        if chat:
            chat.pagina("up")

    def action_chat_page_down(self) -> None:
        chat = self._chat_view()
        if chat:
            chat.pagina("down")

    def action_chat_page_top(self) -> None:
        chat = self._chat_view()
        if chat:
            chat.pagina("top")

    def action_chat_page_bottom(self) -> None:
        chat = self._chat_view()
        if chat:
            chat.pagina("bottom")

    # ── SELEÇÃO/COPY (clonado do opencode original, util/selection.ts + app.tsx):
    # o app É dono da seleção: mouse-up copia (copy-on-select); Ctrl+C com
    # seleção copia A SELEÇÃO (nunca despeja a transcrição por cima); ESC com
    # seleção só limpa a seleção. Clipboard: driver do app + cadeia Linux.
    def on_mouse_up(self, event: Any) -> None:
        """MOUSE-UP PASSIVO: seleção livre e estável. Soltar o mouse NÃO copia
        nem limpa a seleção — o usuário seleciona normalmente o trecho desejado
        e pressiona F3 para copiar a seleção (ou F2 para copiar a transcrição inteira)."""
        pass

    def action_copiar_selecao(self) -> None:
        """F3: Copia EXCLUSIVAMENTE o texto selecionado na tela.
        Se nada estiver selecionado, avisa com elegância sem falhar."""
        copiou = self._copiar_selecao()
        if not copiou:
            self.notify(
                "Nenhum texto selecionado. Selecione com o mouse e aperte F3.",
                severity="warning",
                timeout=3,
            )

    def _copiar_selecao(self) -> bool:
        """Copia a seleção ativa do screen. Retorna True se havia seleção."""
        texto = ""
        try:
            texto = self.screen.get_selected_text() or ""
        except Exception:  # noqa: BLE001 — screen pode não ter seleção
            texto = ""
        if not texto.strip():
            try:
                selecoes = dict(getattr(self.screen, "selections", {}) or {})
            except Exception:  # noqa: BLE001
                selecoes = {}
            if selecoes:
                try:
                    strips = self.screen._compositor.render_strips()
                    texto = "\n".join(
                        "".join(seg.text for seg in strip) for strip in strips
                    ).rstrip()
                except Exception:  # noqa: BLE001 — fallback é best-effort
                    texto = ""
        if not texto.strip():
            return False
        self.action_copiar_tela_de(texto)
        self.notify(f"📋 Trecho copiado ({len(texto)} caracteres)", severity="information", timeout=2)
        return True

    def action_copy_or_quit(self) -> None:
        """CTRL+C: Interrompe ou sai com 2x aperto. Não interfere nas cópias (F2/F3)."""
        import time as _t

        from bombe_code.turing.progress import ABORT_EVENT

        agora = _t.monotonic()
        anterior = getattr(self, "_last_ctrl_c_ts", 0.0)
        if agora - anterior <= 1.8:
            self._last_ctrl_c_ts = 0.0
            if self._is_active_turn:
                ABORT_EVENT.set()  # workers salvam checkpoint e terminam
            self.exit()
            return
        self._last_ctrl_c_ts = agora
        self.notify(
            "F2 copia tudo | Selecione + F3 trecho | 2× Ctrl+C sai",
            severity="information",
            timeout=3,
        )

    def action_copiar_tela(self) -> None:
        """Copia a transcrição inteira como TEXTO PURO (sem tags de cor/markup,
        exatamente igual à extração limpa do F3): driver nativo + cadeia Linux."""
        import re
        from rich.text import Text

        chat = self.query_one("#chat-view", ChatView)
        blocos: list[str] = []
        for w in chat.children:
            # Obtém a representação crua
            raw = getattr(w, "renderable", None) or getattr(w, "content", None)
            if hasattr(raw, "plain"):
                conteudo = str(raw.plain)
            else:
                conteudo = str(raw or "")
            if not conteudo.strip():
                continue
            # 1. Converte Rich markup para texto puro (remove [#89b4fa], [bold], etc.)
            try:
                limpo = Text.from_markup(conteudo).plain
            except Exception:
                limpo = conteudo
            # 2. Remove sequências de escape ANSI se houver
            limpo = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", limpo)
            # 3. Remove quaisquer tags de markup remanescentes [tag] ou [/tag]
            limpo = re.sub(r"\[/?[a-zA-Z0-9_#=, -]+\]", "", limpo)
            blocos.append(limpo.strip())

        texto_puro = "\n\n".join(blocos).strip()
        self.action_copiar_tela_de(texto_puro)

    def action_copiar_tela_de(self, texto: str) -> None:
        """Copia o texto dado para o clipboard (mesma cadeia de drivers)."""
        import subprocess

        try:
            self.copy_to_clipboard(texto)
        except Exception as exc:  # noqa: BLE001 — driver pode não suportar
            logger.debug("copy_to_clipboard indisponível: %s", exc)
        try:
            import pyperclip

            pyperclip.copy(texto)
        except Exception as exc:  # noqa: BLE001 — pyperclip é redundância
            logger.debug("pyperclip indisponível: %s", exc)
        for cmd in (
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
            ["wl-copy"],
        ):
            try:
                proc = subprocess.run(
                    cmd,
                    input=texto.encode("utf-8"),
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if proc.returncode == 0:
                    break
            except (OSError, subprocess.TimeoutExpired):
                continue
        self.notify(f"📋 Copiado ({len(texto)} caracteres)", severity="information")

    async def action_escape_press(self) -> None:
        """ESCAPE DUPLO (janela 1.8s) = interromper. ESC único = dica."""
        import time as _t

        agora = _t.monotonic()
        if agora - self._last_escape_ts <= 1.8:
            self._last_escape_ts = 0.0
            await self.action_interrupt()
            return
        self._last_escape_ts = agora
        chat = self.query_one("#chat-view", ChatView)
        await chat.mount(Static("[dim]⏸ pressione ESC novamente para interromper o fluxo[/dim]"))

    async def action_interrupt(self) -> None:
        """Interrompe DE VERDADE: bandeira global aborta agentes/etapas + server."""
        from bombe_code.turing.progress import ABORT_EVENT

        ABORT_EVENT.set()
        if self.session_id and self._is_active_turn:
            try:
                await self.client.interrupt(self.session_id)
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                logger.warning("Erro ao interromper turno: %s", exc)
            finally:
                self._is_active_turn = False
                if self._processing_bar is not None:
                    self._processing_bar.stop()
        chat = self.query_one("#chat-view", ChatView)
        await chat.mount(
            Static(
                f"[{TOKENS['warning']}]⏸ Interrupção solicitada (ESC ESC) — agentes encerram na "
                f"próxima fronteira e o checkpoint fica salvo.[/{TOKENS['warning']}]"
            )
        )

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

    def action_quit(self) -> None:
        """Encerra a aplicação garantindo o cancelamento de tarefas em background."""
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
        self.exit()

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
        self._exit_renderables.append(Segments(self.console.render(panel, self.console.options)))
        self._close_messages_no_wait()
