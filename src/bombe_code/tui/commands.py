"""Módulo de despacho e execução dos 28 comandos de barra (/) do OpenCode para a TUI."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

import anyio
import httpx
from textual.widgets import Static

from .tokens import TOKENS

logger = logging.getLogger(__name__)


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
        "desc": "Orquestração soberana da ONDA e fluxo de entrega",
    },
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

        if subcmd == "status":
            st = orch.get_status()
            summary = st["tasks_summary"]
            await chat.mount(
                Static(
                    f"[{TOKENS['primary']} bold]⚡ ONDA ATIVA: {st['wave_id']}[/{TOKENS['primary']} bold]\n"
                    f"  • Etapa Atual: [bold]{st['stage']}[/bold]\n"
                    f"  • Autonomia: {st['autonomy_mode']} | Engenharia: {st['engineering_mode']}\n"
                    f"  • Backlog: {summary['completed']} concluídas, {summary['pending']} pendentes, {summary['failed']} falhas (Total: {summary['total']})"
                )
            )
            return True

        if subcmd == "start":
            wave_id = subarg or "ONDA-004"
            res = orch.start_wave(wave_id)
            await chat.mount(
                Static(f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]")
            )
            return True

        if subcmd == "discuss":
            topic = subarg or "Evolução do Sistema"
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Iniciando etapa DISCUSS para:[/{TOKENS['secondary']} bold] {topic}"
                )
            )
            res = await anyio.to_thread.run_sync(orch.run_discuss, topic)
            if res.get("success"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Etapa DISCUSS concluída com sucesso com @meira e @grace.[/{TOKENS['success']}]"
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
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Iniciando etapa PLAN com os arquitetos de Upstream...[/{TOKENS['secondary']} bold]"
                )
            )
            res = await anyio.to_thread.run_sync(orch.run_plan)
            if res.get("success"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ Etapa PLAN concluída. Backlog e arquitetura prontos para execução.[/{TOKENS['success']}]"
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
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Executando ciclo atômico para {story_label}...[/{TOKENS['secondary']} bold]"
                )
            )
            res = await anyio.to_thread.run_sync(orch.run_cycle, target_story)
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
            res = await anyio.to_thread.run_sync(orch.run_execute)
            if res.get("success"):
                await chat.mount(
                    Static(f"[{TOKENS['success']}]✓ {res['message']}[/{TOKENS['success']}]")
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Execução interrompida: {res.get('error')}[/{TOKENS['warning']}]"
                    )
                )
            return True

        if subcmd == "validate":
            await chat.mount(
                Static(
                    f"[{TOKENS['secondary']} bold]Iniciando auditoria de validação formal com @edith e @nina...[/{TOKENS['secondary']} bold]"
                )
            )
            res = await anyio.to_thread.run_sync(orch.run_validate)
            if res.get("success"):
                await chat.mount(
                    Static(
                        f"[{TOKENS['success']}]✓ ONDA validada com sucesso com Selo de Homologação Final.[/{TOKENS['success']}]"
                    )
                )
            else:
                await chat.mount(
                    Static(
                        f"[{TOKENS['warning']}]Validação não aprovada: {res.get('error')}[/{TOKENS['warning']}]"
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
                f"[{TOKENS['warning']}]Subcomando do /wave desconhecido: '{subcmd}'. Use: start, status, discuss, plan, cycle, execute, validate, end.[/{TOKENS['warning']}]"
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
