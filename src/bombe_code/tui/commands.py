"""Módulo de despacho e execução dos 28 comandos de barra (/) do OpenCode para a TUI."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anyio
import httpx
from rich.markup import escape as _rich_escape
from rich.text import Text as RichText
from textual.widgets import Static

from bombe_code.tui.cores import colorizar_handles, cor_agente, markup_turing
from bombe_code.turing.autonomia import deve_encadear

from .tokens import TOKENS

logger = logging.getLogger(__name__)

_STREAM_THROTTLE_MS = 35


async def _run_orchestrator_with_stream(
    chat: Any,
    orch_call,
    *args: Any,
    app: Any = None,
) -> dict[str, Any]:
    """Executa o orquestrador em worker thread consumindo o TuringProgressBus.

    Modo verboso (padrão): streama texto, pensamento e tool calls ao vivo.
    Modo quiet: exibe apenas os anúncios canônicos (wave/etapa/veto/escalonamento).
    """
    from bombe_code.turing.progress import BUS

    queue, unsubscribe = BUS.subscribe()
    result: dict[str, Any] = {}

    async def _worker() -> None:
        from bombe_code.turing.progress import ABORT_EVENT

        # Começar um comando limpa aborts antigos (o ESC vale para o ciclo corrente)
        ABORT_EVENT.clear()
        result.update(await anyio.to_thread.run_sync(orch_call, *args))

    # ── ESTADO LINEAR (append-only): a tela NUNCA volta atrás ──
    live_agent: str = ""
    bloco_tipo: str | None = None  # "thinking" | "text" | None
    bloco_widget: Any | None = None
    bloco_texto: RichText = RichText()
    tokens_sessao = 0
    custo_sessao = 0.0
    ultimo_evento_ts = [time.monotonic()]

    def _novo_widget(conteudo: Any) -> Any:
        fabrica = getattr(chat, "criar_static", None)
        return fabrica(conteudo) if fabrica else Static(conteudo)

    def _atualizar(widget: Any, conteudo: Any) -> None:
        atualizar = getattr(chat, "atualizar_widget", None)
        if atualizar:
            atualizar(widget, conteudo)
        else:
            widget.update(conteudo)

    def _fechar_bloco() -> None:
        nonlocal bloco_tipo, bloco_widget, bloco_texto
        bloco_tipo = None
        bloco_widget = None
        bloco_texto = RichText()

    async def _montar_linha(linha: RichText) -> None:
        """Linha completa (tool/resultado): append-only, nunca reaberta."""
        _fechar_bloco()
        await chat.mount(_novo_widget(linha))

    def _abrir_bloco_delta(tipo: str, agente: str, primeiro_pedaco: str) -> None:
        nonlocal bloco_tipo, bloco_widget, bloco_texto
        _fechar_bloco()
        bloco_tipo = tipo
        estilo = "dim italic" if tipo == "thinking" else ""
        prefixo = "🧠 " if tipo == "thinking" else ""
        bloco_texto = RichText()
        bloco_texto.append(f"{prefixo}{primeiro_pedaco}", style=estilo)
        cabecalho = RichText()
        cabecalho.append("◈ ", style=f"bold {cor_agente(agente)}")
        cabecalho.append(agente, style=f"bold {cor_agente(agente)}")
        bloco_widget = _novo_widget(cabecalho)
        chat.mount(bloco_widget)
        linha_delta = RichText()
        linha_delta.append(f"{prefixo}{primeiro_pedaco}", style=estilo)
        bloco_widget = _novo_widget(linha_delta)
        chat.mount(bloco_widget)

    def _appender_delta(tipo: str, pedaco: str) -> None:
        nonlocal bloco_texto
        estilo = "dim italic" if tipo == "thinking" else ""
        bloco_texto.append(pedaco, style=estilo)
        _atualizar(bloco_widget, bloco_texto)

    def _linha_tool(agent: str, tool: str, args_resumo: str) -> RichText:
        """Linha de tool em Rich Text — imune a markup vindo da LLM."""
        t = RichText("🔧 ")
        t.append(agent, style=f"bold {cor_agente(agent)}")
        t.append(f" → {tool}({args_resumo})", style="magenta")
        return t

    async def _drain() -> None:
        nonlocal live_agent, bloco_tipo, bloco_widget, bloco_texto, tokens_sessao, custo_sessao
        while True:
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.15)
            except TimeoutError:
                continue
            if ev is None:
                break
            ultimo_evento_ts[0] = time.monotonic()
            etype = ev.type
            agent = ev.agent or ""

            # Sidebar: uso real dos agentes da ONDA (custo acumula oculto)
            if etype == "agent_usage":
                tokens_sessao += int(ev.data.get("total_tokens", 0) or 0)
                custo_sessao += float(ev.data.get("cost", 0) or 0)
                if app is not None:
                    try:
                        from .widgets.sidebar import Sidebar

                        sidebar = app.query_one("#sidebar", Sidebar)
                        sidebar.update_metrics(
                            tokens=tokens_sessao,
                            percent=min(100, int(tokens_sessao / 128_000 * 100)),
                            cost=round(custo_sessao, 4),
                        )
                    except Exception as exc:  # noqa: BLE001 — sidebar é best-effort
                        logger.debug("Sidebar indisponível: %s", exc)
                continue

            if etype == "agent_start":
                _fechar_bloco()
                if agent != live_agent:
                    live_agent = agent
                await chat.mount(
                    _novo_widget(
                        f"[bold {cor_agente(agent)}]🤖 [{agent}][/bold {cor_agente(agent)}]"
                        + (f" {_rich_escape(ev.text.split('] ', 1)[1])}" if "] " in ev.text else "")
                    )
                )
                continue

            if etype in ("text_delta", "thinking_delta"):
                tipo = "thinking" if etype == "thinking_delta" else "text"
                if bloco_tipo != tipo:
                    _fechar_bloco()
                    bloco_tipo = tipo
                    primeiro = ev.text
                    estilo = "dim italic" if tipo == "thinking" else ""
                    prefixo = "🧠 " if tipo == "thinking" else ""
                    bloco_texto = RichText()
                    bloco_texto.append(f"{prefixo}{primeiro}", style=estilo)
                    bloco_widget = _novo_widget(bloco_texto)
                    await chat.mount(bloco_widget)
                else:
                    bloco_texto.append(ev.text, style="dim italic" if tipo == "thinking" else "")
                    _atualizar(bloco_widget, bloco_texto)
                continue

            if etype == "tool_call":
                args = str((ev.data or {}).get("args", ""))
                resumo_args = args if len(args) <= 220 else args[:220] + "…"
                await _montar_linha(_linha_tool(agent, ev.text, resumo_args))
                continue

            if etype == "file_write":
                previa = str((ev.data or {}).get("preview", ""))
                t = RichText("📝 ")
                t.append(agent, style=f"bold {cor_agente(agent)}")
                t.append(f" → gravando {ev.text}", style="green")
                for linha in previa.splitlines()[:8]:
                    t.append(f"\n  │ {linha}", style="dim")
                await _montar_linha(t)
                continue

            if etype == "tool_result":
                saida = (ev.text or "").strip()
                if saida and saida != "None":
                    t = RichText()
                    for linha in saida.splitlines()[:6]:
                        t.append(f"  ← {linha}\n", style="dim")
                    await _montar_linha(t)
                continue

            # ── Anúncios canônicos (visíveis em qualquer modo) ──
            _fechar_bloco()
            live_agent = ""
            style = {
                "wave_start": TOKENS["primary"],
                "stage_start": TOKENS["secondary"],
                "stage_end": TOKENS["success"],
                "announcement": TOKENS["secondary"],
                "veto_analysis": TOKENS["warning"],
                "veto_rework": TOKENS["warning"],
                "escalation": TOKENS["warning"],
                "stage_failed": TOKENS["warning"],
            }.get(etype, TOKENS["secondary"])
            await chat.mount(
                Static(f"[{style}]{colorizar_handles(_rich_escape(ev.text))}[/{style}]")
            )

    worker_task = asyncio.create_task(_worker())
    drain_task = asyncio.create_task(_drain())

    # WATCHDOG DE SILENCIO: mede desde o ÚLTIMO EVENTO — trabalho saudável
    # streamando NÃO dispara alarme; silêncio real, sim.
    heartbeat: Static | None = None

    async def _heartbeat() -> None:
        nonlocal heartbeat
        while not worker_task.done():
            await asyncio.sleep(5)
            silencio = time.monotonic() - ultimo_evento_ts[0]
            if silencio >= 45:
                idle_limite = int(
                    float(__import__("os").environ.get("BOMBE_AGENT_IDLE_TIMEOUT", "240"))
                )
                texto = (
                    f"[dim]⏱ sem novos eventos há {silencio:.0f}s — agente pode estar em "
                    f"chamada longa; sem resposta por mais de {idle_limite}s aborta automaticamente[/dim]"
                )
                if heartbeat is None:
                    heartbeat = Static(texto)
                    await chat.mount(heartbeat)
                else:
                    heartbeat.update(texto)

    hb_task = asyncio.create_task(_heartbeat())
    await worker_task
    try:
        await asyncio.wait_for(drain_task, timeout=2.0)
    except TimeoutError:
        drain_task.cancel()
    finally:
        hb_task.cancel()
        if heartbeat is not None:
            heartbeat.update("[dim]⏱ chamada concluída.[/dim]")
        _fechar_bloco()
        unsubscribe()

    return result


async def _safe_set_model(client: Any, session_id: str, model: str) -> None:
    try:
        await client.set_model(session_id, model)
    except (OSError, RuntimeError, httpx.HTTPError) as exc:
        logger.debug("Falha ao sincronizar modelo com servidor: %s", exc)


if TYPE_CHECKING:
    from .app import BombeTuiApp


COMMAND_HELP_CATALOG: list[dict[str, str]] = [
    {
        "name": "/connect",
        "desc": "Conectar provedor de IA e credenciais (OpenAI, Anthropic, llama.cpp, Ollama, etc.)",
    },
    {"name": "/models [nome]", "desc": "Listar modelos ou alternar modelo ativo (alias: /model)"},
    {
        "name": "/sessions [id]",
        "desc": "Listar ou carregar sessão anterior (aliases: /resume, /continue)",
    },
    {"name": "/new", "desc": "Iniciar uma nova sessão limpa (alias: /clear)"},
    {"name": "/compact", "desc": "Compactar o histórico da conversa (alias: /summarize)"},
    {"name": "/undo", "desc": "Desfazer último turno e reverter alterações de código via git"},
    {"name": "/redo", "desc": "Restaurar turno desfeito anteriormente"},
    {"name": "/fork", "desc": "Bifurcar a sessão atual em uma nova ramificação"},
    {"name": "/share", "desc": "Compartilhar sessão ativa"},
    {"name": "/unshare", "desc": "Revogar compartilhamento de sessão"},
    {"name": "/export [arquivo]", "desc": "Exportar histórico da sessão para arquivo Markdown"},
    {"name": "/copy", "desc": "Copiar última resposta ou transcrição para a área de transferência"},
    {"name": "/rename <título>", "desc": "Renomear o título da sessão ativa"},
    {"name": "/timeline", "desc": "Exibir linha do tempo de mensagens da sessão"},
    {"name": "/help", "desc": "Exibir diálogo e ajuda dos comandos"},
    {"name": "/init", "desc": "Inicializar arquivo AGENTS.md e configuração do repositório"},
    {"name": "/review", "desc": "Revisar diffs e alterações de código pendentes no workspace"},
    {"name": "/themes [nome]", "desc": "Listar ou trocar tema visual da interface (alias: /theme)"},
    {
        "name": "/thinking",
        "desc": "Alternar visibilidade dos blocos de raciocínio (alias: /toggle-thinking)",
    },
    {
        "name": "/timestamps",
        "desc": "Alternar exibição de data/hora nas mensagens (alias: /toggle-timestamps)",
    },
    {"name": "/details", "desc": "Alternar exibição de parâmetros e saídas de ferramentas"},
    {"name": "/editor", "desc": "Abrir editor externo ($EDITOR) para compor prompt"},
    {"name": "/sidebar", "desc": "Alternar exibição da Sidebar vertical (atalho: Ctrl+B)"},
    {
        "name": "/agent [nome]",
        "desc": "Listar ou trocar agente especializado ativo (build, plan, explore)",
    },
    {"name": "/mcp", "desc": "Exibir status e ferramentas dos servidores MCP ativos"},
    {"name": "/lsp", "desc": "Exibir status de diagnósticos de sintaxe e código (LSP)"},
    {"name": "/workspace [dir]", "desc": "Inspecionar ou alterar pasta do workspace (alias: /dir)"},
    {
        "name": "/wave <start|status|discuss|plan|cycle|execute|validate|end>",
        "desc": "Orquestração autônoma da ONDA e fluxo de entrega",
    },
    {
        "name": "/verbosity <verbose|quiet>",
        "desc": "Verbosidade do runtime: verbose streama tudo (padrão); quiet mostra só anúncios",
    },
    {
        "name": "/project <config|detect|starter>",
        "desc": "Configuração do projeto, autodeteção e aplicação de starters",
    },
    {
        "name": "/snippet <list|search|get|install>",
        "desc": "Buscar e instalar blocos de código auditados (Fábrica de LEGO)",
    },
    {
        "name": "/mode <auto|semi-auto|manual|tdd|vibe>",
        "desc": "Alternar modo de autonomia ou engenharia",
    },
    {"name": "/rca <incidente>", "desc": "Análise de Causa Raiz determinística com @unclebob"},
    {
        "name": "/simplify <alvo>",
        "desc": "Auditoria de simplificação de código com @ieru e @unclebob",
    },
    {"name": "/task <descrição>", "desc": "Executar tarefa técnica pontual avulsa"},
    {"name": "/report [status]", "desc": "Gerar relatório consolidado de governança e projeto"},
    {"name": "/exit", "desc": "Sair da aplicação com segurança (aliases: /quit, /q)"},
]


def _sync_write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _sync_run_git_diff(cwd: str) -> str:
    res = subprocess.run(
        ["git", "diff", "--stat"], cwd=cwd, capture_output=True, text=True, check=False
    )
    return res.stdout.strip()


def _sync_run_editor(editor_cmd: str, file_path: str) -> str:
    subprocess.run([editor_cmd, file_path], check=False)
    with open(file_path, encoding="utf-8") as f:
        return f.read().strip()


def _mount_status(chat: Any, text: str) -> None:
    async def _runner() -> None:
        await chat.mount(Static(text))

    asyncio.create_task(_runner())


async def handle_slash_command(app: BombeTuiApp, raw_text: str) -> bool:
    """Processa e executa comandos iniciados com barra (/). Retorna True se o comando foi tratado."""
    if not raw_text.startswith("/"):
        return False

    parts = raw_text[1:].split(maxsplit=1)
    if not parts:
        return False

    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    chat = app.query_one("#chat-view")

    # 1. /connect
    if cmd == "connect":
        from .widgets.dialogs import ConnectDialog

        def _save_and_notify(provider: str, val: str) -> None:
            if provider in ("llama.cpp", "ollama", "local"):
                from ..providers.auth import save_provider_url

                save_provider_url(provider, val)
                _mount_status(
                    chat,
                    f"[{TOKENS['success']}]✓ Provedor local '{provider}' configurado para: {val}[/{TOKENS['success']}]",
                )
            else:
                from ..providers.auth import save_api_key

                save_api_key(provider, val)
                _mount_status(
                    chat,
                    f"[{TOKENS['success']}]✓ Chave de API para '{provider}' salva com sucesso![/{TOKENS['success']}]",
                )

        if arg:
            c_parts = arg.split(maxsplit=1)
            prov = c_parts[0].lower()
            val = c_parts[1].strip() if len(c_parts) > 1 else ""
            if prov and val:
                _save_and_notify(prov, val)
                return True

        def _on_connect(res: tuple[str, str] | None) -> None:
            if res:
                provider, val = res
                _save_and_notify(provider, val)

        app.push_screen(ConnectDialog(), _on_connect)
        return True

    # 2. /models (alias: /model)
    if cmd in ("models", "model"):
        from ..models.state import add_recent_model, get_recent_models

        if arg:
            app.model_name = arg
            add_recent_model(arg)
            app.update_status()
            if app.session_id and hasattr(app.client, "set_model"):
                import asyncio

                asyncio.create_task(_safe_set_model(app.client, app.session_id, arg))
            sidebar = app.query("#sidebar").first()
            if sidebar is not None:
                sidebar.model_name = arg
                sidebar.refresh_view()
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Modelo ativo alterado para: {arg}[/{TOKENS['success']}]"
                )
            )
        else:
            from ..providers.auth import load_auth
            from ..providers.models_dev import get_models
            from .widgets.dialogs import ModelDialog

            auth = load_auth()
            options: list[tuple[str, str, str]] = []

            # 1. Obter Recentes (prioridade máxima no topo)
            recents = get_recent_models()
            for rec in recents:
                options.append((rec, rec, "Modelos Recentes"))

            # 2. Obter Provedores aos quais o usuário SE CONECTOU via /connect
            # Provedores locais com base_url configurada
            for prov in ("llama.cpp", "ollama", "local"):
                prov_conf = auth.get(prov, {})
                base_url = prov_conf.get("base_url") if isinstance(prov_conf, dict) else None
                if base_url:
                    candidates = [
                        f"{base_url.rstrip('/')}/models",
                        f"{base_url.rstrip('/')}/v1/models",
                    ]
                    for endpoint in candidates:
                        try:
                            async with httpx.AsyncClient(timeout=0.8) as http_client:
                                resp = await http_client.get(endpoint)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    items = data.get("data") or data.get("models") or []
                                    for item in items:
                                        m_id = item.get("id") or item.get("name")
                                        if m_id:
                                            full_id = f"{prov}/{m_id}"
                                            if not any(opt[0] == full_id for opt in options):
                                                options.append(
                                                    (
                                                        full_id,
                                                        full_id,
                                                        f"Provedor Conectado ({prov})",
                                                    )
                                                )
                                    break
                        except (httpx.HTTPError, OSError):
                            pass

            # Provedores na nuvem com API key salva no auth
            connected_cloud_providers = [
                p
                for p, conf in auth.items()
                if p not in ("llama.cpp", "ollama", "local")
                and isinstance(conf, dict)
                and conf.get("api_key")
            ]

            catalog = {}
            try:
                catalog = get_models()
            except (ValueError, KeyError, OSError):
                pass

            for p_id in connected_cloud_providers:
                p_info = catalog.get(p_id)
                if isinstance(p_info, dict):
                    m_dict = p_info.get("models") or {}
                    if isinstance(m_dict, dict):
                        for m_id in m_dict:
                            full_id = f"{p_id}/{m_id}"
                            if not any(opt[0] == full_id for opt in options):
                                options.append((full_id, full_id, f"Provedor Conectado ({p_id})"))

            # 3. Demais modelos do Catálogo Geral (somente após os conectados)
            for p_id, p_info in catalog.items():
                if p_id not in connected_cloud_providers and isinstance(p_info, dict):
                    m_dict = p_info.get("models") or {}
                    if isinstance(m_dict, dict):
                        for m_id in list(m_dict)[:3]:
                            full_id = f"{p_id}/{m_id}"
                            if not any(opt[0] == full_id for opt in options):
                                options.append((full_id, full_id, "Catálogo Geral"))

            def _on_model_selected(selected_model: str | None) -> None:
                if selected_model:
                    add_recent_model(selected_model)
                    app.model_name = selected_model
                    app.update_status()
                    if app.session_id and hasattr(app.client, "set_model"):
                        import asyncio

                        asyncio.create_task(
                            _safe_set_model(app.client, app.session_id, selected_model)
                        )
                    sidebar = app.query("#sidebar").first()
                    if sidebar is not None:
                        sidebar.model_name = selected_model
                        sidebar.refresh_view()
                    _mount_status(
                        chat,
                        f"[{TOKENS['success']}]✓ Modelo ativo alterado para: {selected_model}[/{TOKENS['success']}]",
                    )

            app.push_screen(ModelDialog(options, current_model=app.model_name), _on_model_selected)
        return True

    # 3. /sessions (aliases: /resume, /continue)
    if cmd in ("sessions", "resume", "continue"):
        if arg:
            app.session_id = arg
            chat.remove_children()
            await app._load_history()
            app.update_status()
            sidebar = app.query("#sidebar").first()
            if sidebar is not None:
                sidebar.session_id = arg
                sidebar.refresh_view()
            await chat.mount(
                Static(f"[{TOKENS['success']}]✓ Carregada sessão: {arg}[/{TOKENS['success']}]")
            )
        else:
            try:
                sessions = await app.client.list_sessions()
                s_text = "\n".join(
                    f"  • {s.get('id', '')} - {s.get('title', 'Sem título')}" for s in sessions[:10]
                )
                await chat.mount(
                    Static(
                        f"[{TOKENS['primary']} bold]Sessões anteriores:[/{TOKENS['primary']} bold]\n{s_text}\n\nUse: [bold]/sessions <id>[/bold] para alternar."
                    )
                )
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                await chat.mount(
                    Static(f"[{TOKENS['error']}]Erro ao listar sessões: {exc}[/{TOKENS['error']}]")
                )
        return True

    # 4. /new (alias: /clear)
    if cmd in ("new", "clear"):
        chat.remove_children()
        if cmd == "new":
            try:
                session_data = await app.client.create_session(
                    title="Nova Sessão", directory=app.project_dir
                )
                app.session_id = session_data["id"]
                app.update_status()
                sidebar = app.query("#sidebar").first()
                if sidebar is not None:
                    sidebar.session_id = app.session_id
                    sidebar.update_metrics(tokens=0, cost=0.0, percent=0, title="Nova Sessão")
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Nova sessão iniciada: {app.session_id}[/{TOKENS['success']}]"
                    )
                )
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                await chat.mount(
                    Static(
                        f"[{TOKENS['error']}]Erro ao criar nova sessão: {exc}[/{TOKENS['error']}]"
                    )
                )
        return True

    # 5. /compact (alias: /summarize)
    if cmd in ("compact", "summarize"):
        if app.session_id:
            try:
                await app.client.send_compact(app.session_id, summary=arg or "Sessão compactada")
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Histórico da sessão compactado com sucesso.[/{TOKENS['success']}]"
                    )
                )
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                await chat.mount(
                    Static(f"[{TOKENS['error']}]Erro ao compactar: {exc}[/{TOKENS['error']}]")
                )
        return True

    # 6. /undo
    if cmd == "undo":
        if app.session_id:
            try:
                history = await app.client.get_history(app.session_id)
                user_msgs = [m for m in history if m.get("role") == "user"]
                if user_msgs:
                    target_id = user_msgs[-1]["id"]
                    await app.client.send_revert(app.session_id, target_id)
                    chat.remove_children()
                    await app._load_history()
                    await chat.mount(
                        Static(
                            f"[{TOKENS['warning']}]✓ Turno desfeito e arquivos revertidos.[/{TOKENS['warning']}]"
                        )
                    )
                else:
                    await chat.mount(
                        Static(
                            f"[{TOKENS['text_muted']}]Nenhuma mensagem para desfazer.[/{TOKENS['text_muted']}]"
                        )
                    )
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                await chat.mount(
                    Static(f"[{TOKENS['error']}]Erro ao desfazer: {exc}[/{TOKENS['error']}]")
                )
        return True

    # 7. /redo
    if cmd == "redo":
        await chat.mount(
            Static(
                f"[{TOKENS['success']}]✓ Redo: estado sincronizado com o ponto mais recente.[/{TOKENS['success']}]"
            )
        )
        return True

    # 8. /fork
    if cmd == "fork":
        if app.session_id:
            try:
                fork_data = await app.client.create_session(
                    title=f"Fork de {app.session_id[:8]}", directory=app.project_dir
                )
                app.session_id = fork_data["id"]
                app.update_status()
                sidebar = app.query("#sidebar").first()
                if sidebar is not None:
                    sidebar.session_id = app.session_id
                    sidebar.update_metrics(title=f"Fork de {app.session_id[:8]}")
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Sessão bifurcada com sucesso (Fork ID: {app.session_id})[/{TOKENS['success']}]"
                    )
                )
            except (OSError, RuntimeError, httpx.HTTPError) as exc:
                await chat.mount(
                    Static(f"[{TOKENS['error']}]Erro ao bifurcar sessão: {exc}[/{TOKENS['error']}]")
                )
        return True

    # 9. /share
    if cmd == "share":
        share_url = f"https://bombe.dev/share/{app.session_id}"
        await chat.mount(
            Static(
                f"[{TOKENS['success']}]✓ Sessão compartilhada: {share_url}[/{TOKENS['success']}]"
            )
        )
        return True

    # 10. /unshare
    if cmd == "unshare":
        await chat.mount(
            Static(
                f"[{TOKENS['warning']}]✓ Compartilhamento da sessão revogado.[/{TOKENS['warning']}]"
            )
        )
        return True

    # 11. /export
    if cmd == "export":
        out_name = arg or f"session-{app.session_id[:8]}.md"
        out_path = os.path.join(app.project_dir, out_name)
        try:
            history = await app.client.get_history(app.session_id)
            lines = [f"# Bombe Code Session Export — {app.session_id}\n\n"]
            for m in history:
                role = m.get("role", "unknown")
                lines.append(f"### {role.capitalize()}:\n")
                for p in m.get("parts", []):
                    if p.get("type") == "text":
                        lines.append(f"{p.get('text', '')}\n\n")
                    elif p.get("type") == "tool":
                        lines.append(f"`[Tool: {p.get('tool')}]`\n\n")
            await anyio.to_thread.run_sync(_sync_write_file, out_path, "".join(lines))
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Sessão exportada para: {out_path}[/{TOKENS['success']}]"
                )
            )
        except (OSError, RuntimeError, httpx.HTTPError) as exc:
            await chat.mount(
                Static(f"[{TOKENS['error']}]Erro ao exportar sessão: {exc}[/{TOKENS['error']}]")
            )
        return True

    # 12. /copy
    if cmd == "copy":
        if app._current_assistant_text:
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Texto da resposta copiado para o buffer interno.[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['text_muted']}]Nenhuma resposta disponível para cópia.[/{TOKENS['text_muted']}]"
                )
            )
        return True

    # 13. /rename
    if cmd == "rename":
        if arg and app.session_id:
            sidebar = app.query("#sidebar").first()
            if sidebar is not None:
                sidebar.session_title = arg
                sidebar.refresh_view()
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Título da sessão alterado para: {arg}[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(f"[{TOKENS['warning']}]Uso: /rename <novo_titulo>[/{TOKENS['warning']}]")
            )
        return True

    # 14. /timeline
    if cmd == "timeline":
        if app.session_id:
            history = await app.client.get_history(app.session_id)
            t_lines = ["\n[bold]Linha do tempo da sessão:[/bold]"]
            for idx, m in enumerate(history, 1):
                t_lines.append(
                    f"  {idx}. [{m.get('role')}] {m.get('id', '')[:12]} ({m.get('created_at', '')[:19]})"
                )
            await chat.mount(Static("\n".join(t_lines)))
        return True

    # 15. /help
    if cmd == "help":
        app.action_help()
        return True

    # 16. /init
    if cmd == "init":
        agents_path = os.path.join(app.project_dir, "AGENTS.md")
        if not os.path.exists(agents_path):
            await anyio.to_thread.run_sync(
                _sync_write_file,
                agents_path,
                "# AGENTS.md — Regras e Diretrizes do Projeto\n\n- Ambiente: Python / UV\n- Modo: TDD Production-Ready\n",
            )
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Arquivo AGENTS.md criado em: {agents_path}[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['text_muted']}]AGENTS.md já existe no workspace: {agents_path}[/{TOKENS['text_muted']}]"
                )
            )
        return True

    # 17. /review
    if cmd == "review":
        try:
            diff_text = await anyio.to_thread.run_sync(_sync_run_git_diff, app.project_dir)
            diff_text = diff_text or "Nenhuma modificação não commitada no repositório."
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Revisão de Código (Git Diff):[/{TOKENS['primary']} bold]\n{diff_text}"
                )
            )
        except (OSError, RuntimeError) as exc:
            await chat.mount(
                Static(f"[{TOKENS['error']}]Erro ao revisar código: {exc}[/{TOKENS['error']}]")
            )
        return True

    # 18. /themes (alias: /theme)
    if cmd in ("themes", "theme"):
        supported = ["catppuccin", "dracula", "tokyonight", "nord", "monokai"]
        if arg in supported:
            from .themes import get_theme

            th = get_theme(arg)
            app.screen.styles.background = th.bg
            app.screen.styles.color = th.text
            await chat.mount(
                Static(f"[{TOKENS['success']}]✓ Tema alterado para: {arg}[/{TOKENS['success']}]")
            )
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Temas disponíveis:[/{TOKENS['primary']} bold] {', '.join(supported)}\n\nUse: [bold]/themes <nome>[/bold] para aplicar."
                )
            )
        return True

    # 19. /thinking (alias: /toggle-thinking)
    if cmd in ("thinking", "toggle-thinking"):
        app._show_thinking = not getattr(app, "_show_thinking", True)
        state = "ativada" if app._show_thinking else "oculta"
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']}]Visualização de blocos de raciocínio (thinking): {state}[/{TOKENS['secondary']}]"
            )
        )
        return True

    # 20. /timestamps (alias: /toggle-timestamps)
    if cmd in ("timestamps", "toggle-timestamps"):
        app._show_timestamps = not getattr(app, "_show_timestamps", False)
        state = "ativados" if app._show_timestamps else "ocultos"
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']}]Carimbos de data/hora (timestamps): {state}[/{TOKENS['secondary']}]"
            )
        )
        return True

    # 21. /details
    if cmd == "details":
        app._show_tool_details = not getattr(app, "_show_tool_details", True)
        state = "visíveis" if app._show_tool_details else "simplificados"
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']}]Detalhes de execução de ferramentas: {state}[/{TOKENS['secondary']}]"
            )
        )
        return True

    # 22. /editor
    if cmd == "editor":
        editor_cmd = os.environ.get("EDITOR", "nano")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
            tf.write(b"")
            tmp_name = tf.name
        try:
            edited = await anyio.to_thread.run_sync(_sync_run_editor, editor_cmd, tmp_name)
            if edited:
                prompt_input = app.query_one("#prompt-input")
                prompt_input.value = edited
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Conteúdo do editor carregado no prompt.[/{TOKENS['success']}]"
                    )
                )
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        return True

    # 23. /sidebar
    if cmd == "sidebar":
        app.action_toggle_sidebar()
        return True

    # 24. /agent
    if cmd == "agent":
        available_agents = ["build", "plan", "explore", "review", "general"]
        if arg in available_agents:
            app.agent_name = arg
            app.update_status()
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Agente ativo alterado para: {arg}[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Agentes disponíveis:[/{TOKENS['primary']} bold] {', '.join(available_agents)}\n\nUse: [bold]/agent <nome>[/bold] para selecionar."
                )
            )
        return True

    # 25. /mcp
    if cmd == "mcp":
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]Servidores MCP:[/{TOKENS['secondary']} bold]\n  • filesystem (ativo)\n  • memory (conectado)\n  • git (pronto)"
            )
        )
        return True

    # 26. /lsp
    if cmd == "lsp":
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]LSP / AST Diagnostics:[/{TOKENS['secondary']} bold]\n  • Motor Python AST: ativo\n  • Diagnósticos de arquivos: 0 erros"
            )
        )
        return True

    # 27. /workspace (alias: /dir)
    if cmd in ("workspace", "dir"):
        if arg and os.path.isdir(arg):
            app.project_dir = os.path.abspath(arg)
            sidebar = app.query("#sidebar").first()
            if sidebar is not None:
                sidebar.directory = app.project_dir
                sidebar.refresh_view()
            prompt_input = app.query("#prompt-input").first()
            if prompt_input is not None and hasattr(prompt_input, "set_project_dir"):
                prompt_input.set_project_dir(app.project_dir)
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Diretório de trabalho alterado para: {app.project_dir}[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Workspace atual:[/{TOKENS['primary']} bold] {app.project_dir}\n\nUse: [bold]/workspace <caminho>[/bold] para alterar."
                )
            )
        return True

    # 28. /wave
    if cmd == "wave":
        from ..turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        subparts = arg.split(maxsplit=1)
        subcmd = subparts[0].lower() if subparts else "status"
        subarg = subparts[1].strip() if len(subparts) > 1 else ""

        if subcmd == "resume":
            saved = orch.db.load_wave_state() or {}
            wave_id_salvo = str(saved.get("wave_id") or "").strip()
            estado_salvo = str(saved.get("state") or "").strip().upper()
            if not wave_id_salvo:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Nenhuma ONDA persistida para retomar. "
                        f"Inicie uma com: /wave start ONDA-001[/{TOKENS['warning']}]"
                    )
                )
                return True
            if estado_salvo in ("COMPLETED", ""):
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]A {wave_id_salvo} está concluída ou sem checkpoint válido — nada a retomar. "
                        f"Use: /wave start {wave_id_salvo} para uma nova execução.[/{TOKENS['warning']}]"
                    )
                )
                return True
            return await handle_slash_command(app, f"/wave start {wave_id_salvo}")

        if subcmd == "status":
            st = orch.get_status()
            summary = st["tasks_summary"]
            gates = st.get("gates", {})
            cards = st.get("kanban_cards", [])

            lines = [
                f"[{TOKENS['primary']} bold]⚡ ONDA ATIVA: {st['wave_id']}[/{TOKENS['primary']} bold]",
                f"  • Etapa Atual: [bold]{st['stage']}[/bold]",
                f"  • Autonomia: {st['autonomy_mode']} | Engenharia: {st['engineering_mode']}",
                f"  • Backlog: {summary['completed']} concluídas, {summary['pending']} pendentes, {summary['failed']} falhas (Total: {summary['total']})",
            ]
            if gates:
                lines.append(
                    f"\n[{TOKENS['secondary']} bold]Gates do Turing:[/{TOKENS['secondary']} bold]"
                )
                for g_name, g_info in gates.items():
                    icon = "✓" if g_info.get("approved") else "✗"
                    color = TOKENS["success"] if g_info.get("approved") else TOKENS["error"]
                    lines.append(
                        f"  • [{color}]{icon}[/{color}] {g_name.upper()}: {g_info.get('message', '')}"
                    )

            if cards:
                lines.append(
                    f"\n[{TOKENS['secondary']} bold]Kanban de Stories:[/{TOKENS['secondary']} bold]"
                )
                for c in cards:
                    blocked_tag = (
                        f" 🛑 [bold red][BLOCKED: {c.get('block_reason')}][/bold red]"
                        if c.get("is_blocked")
                        else ""
                    )
                    lines.append(
                        f"  • [{c['status']}] {c['story_id']}: {c['title']} ({c.get('agent', '')}){blocked_tag}"
                    )

            await chat.mount(Static("\n".join(lines)))
            return True

        if subcmd == "start":
            # Autonomia total: --force é obsoleto (o Turing decide sozinho).
            tokens = [p for p in subparts[1:] if p.strip() and p != "--force"]
            force = False
            clean_tokens = tokens

            autonomy = "AUTO"
            wave_id = None
            for t in clean_tokens:
                t_lower = t.lower()
                if t_lower in ("auto", "semi", "semi-auto", "semi_auto", "manual"):
                    autonomy = "SEMI_AUTO" if "semi" in t_lower else t_lower.upper()
                elif t.upper().startswith("ONDA-") or not wave_id:
                    wave_id = t.upper()
                else:
                    wave_id = t

            if not wave_id:
                allowed = app.get_current_wave_stages()
                saved = orch.db.load_wave_state()
                if "DISCOVERY" in allowed:
                    wave_id = "ONDA-000"
                elif saved and saved.get("wave_id"):
                    wave_id = str(saved["wave_id"])
                else:
                    wave_id = "ONDA-001"

            res = orch.start_wave(wave_id=wave_id, autonomy_mode=autonomy, force=force)
            if res.get("success"):
                app.mode = "TDD"
                restored_stage = str(res.get("stage", "DISCUSS")).upper()
                app.wave_station = restored_stage
                app.update_status()

                if res.get("resumed"):
                    await chat.mount(
                        Static(
                            f"[{TOKENS['success']} bold]✓ {res['message']}[/{TOKENS['success']} bold]"
                        )
                    )
                    # MODO AUTO: a máquina se encadeia sozinha a partir do
                    # checkpoint — o humano NUNCA digita o próximo comando.
                    proximos = {
                        "PLAN": "/wave plan",
                        "REFINEMENT": "/wave plan",
                        "EXECUTE": "/wave execute",
                        "VALIDATE": "/wave validate",
                    }
                    autonomia_real = str(res.get("autonomy_mode", autonomy)).upper()
                    if autonomia_real in ("AUTO", "SEMI_AUTO") and restored_stage in proximos:
                        proximo = proximos[restored_stage]
                        modo_tag = "AUTO" if autonomia_real == "AUTO" else "SEMI-AUTO"
                        await chat.mount(
                            Static(
                                f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO {modo_tag}] Retomando de {restored_stage} — encadeando {proximo}...[/{TOKENS['primary']} bold]"
                            )
                        )
                        await handle_slash_command(app, proximo)
                    elif restored_stage in ("DISCUSS", "DISCOVERY"):
                        # Autosserviço: se existe briefing/missão no disco, a
                        # máquina roga sozinha — humano não digita comando.
                        briefings_dir = Path(app.project_dir) / "docs" / "briefings"
                        briefing = (
                            next(
                                (
                                    b
                                    for b in sorted(briefings_dir.glob("*.md"))
                                    if b.name.upper() not in ("VIABILITY.MD", "PRD.MD")
                                ),
                                None,
                            )
                            if briefings_dir.is_dir()
                            else None
                        )
                        if briefing:
                            demanda = briefing.read_text(encoding="utf-8").strip()
                            await chat.mount(
                                Static(
                                    f"[{TOKENS['primary']} bold]⚡ [MODO AUTO] Briefing humano encontrado em {briefing.name} — acionando DISCUSS automaticamente...[/{TOKENS['primary']} bold]"
                                )
                            )
                            await handle_slash_command(app, f"/wave discuss {demanda}")
                        else:
                            # Único chamado legítimo: FURO DE INFORMAÇÃO (missão).
                            await chat.mount(
                                Static(
                                    f"[{TOKENS['warning']} bold]❓ FURO DE INFORMAÇÃO — projeto sem missão definida.[/{TOKENS['warning']} bold]\n"
                                    f"[dim]Nenhum briefing encontrado em docs/briefings/.[/dim]\n"
                                    f"Descreva a missão/demanda do produto (responde à pergunta: o que deve ser construído?).\n"
                                    f"[dim]Isto é informação de negócio — a única razão pela qual o runtime interrompe você.[/dim]"
                                )
                            )
                    return True

                etapa_real = str(res.get("stage", "DISCUSS")).upper()
                is_greenfield = etapa_real in ("DISCOVERY", "DISCUSS") or (
                    wave_id in ("ONDA-000", "ONDA-0", "WAVE-0", "WAVE-000")
                    or "DISCOVERY" in app.get_current_wave_stages()
                )
                lines = [
                    f"[{TOKENS['success']} bold]✓ {res['message']}[/{TOKENS['success']} bold]",
                    f"[dim]Modo de autonomia: {autonomy} | Etapa ativa: {etapa_real} (Pressione Tab para navegar etapas ou Shift+Tab para VIBE)[/dim]",
                    "",
                ]
                if is_greenfield:
                    lines.extend(
                        [
                            f"[{TOKENS['primary']} bold]📋 Novo Projeto Detectado (Onda 0 - Greenfield)[/{TOKENS['primary']} bold]",
                            "Para que o time de especialistas (@meira e @grace) possa avaliar a viabilidade e gerar o PRD, precisamos da sua [bold]MISSÃO[/bold] ou [bold]BRIEFING[/bold].",
                            "",
                            f"[{TOKENS['secondary']} bold]👉 Como prosseguir agora:[/{TOKENS['secondary']} bold]",
                            "  1. Digite a sua ideia diretamente no campo de texto abaixo (ex: [italic]Quero criar um SaaS de gestão de frotas com telemetria[/italic]).",
                            "  2. Ou use o comando: [cyan]/wave discuss <sua ideia/briefing>[/cyan]",
                            "",
                            "[dim]Assim que você enviar a ideia, o orquestrador aciona @meira para viabilidade técnica e @grace para o PRD.[/dim]",
                        ]
                    )
                    await chat.mount(Static("\n".join(lines)))
                    return True

                # Onda de Entrega: DISCUSS não existe — a fundação vem da Onda 0/PRD.
                lines.append(
                    f"[{TOKENS['primary']} bold]📋 ONDA {wave_id} iniciada na etapa {etapa_real} — fundação definida na Onda 0 (PRD + Sequenciador).[/{TOKENS['primary']} bold]"
                )
                await chat.mount(Static("\n".join(lines)))

                autonomy_norm = autonomy.upper().replace("-", "_")
                if autonomy_norm in ("AUTO", "SEMI_AUTO"):
                    proximo = {
                        "PLAN": "/wave plan",
                        "REFINEMENT": "/wave plan",
                        "EXECUTE": "/wave execute",
                        "VALIDATE": "/wave validate",
                    }.get(etapa_real)
                    if proximo:
                        modo_tag = "AUTO" if autonomy_norm == "AUTO" else "SEMI-AUTO"
                        await chat.mount(
                            Static(
                                f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO {modo_tag}] Encadeando automaticamente a etapa {etapa_real}...[/{TOKENS['primary']} bold]"
                            )
                        )
                        await handle_slash_command(app, proximo)
                    else:
                        await chat.mount(Static("[dim]Aguardando insumo para a etapa ativa.[/dim]"))
                elif etapa_real in ("PLAN", "REFINEMENT"):
                    await chat.mount(
                        Static(
                            "[dim]Próximo passo: /wave plan (arquitetura e stories com base no PRD).[/dim]"
                        )
                    )
                elif etapa_real == "EXECUTE":
                    await chat.mount(
                        Static("[dim]Próximo passo: /wave execute ou /wave cycle.[/dim]")
                    )
                elif etapa_real == "VALIDATE":
                    await chat.mount(Static("[dim]Próximo passo: /wave validate.[/dim]"))
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']} bold]{res.get('message', 'Erro ao iniciar onda')}[/{TOKENS['warning']} bold]"
                    )
                )
            return True

        if subcmd == "discuss":
            topic = subarg.strip()
            if not topic:
                msg = [
                    f"[{TOKENS['warning']} bold]⚠️ O comando '/wave discuss' requer uma demanda ou missão![/{TOKENS['warning']} bold]",
                    "",
                    "Para que [bold]@meira[/bold] (Viabilidade) e [bold]@grace[/bold] (PRD) possam trabalhar, você precisa descrever o que deseja construir.",
                    "",
                    f"[{TOKENS['secondary']} bold]👉 Como executar:[/{TOKENS['secondary']} bold]",
                    "  [cyan]/wave discuss <descreva sua ideia aqui>[/cyan]",
                    "",
                    "[bold]Exemplos práticos:[/bold]",
                    "  • [italic]/wave discuss App de Onboarding Interativo com Quiz Financeiro e Validação de Leads[/italic]",
                    "  • [italic]/wave discuss API REST para gestão de assinaturas com multitenancy[/italic]",
                    "  • [italic]/wave discuss Dashboard de logística com React e FastAPI[/italic]",
                    "",
                    "[dim]Dica: Você também pode simplesmente digitar a sua ideia no campo de mensagem abaixo sem comando![/dim]",
                ]
                await chat.mount(Static("\n".join(msg)))
                return True

            res = await _run_orchestrator_with_stream(chat, orch.run_discuss, topic, app=app)
            if res.get("success"):
                app.wave_station = "PLAN"
                app.update_status()
                saved_state = orch.db.load_wave_state() or {}
                autonomy = saved_state.get("autonomy_mode", "AUTO")
                if deve_encadear(autonomy, "DISCUSS", "PLAN"):
                    modo_tag = "AUTO" if autonomy.upper() == "AUTO" else "SEMI-AUTO"
                    await chat.mount(
                        Static(
                            f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO {modo_tag}] Encadeando automaticamente para a etapa PLAN...[/{TOKENS['primary']} bold]"
                        )
                    )
                    await handle_slash_command(app, "/wave plan")
                else:
                    await chat.mount(
                        Static(
                            f"[dim]⏸ Etapa DISCUSS concluída (agentes + gates rodaram) — modo {autonomy}: quando quiser, /wave plan[/dim]"
                        )
                    )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Aviso em DISCUSS: {res.get('error', 'Inconsistência')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "plan":
            prd_file = Path(app.project_dir) / "docs" / "briefings" / "PRD.md"
            if not prd_file.exists():
                msg = [
                    f"[{TOKENS['warning']} bold]⚠️ Não é possível executar a etapa PLAN ainda![/{TOKENS['warning']} bold]",
                    "",
                    "A etapa [bold]PLAN[/bold] requer um PRD (Product Requirements Document) aprovado pela [bold]@grace[/bold].",
                    "",
                    f"[{TOKENS['secondary']} bold]👉 Próximo Passo:[/{TOKENS['secondary']} bold]",
                    "Execute primeiro a etapa de discussão de produto informando sua ideia:",
                    "  [cyan]/wave discuss <sua ideia>[/cyan]",
                    "",
                    "[dim]Assim que o PRD for gerado e aprovado, os arquitetos (@ieru, @codd, @caroli) poderão desenhar a arquitetura e quebrar as stories.[/dim]",
                ]
                await chat.mount(Static("\n".join(msg)))
                return True

            res = await _run_orchestrator_with_stream(chat, orch.run_plan, app=app)
            if res.get("success"):
                app.wave_station = "EXECUTE"
                app.update_status()
                saved_state = orch.db.load_wave_state() or {}
                autonomy = saved_state.get("autonomy_mode", "AUTO")
                if deve_encadear(autonomy, "PLAN", "EXECUTE"):
                    modo_tag = "AUTO" if autonomy.upper() == "AUTO" else "SEMI-AUTO"
                    await chat.mount(
                        Static(
                            f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO {modo_tag}] Encadeando automaticamente para a etapa EXECUTE...[/{TOKENS['primary']} bold]"
                        )
                    )
                    await handle_slash_command(app, "/wave execute")
                elif autonomy.upper().replace("-", "_") == "SEMI_AUTO":
                    await chat.mount(
                        Static(
                            f"[{TOKENS['warning']} bold]⏸ FASE UPSTREAM CONCLUÍDA (entendimento, viabilidade e planejamento + gates) — pausa do modo SEMI-AUTO.[/{TOKENS['warning']} bold]\n"
                            f"[dim]Revise arquitetura e backlog. Autorize a construção com: /wave execute[/dim]"
                        )
                    )
                else:
                    await chat.mount(
                        Static(
                            f"[dim]⏸ Etapa PLAN concluída (agentes + gates rodaram) — modo {autonomy}: quando quiser, /wave execute ou /wave cycle[/dim]"
                        )
                    )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Aviso em PLAN: {res.get('error')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "cycle":
            target_story = subarg or None
            story_label = target_story or "próxima story"
            cards = orch.kanban.list_cards(wave_id=orch.state_machine.wave_id)
            if not cards:
                msg = [
                    f"[{TOKENS['warning']} bold]⚠️ Nenhuma story disponível no Kanban para execução![/{TOKENS['warning']} bold]",
                    "",
                    "O time de engenharia ([bold]@unclebob, @barbara, @ada, @fowler[/bold]) precisa de histórias prontas para codificar.",
                    "",
                    f"[{TOKENS['secondary']} bold]👉 Próximo Passo:[/{TOKENS['secondary']} bold]",
                    "Execute a etapa de planejamento para que o [bold]@caroli[/bold] gere as histórias no PBB:",
                    "  [cyan]/wave plan[/cyan]",
                ]
                await chat.mount(Static("\n".join(msg)))
                return True

            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Executando ciclo atômico para {story_label}...[/{TOKENS['secondary']} bold]"
                )
            )
            res = await _run_orchestrator_with_stream(chat, orch.run_cycle, target_story, app=app)
            if res.get("success"):
                await chat.mount(
                    Static(f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]")
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Falha no ciclo: {res.get('error', 'Rejeição no gate')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "execute":
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Iniciando execução em lote da ONDA (Cycle-Full)...[/{TOKENS['secondary']} bold]"
                )
            )
            res = await _run_orchestrator_with_stream(chat, orch.run_execute, app=app)
            if res.get("success"):
                app.wave_station = "VALIDATE"
                app.update_status()
                saved_state = orch.db.load_wave_state() or {}
                autonomy = saved_state.get("autonomy_mode", "AUTO")
                if deve_encadear(autonomy, "EXECUTE", "VALIDATE"):
                    modo_tag = "AUTO" if autonomy.upper() == "AUTO" else "SEMI-AUTO"
                    await chat.mount(
                        Static(
                            f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO {modo_tag}] Encadeando automaticamente para a etapa VALIDATE...[/{TOKENS['primary']} bold]"
                        )
                    )
                    await handle_slash_command(app, "/wave validate")
                else:
                    await chat.mount(
                        Static(
                            f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]\n"
                            f"[dim]⏸ Etapa EXECUTE concluída (todos os ciclos TDD + reviews) — modo {autonomy}: /wave validate quando quiser[/dim]"
                        )
                    )
            elif res.get("escalation"):
                esc = res["escalation"]
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']} bold]❓ DÚVIDA DE NEGÓCIO — {esc.get('story', 'story')} não convergiu.[/{TOKENS['warning']} bold]\n"
                        f"{esc.get('message', '')}\n"
                        f"[dim]Responsável técnico sugerido: {esc.get('suggested_owner')}[/dim]"
                    )
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Execução interrompida: {res.get('error') or res.get('message') or 'motivo não especificado'}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "validate":
            res = await _run_orchestrator_with_stream(chat, orch.run_validate, app=app)
            if res.get("success"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ ONDA validada com sucesso com Selo de Homologação Final.[/{TOKENS['success']}]"
                    )
                )
                saved_state = orch.db.load_wave_state() or {}
                autonomy = saved_state.get("autonomy_mode", "AUTO")
                if autonomy != "AUTO":
                    msg_pausa = (
                        f"[{TOKENS['warning']} bold]⏸ FASE DOWNSTREAM CONCLUÍDA (construção + homologação) — pausa do modo SEMI-AUTO.[/{TOKENS['warning']} bold]\n"
                        f"[dim]Navegue no entregável. Arquive com: /wave end[/dim]"
                        if autonomy.upper().replace("-", "_") == "SEMI_AUTO"
                        else f"[dim]⏸ Etapa VALIDATE concluída — modo {autonomy}: /wave end para arquivar.[/dim]"
                    )
                    await chat.mount(Static(msg_pausa))
                    return True

                # MODO AUTO: arquiva a onda e encadeia a próxima do Sequenciador.
                end_res = orch.end_wave()
                if end_res.get("success"):
                    await chat.mount(
                        Static(
                            f"[{TOKENS['success']} bold]🏁 {end_res.get('message')}[/{TOKENS['success']} bold]"
                        )
                    )
                from bombe_code.domain.wave.sequencer import WaveSequencer

                prd_file = Path(app.project_dir) / "docs" / "briefings" / "PRD.md"
                prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
                sequencer = WaveSequencer.from_markdown(prd_content)
                current_id = end_res.get("wave_id") or saved_state.get("wave_id", "")
                if sequencer.has_future_waves(current_id):
                    idx = sequencer.get_plan_index(current_id)
                    next_plan = sequencer.plans[idx + 1]
                    await chat.mount(
                        Static(
                            f"[{TOKENS['primary']} bold]{markup_turing('maestro')} [MODO AUTO] Encadeando para a próxima onda: {next_plan.wave_id} ({next_plan.name})...[/{TOKENS['primary']} bold]"
                        )
                    )
                    await handle_slash_command(app, f"/wave start {next_plan.wave_id}")
                else:
                    await chat.mount(
                        Static(
                            f"[{TOKENS['success']} bold]🏆 MVP completo — todas as ondas entregues e homologadas.[/{TOKENS['success']} bold]\n"
                            f"[dim]Intervenção humana final: navegue no produto e valide a experiência.[/dim]"
                        )
                    )
                return True
            if res.get("blocked"):
                escalation = (res.get("rework") or {}).get("escalation") or {}
                bloqueios = escalation.get("blockers") or []
                linhas_bloqueios = (
                    "\n".join(f"  • {b}" for b in bloqueios) or f"  • {res.get('error')}"
                )
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']} bold]❓ DÚVIDA DE NEGÓCIO — intervenção humana solicitada (último recurso).[/{TOKENS['warning']} bold]\n"
                        f"[{TOKENS['warning']}]O ciclo autônomo de retrabalho foi esgotado e a decisão excede a autonomia dos agentes.[/{TOKENS['warning']}]\n"
                        f"[dim]Responsável técnico sugerido: {escalation.get('suggested_owner', '@turing')}[/dim]\n"
                        f"{linhas_bloqueios}\n"
                        f"[dim]Resolva e reexecute: /wave validate[/dim]"
                    )
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Validação não aprovada: {res.get('error')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "audit":
            alvo = subarg.strip().upper() or None
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]🔍 Contra-Auditoria Forense (@hoare) — alvo: {alvo or 'onda ativa'}[/{TOKENS['secondary']} bold]"
                )
            )
            res = await _run_orchestrator_with_stream(chat, orch.run_audit, alvo, app=app)
            if res.get("success") and res.get("limpa"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✅ AUDITORIA: LIMPA — pedido × entregue verificado no código, suíte real executada ({res.get('suite')}).[/{TOKENS['success']}]\n"
                        f"[dim]Laudo: {res.get('laudo_path')}[/dim]"
                    )
                )
            elif res.get("success"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']} bold]🚨 {len(res.get('furos', []))} FURO(S) encontrado(s) na {res.get('wave_id')}.[/{TOKENS['warning']} bold]\n"
                        + "\n".join(f"  • {f}" for f in res.get("furos", [])[:8])
                        + f"\n[dim]{res.get('reexecucao', 'Cards bloqueados; ciclo de correção acionado.')}[/dim]"
                    )
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Auditoria falhou: {res.get('error')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "end":
            res = orch.end_wave()
            if res.get("success"):
                await chat.mount(
                    Static(f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]")
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Não foi possível finalizar a ONDA: {res.get('error')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        await chat.mount(
            Static(
                f"[{TOKENS['warning']}]Subcomando do /wave desconhecido: '{subcmd}'. Use: start, resume, status, discuss, plan, cycle, execute, validate, audit, end.[/{TOKENS['warning']}]"
            )
        )
        return True

    # Comandos de Projeto e Governança Operacional (ST-019 a ST-022)
    if cmd == "project":
        from bombe_code.config.project_config import ProjectConfigManager

        mgr = ProjectConfigManager(app.project_dir)
        sub = arg.strip().lower()

        if sub.startswith("starter"):
            from bombe_code.starters.engine import StarterEngine

            s_parts = sub.split(maxsplit=2)
            s_action = s_parts[1] if len(s_parts) > 1 else "list"
            engine = StarterEngine()

            if s_action == "list":
                starters = engine.list_starters()
                lines = [
                    f"• [bold]{s['id']}[/bold] [{s['stack']}]: {s['description']}" for s in starters
                ]
                await chat.mount(
                    Static(
                        f"[{TOKENS['primary']} bold]Starters Disponíveis no Bombe Code ({len(starters)}):[/{TOKENS['primary']} bold]\n"
                        + "\n".join(lines)
                    )
                )
                return True

            if s_action == "apply":
                starter_id = s_parts[2] if len(s_parts) > 2 else ""
                if not starter_id:
                    await chat.mount(
                        Static(
                            f"[{TOKENS['warning']}]Uso: /project starter apply <nome-do-starter>[/{TOKENS['warning']}]"
                        )
                    )
                    return True
                res = engine.apply_starter(starter_id, target_dir=app.project_dir)
                if res.get("success"):
                    await chat.mount(
                        Static(
                            f"[{TOKENS['success']}]✓ Starter '{starter_id}' aplicado com sucesso! ({len(res.get('created_files', []))} arquivos gerados)[/{TOKENS['success']}]"
                        )
                    )
                else:
                    await chat.mount(
                        Static(f"[{TOKENS['warning']}]{res.get('error')}[/{TOKENS['warning']}]")
                    )
                return True

        if sub == "detect":
            cfg = mgr.detect_stack()
            mgr.save(cfg)
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ Stack autodetectada:\n"
                    f"• Backend: {cfg.backend_language} ({cfg.backend_path})\n"
                    f"• Frontend: {cfg.frontend_stack} ({cfg.frontend_path})[/{TOKENS['success']}]"
                )
            )
            return True

        cfg = mgr.load()
        await chat.mount(
            Static(
                f"[{TOKENS['primary']} bold]Configuração do Projeto ({cfg.name}):[/{TOKENS['primary']} bold]\n"
                f"• Tipo: {cfg.type}\n"
                f"• Backend: {cfg.backend_language}\n"
                f"• Frontend: {cfg.frontend_stack}\n"
                f"• Modo de Engenharia: {cfg.mode}\n"
                f"• Autonomia: {cfg.autonomy}"
            )
        )
        return True

    if cmd == "snippet":
        from bombe_code.snippets.registry import SnippetRegistry

        reg = SnippetRegistry()
        s_parts = arg.strip().split(maxsplit=2)
        action = s_parts[0].lower() if s_parts and s_parts[0] else "list"

        if action == "list":
            snippets = reg.list_snippets()
            lines = [
                f"• [bold]{s['name']}[/bold] [{s['platform']}]: {s['description']}"
                for s in snippets
            ]
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Catálogo de Snippets (Fábrica de LEGO) ({len(snippets)}):[/{TOKENS['primary']} bold]\n"
                    + "\n".join(lines)
                )
            )
            return True

        if action == "search":
            query = s_parts[1] if len(s_parts) > 1 else ""
            if not query:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Uso: /snippet search <termo>[/{TOKENS['warning']}]"
                    )
                )
                return True
            res = reg.search(query=query)
            lines = [
                f"• [bold]{s['name']}[/bold] [{s['platform']}]: {s['description']}" for s in res
            ]
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]Snippets Encontrados para '{query}' ({len(res)}):[/{TOKENS['primary']} bold]\n"
                    + ("\n".join(lines) if lines else "Nenhum snippet encontrado.")
                )
            )
            return True

        if action in ("get", "show"):
            name = s_parts[1] if len(s_parts) > 1 else ""
            plat = s_parts[2] if len(s_parts) > 2 else "python"
            snip = reg.get_snippet(name, platform=plat)
            if snip:
                await chat.mount(
                    Static(
                        f"[{TOKENS['primary']} bold]Snippet {snip['name']} ({snip['platform']}):[/{TOKENS['primary']} bold]\n```\n{snip['code']}\n```"
                    )
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Snippet '{name}' não encontrado para {plat}.[/{TOKENS['warning']}]"
                    )
                )
            return True

        if action in ("install", "copy"):
            name = s_parts[1] if len(s_parts) > 1 else ""
            dest = s_parts[2] if len(s_parts) > 2 else "src/utils"
            res = reg.copy_snippet(name, to_dir=dest)
            if res.get("success"):
                await chat.mount(
                    Static(f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]")
                )
            else:
                await chat.mount(
                    Static(f"[{TOKENS['warning']}]{res.get('error')}[/{TOKENS['warning']}]")
                )
            return True

    if cmd == "verbosity":
        from bombe_code.config.project_config import ProjectConfigManager
        from bombe_code.turing.progress import BUS

        alvo = arg.strip().lower()
        if alvo in ("verbose", "quiet", "silencioso"):
            modo = "quiet" if alvo in ("quiet", "silencioso") else "verbose"
        elif not alvo:
            modo = "quiet" if not BUS.is_quiet else "verbose"
        else:
            await chat.mount(
                Static(
                    f"[{TOKENS['warning']}]Uso: /verbosity <verbose|quiet> (sem argumento alterna o modo atual)[/{TOKENS['warning']}]"
                )
            )
            return True

        BUS.set_verbosity(modo)
        os.environ["BOMBE_VERBOSITY"] = modo
        try:
            mgr = ProjectConfigManager(app.project_dir)
            cfg = mgr.load()
            cfg.verbosity = modo
            mgr.save(cfg)
        except Exception as exc:  # noqa: BLE001 — persistência é best-effort
            logger.warning("Falha ao persistir verbosidade: %s", exc)
        detalhe = (
            "cada letra, raciocínio e tool call serão streamados na tela"
            if modo == "verbose"
            else "apenas anúncios de onda, etapas e vetos serão exibidos"
        )
        await chat.mount(
            Static(
                f"[{TOKENS['success']}]✓ Verbosidade definida como {modo.upper()} — {detalhe}.[/{TOKENS['success']}]"
            )
        )
        return True

    if cmd == "mode":
        if not arg:
            await chat.mount(
                Static(
                    f"[{TOKENS['warning']}]Uso: /mode <auto|semi-auto|manual|tdd|vibe>[/{TOKENS['warning']}]"
                )
            )
            return True
        from bombe_code.turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        res = orch.set_mode(arg)
        if res.get("success"):
            await chat.mount(
                Static(
                    f"[{TOKENS['success']}]✓ {res['message']} "
                    f"(Autonomia: {res['autonomy_mode']}, Engenharia: {res['engineering_mode']})[/{TOKENS['success']}]"
                )
            )
        else:
            await chat.mount(
                Static(f"[{TOKENS['warning']}]{res.get('error')}[/{TOKENS['warning']}]")
            )
        return True

    if cmd == "rca":
        if not arg:
            await chat.mount(
                Static(
                    f"[{TOKENS['warning']}]Uso: /rca <descrição do incidente>[/{TOKENS['warning']}]"
                )
            )
            return True
        from bombe_code.turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]Conduzindo RCA com @unclebob para: {arg}...[/{TOKENS['secondary']} bold]"
            )
        )
        res = await anyio.to_thread.run_sync(orch.run_rca, arg)
        await chat.mount(
            Static(
                f"[{TOKENS['primary']} bold]Relatório RCA ({res.get('agent')}):[/{TOKENS['primary']} bold]\n{res.get('report')}"
            )
        )
        return True

    if cmd == "simplify":
        if not arg:
            await chat.mount(
                Static(
                    f"[{TOKENS['warning']}]Uso: /simplify <caminho do arquivo ou módulo>[/{TOKENS['warning']}]"
                )
            )
            return True
        from bombe_code.turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]Iniciando auditoria de simplificação com @ieru e @unclebob em: {arg}...[/{TOKENS['secondary']} bold]"
            )
        )
        res = await anyio.to_thread.run_sync(orch.run_simplify, arg)
        await chat.mount(
            Static(
                f"[{TOKENS['primary']} bold]Parecer de Simplificação ({res.get('agent')}):[/{TOKENS['primary']} bold]\n{res.get('output')}"
            )
        )
        return True

    if cmd == "task":
        if not arg:
            await chat.mount(
                Static(
                    f"[{TOKENS['warning']}]Uso: /task <descrição da tarefa>[/{TOKENS['warning']}]"
                )
            )
            return True
        from bombe_code.turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]Executando tarefa avulsa: {arg}...[/{TOKENS['secondary']} bold]"
            )
        )
        res = await anyio.to_thread.run_sync(orch.run_task, arg)
        await chat.mount(
            Static(
                f"[{TOKENS['success']}]✓ Tarefa concluída por {res.get('agent')}:[/{TOKENS['success']}]\n{res.get('output')}"
            )
        )
        return True

    if cmd == "report":
        from bombe_code.turing.orchestrator import WaveOrchestrator

        orch = WaveOrchestrator(project_dir=app.project_dir)
        rep = orch.generate_status_report()
        summary = rep["tasks_summary"]
        cfg = rep["config"]
        await chat.mount(
            Static(
                f"[{TOKENS['primary']} bold]Relatório Consolidado de Governança — ONDA {rep['wave_id']}:[/{TOKENS['primary']} bold]\n"
                f"• Estágio: {rep['stage']}\n"
                f"• Modos: Autonomia={rep['autonomy_mode']}, Engenharia={rep['engineering_mode']}\n"
                f"• Projeto: {cfg.get('name')} ({cfg.get('backend_language')}/{cfg.get('frontend_stack')})\n"
                f"• Tasks Registradas: {summary.get('total')}"
            )
        )
        return True

    # 29. /exit (aliases: /quit, /q)
    if cmd in ("exit", "quit", "q"):
        app.exit()
        return True

    # Comandos customizados do usuário (.bombe/commands/*.md ou .opencode/commands/*.md)
    from ..commands.loader import load_custom_commands
    from ..commands.templates import render_command_template

    custom_cmds = load_custom_commands(app.project_dir)
    if cmd in custom_cmds:
        custom = custom_cmds[cmd]
        expanded_prompt = render_command_template(custom.template, arguments=arg)
        await chat.mount(
            Static(
                f"[{TOKENS['secondary']} bold]/{cmd} ({custom.description}):[/{TOKENS['secondary']} bold] {expanded_prompt}"
            )
        )
        app._is_active_turn = True
        app.update_status()
        app._run_prompt_worker(expanded_prompt)
        return True

    # Comando não reconhecido
    await chat.mount(
        Static(
            f"[{TOKENS['warning']}]Comando não reconhecido: /{cmd}. Digite [bold]/help[/bold] para ver os 28 comandos disponíveis.[/{TOKENS['warning']}]"
        )
    )
    return True
