"""Entrypoint da CLI Bombe Code construída com Typer."""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Annotated, Any

import httpx
import typer
import uvicorn

from .. import __version__
from ..config.paths import get_paths
from ..permissions.rules import PermissionService, Rule
from ..providers.models_dev import get_models
from ..server.app import create_app
from ..session import crud
from ..session.loop import run_prompt
from ..tools.registry import ToolRegistry, builtin_registry, load_custom_tools


def create_default_registry(project_dir: str = ".") -> ToolRegistry:
    reg = builtin_registry()
    load_custom_tools(reg, project_dir)
    return reg


class ServerThread:
    """Invólucro para o servidor uvicorn in-process."""

    def __init__(self, server: uvicorn.Server, thread: threading.Thread):
        self.server = server
        self.thread = thread

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5.0)


from ..providers.resolver import resolve_provider_adapter

resolve_default_adapter = resolve_provider_adapter


def start_server_in_process(
    host: str = "127.0.0.1",
    port: int = 0,
    project_dir: str = ".",
    adapter: Any = None,
) -> tuple[ServerThread, int, str]:
    """Inicia servidor uvicorn em thread secundária para uso in-process."""
    if adapter is None:
        adapter = resolve_default_adapter()

    permissions = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")],
        approved=[],
    )
    app_instance = create_app(
        adapter=adapter,
        permissions=permissions,
        project_dir=project_dir,
    )

    config = uvicorn.Config(app_instance, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15.0
    bound_port = None
    while time.time() < deadline:
        if getattr(server, "servers", None):
            bound_port = server.servers[0].sockets[0].getsockname()[1]
            break
        time.sleep(0.05)

    if bound_port is None:
        raise RuntimeError("Servidor uvicorn in-process não iniciou a tempo.")

    auth_path = get_paths().state / "server-auth"
    password = auth_path.read_text(encoding="utf-8").strip() if auth_path.is_file() else ""
    return ServerThread(server, thread), bound_port, password


app = typer.Typer(
    name="bombe-code",
    help="Bombe Code — Agente de código autônomo com ciclo vibe.",
    no_args_is_help=False,
)

from .commands.mission import mission_app
from .commands.project import project_app
from .commands.round import (
    round_all_cmd,
    round_app,
    round_full_cmd,
    round_start_cmd,
)
from .commands.standalone import (
    mode_cmd,
    rca_cmd,
    review_cmd,
    simplify_cmd,
    standalone_app,
    status_report_cmd,
    task_cmd,
)
from .commands.wave_bridge import wave_app

app.add_typer(mission_app, name="mission")
app.add_typer(project_app, name="project")
app.add_typer(round_app, name="round")
app.add_typer(wave_app, name="wave")
app.add_typer(standalone_app, name="standalone")

app.command("round-start")(round_start_cmd)
app.command("round-full")(round_full_cmd)
app.command("round-all")(round_all_cmd)

# Standalone root commands
app.command("mode")(mode_cmd)
app.command("task")(task_cmd)
app.command("rca")(rca_cmd)
app.command("review")(review_cmd)
app.command("simplify")(simplify_cmd)
app.command("status-report")(status_report_cmd)
app.command("report")(status_report_cmd)


snippet_cli = typer.Typer(name="snippet", help="Gerencia snippets de código (Fábrica de LEGO).")
app.add_typer(snippet_cli, name="snippet")


@snippet_cli.command("list")
def snippet_list(
    platform: Annotated[
        str | None,
        typer.Option("--platform", "-p", help="Filtrar por linguagem (python, go, nodejs)"),
    ] = None,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Filtrar por categoria")
    ] = None,
) -> None:
    """Lista snippets disponíveis no catálogo."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    snippets = reg.list_snippets(platform=platform, category=category)
    typer.echo(f"Snippets Disponíveis ({len(snippets)}):")
    for s in snippets:
        typer.echo(f"• {s['name']} [{s['platform']}] ({s['category']}): {s['description']}")


@snippet_cli.command("search")
def snippet_search(
    query: Annotated[str, typer.Argument(help="Termo de pesquisa")],
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Filtrar por linguagem")
    ] = None,
) -> None:
    """Pesquisa snippets por termo no nome, descrição ou tags."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    results = reg.search(query=query, platform=platform)
    typer.echo(f"Snippets Encontrados para '{query}' ({len(results)}):")
    for s in results:
        typer.echo(f"• {s['name']} [{s['platform']}]: {s['description']}")


@snippet_cli.command("install")
def snippet_install(
    name: Annotated[str, typer.Argument(help="Nome do snippet")],
    to: Annotated[
        str, typer.Option("--to", "-t", help="Diretório de destino no projeto")
    ] = "src/utils",
    platform: Annotated[str, typer.Option("--platform", "-p", help="Linguagem")] = "python",
) -> None:
    """Instala o código e testes do snippet no diretório especificado."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    res = reg.copy_snippet(name=name, to_dir=to, platform=platform)
    if res.get("success"):
        typer.echo(res.get("message", "Snippet instalado com sucesso."))
    else:
        typer.echo(f"Erro ao instalar snippet: {res.get('error')}", err=True)
        raise typer.Exit(code=1)


@app.command("version")
def version() -> None:
    """Exibe a versão instalada do Bombe Code."""
    typer.echo(f"bombe-code {__version__}")


@app.command("upgrade")
def upgrade_cmd(
    branch: Annotated[
        str | None,
        typer.Option(
            "--branch",
            "-b",
            help="Branch do repositório Git para upgrade (ex: main, dev-working-ia)",
        ),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", "-t", help="Tag/Release específica do Git (ex: v0.1.2)"),
    ] = None,
    git_url: Annotated[
        str | None,
        typer.Option("--git-url", "-g", help="URL do repositório Git (padrão: oficial no GitHub)"),
    ] = None,
    local: Annotated[
        bool,
        typer.Option("--local", "-l", help="Atualiza a partir do diretório local atual"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Força a reinstalação mesmo se a versão for a mesma"),
    ] = True,
    check_only: Annotated[
        bool,
        typer.Option(
            "--check",
            "-c",
            help="Apenas verifica se há novas versões disponíveis no Git sem instalar",
        ),
    ] = False,
) -> None:
    """Atualiza a instalação do Bombe Code via Git usando uv tool install."""
    from .updater import ha_sessao_ativa

    sessoes = ha_sessao_ativa()
    if sessoes:
        detalhes = ", ".join(f"PID {s['pid']}" for s in sessoes)
        typer.echo(
            f"⏸ Deploy BLOQUEADO: há sessão(ões) do Bombe Code rodando ({detalhes}).\n"
            "Feche-a(s) antes de atualizar — deploy por cima derruba trabalho em voo "
            "e deixa o usuário na versão velha sem saber.",
            err=True,
        )
        raise typer.Exit(code=1)
    from .updater import run_upgrade

    typer.echo("🔄 Verificando atualizações do Bombe Code...")
    res = run_upgrade(
        git_url=git_url,
        branch=branch,
        tag=tag,
        local=local,
        force=force,
        check_only=check_only,
    )

    if not res.get("success"):
        typer.echo(f"❌ Erro durante o upgrade: {res.get('error')}", err=True)
        raise typer.Exit(code=1)

    if res.get("check_only"):
        typer.echo(f"ℹ️ {res.get('message')}")
        return

    typer.echo(f"✅ {res.get('message')}")
    if res.get("remote_sha"):
        typer.echo(f"   Commit SHA: {res.get('remote_sha')[:10]}")


@app.command("models")
def models() -> None:
    """Lista catálogo de modelos suportados."""
    try:
        catalog = get_models()
        typer.echo("Catálogo de Modelos (models.dev):")
        for prov, info in catalog.items():
            if isinstance(info, dict) and "models" in info:
                mod_names = ", ".join(list(info["models"].keys())[:5])
                typer.echo(f"  • {prov}: {mod_names}...")
    except (OSError, RuntimeError, httpx.HTTPError):
        # Fallback offline
        typer.echo("Catálogo de Modelos (offline):")
        typer.echo("  • openai: gpt-4o, gpt-4o-mini, o1")
        typer.echo("  • anthropic: claude-3-5-sonnet, claude-3-5-haiku")
        typer.echo("  • google: gemini-1.5-pro, gemini-2.0-flash")


@app.command("providers")
def providers() -> None:
    """Lista provedores de LLM suportados."""
    provs = [
        "anthropic",
        "openai",
        "google",
        "azure",
        "bedrock",
        "copilot",
        "openrouter",
        "xai",
        "openai-compatible",
    ]
    typer.echo("Provedores suportados:")
    for p in provs:
        typer.echo(f"  • {p}")


@app.command("run")
def run_command(
    prompt: Annotated[str, typer.Argument(help="Instrução para o agente")],
    model: Annotated[str | None, typer.Option("--model", "-m", help="Modelo a utilizar")] = None,
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="Nome do agente")] = None,
    session: Annotated[
        str | None, typer.Option("--session", "-s", help="ID da sessão existente")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório do projeto")] = ".",
) -> None:
    """Executa um prompt diretamente no terminal e imprime a resposta."""
    s_obj = (
        crud.load_session(session)
        if session
        else crud.create_session(title="CLI Run", directory=project_dir)
    )
    adapter = resolve_default_adapter(model)
    registry = create_default_registry(project_dir=project_dir)

    def on_event(ev: dict[str, Any]) -> None:
        if ev.get("type") == "text-delta":
            sys.stdout.write(ev.get("text", ""))
            sys.stdout.flush()

    output = run_prompt(
        session=s_obj,
        user_text=prompt,
        adapter=adapter,
        registry=registry,
        on_event=on_event,
    )
    if not output:
        typer.echo("")
    else:
        typer.echo("")


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Porta HTTP")] = 4096,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório")] = ".",
) -> None:
    """Inicia o servidor HTTP Bombe Code em primeiro plano."""
    adapter = resolve_default_adapter()
    permissions = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")],
        approved=[],
    )
    app_instance = create_app(
        adapter=adapter,
        permissions=permissions,
        project_dir=project_dir,
    )
    typer.echo(f"Iniciando Bombe Code Server em http://{host}:{port}")
    uvicorn.run(app_instance, host=host, port=port)


@app.command("tui")
def tui(
    port: Annotated[int | None, typer.Option("--port", "-p", help="Porta do servidor")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Modelo")] = None,
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="Agente")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="ID da sessão")] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório")] = ".",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Modo menos verboso: apenas anúncios de onda, etapas e vetos (padrão é verboso: streama tudo)",
        ),
    ] = False,
) -> None:
    """Abre a interface interativa de terminal (TUI Textual)."""
    from ..tui.app import BombeTuiApp
    from ..tui.client import BombeClient
    from ..turing.progress import BUS

    def _restaurar_terminal() -> None:
        """Desliga modos de rastreio (mouse/bracketed) deixados por um crash.

        Sem isso, após uma morte abrupta o shell ecoa códigos como
        '35;100;2M' a cada movimento do mouse (opencode original sofre igual).
        """
        try:
            sys.stdout.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?2004l\x1b[?25h")
            sys.stdout.flush()
        except (OSError, ValueError):
            pass

    if quiet:
        BUS.set_verbosity("quiet")
        os.environ["BOMBE_VERBOSITY"] = "quiet"

    server_thread: ServerThread | None = None
    if port is None:
        server_thread, bound_port, password = start_server_in_process(
            port=0, project_dir=project_dir
        )
        base_url = f"http://127.0.0.1:{bound_port}"
        auth = ("bombe", password)
    else:
        auth_path = get_paths().state / "server-auth"
        password = auth_path.read_text(encoding="utf-8").strip() if auth_path.is_file() else ""
        base_url = f"http://127.0.0.1:{port}"
        auth = ("bombe", password)

    def _mouse_livre_tui() -> None:
        """Paridade opencode: mouse LIVRE na TUI — o terminal faz a seleção
        nativa e o Ctrl+Shift+C do terminal copia a seleção (Kitty off). Dentro
        de tmux o atalho não intercepta; o app trata o Ctrl+C que chega com
        dica + F2//copy para o transcrição completa."""
        try:
            with open("/dev/tty", "w") as tty:
                tty.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l")
                tty.flush()
        except OSError:
            pass

    import atexit

    atexit.register(_restaurar_terminal)
    _mouse_livre_tui()  # já no boot: seleção nativa disponível desde o início
    try:
        try:
            client = BombeClient(base_url, auth=auth)
            tui_app = BombeTuiApp(
                client=client, session_id=session, model=model, agent=agent, project_dir=project_dir
            )
            tui_app.run()
        finally:
            from ..turing.progress import ABORT_EVENT

            ABORT_EVENT.set()  # fechamento graceful: workers salvam e terminam
            _mouse_livre_tui()
            _restaurar_terminal()
            if server_thread:
                server_thread.stop()
    except Exception as exc:
        from ..errors import format_error_panel, is_debug_mode, record_exception

        if is_debug_mode():
            raise
        log_file = record_exception(exc, context="CLI TUI Runner")
        from rich.console import Console

        console = Console(stderr=True)
        console.print(format_error_panel(exc, log_file))
        sys.exit(1)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Ponto de entrada padrão: se nenhum comando for fornecido, executa 'tui'."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(tui)
