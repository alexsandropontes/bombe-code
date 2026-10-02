"""Entrypoint da CLI Bombe Code construída com Typer."""

from __future__ import annotations

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

wave_cli = typer.Typer(name="wave", help="Comandos de orquestração do ciclo da ONDA.")
app.add_typer(wave_cli, name="wave")


@wave_cli.command("start")
def wave_start(
    wave_id: Annotated[
        str, typer.Argument(help="Identificador da ONDA (ex: ONDA-004)")
    ] = "ONDA-004",
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Inicializa uma nova ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.start_wave(wave_id)
    typer.echo(res["message"])


@wave_cli.command("status")
def wave_status(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Exibe o status da ONDA ativa."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    st = orch.get_status()
    summary = st["tasks_summary"]
    typer.echo(f"ONDA: {st['wave_id']} | Etapa: {st['stage']}")
    typer.echo(f"Modo: {st['autonomy_mode']} | Engenharia: {st['engineering_mode']}")
    typer.echo(
        f"Tasks: {summary['completed']} concluídas, {summary['pending']} pendentes, {summary['failed']} falhas"
    )


@wave_cli.command("discuss")
def wave_discuss(
    topic: Annotated[
        str, typer.Argument(help="Tópico para discussão de viabilidade e PRD")
    ] = "Evolução do Sistema",
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a etapa DISCUSS com @meira e @grace."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_discuss(topic)
    if res.get("success"):
        typer.echo("Etapa DISCUSS concluída com sucesso.")
    else:
        typer.echo(f"Erro em DISCUSS: {res.get('error')}", err=True)


@wave_cli.command("plan")
def wave_plan(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a etapa PLAN com os arquitetos de Upstream."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_plan()
    if res.get("success"):
        typer.echo("Etapa PLAN concluída com sucesso.")
    else:
        typer.echo(f"Erro em PLAN: {res.get('error')}", err=True)


@wave_cli.command("cycle")
def wave_cycle(
    story_id: Annotated[
        str | None, typer.Argument(help="ID da story para execução atômica")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa o ciclo atômico de uma story e pausa."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_cycle(story_id)
    typer.echo(res.get("message", "Ciclo executado."))


@wave_cli.command("execute")
def wave_execute(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa o lote total de stories da ONDA (Cycle-Full)."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_execute()
    typer.echo(res.get("message", "Execução de stories finalizada."))


@wave_cli.command("validate")
def wave_validate(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a validação formal da ONDA com @edith e @nina."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_validate()
    if res.get("success"):
        typer.echo("ONDA homologada com sucesso.")
    else:
        typer.echo(f"Validação não aprovada: {res.get('error')}", err=True)


@wave_cli.command("end")
def wave_end(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Finaliza e arquiva a ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.end_wave()
    typer.echo(res.get("message", "ONDA finalizada."))


project_cli = typer.Typer(
    name="project", help="Comandos de configuração do projeto (.bombeconfig)."
)
app.add_typer(project_cli, name="project")


@project_cli.command("detect")
def project_detect(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Autodetecta a stack tecnológica e salva no .bombeconfig."""
    from bombe_code.config.project_config import ProjectConfigManager

    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.detect_stack()
    mgr.save(cfg)
    typer.echo("Stack autodetectada e salva em .bombeconfig:")
    typer.echo(f"- Backend: {cfg.backend_language} ({cfg.backend_path})")
    typer.echo(f"- Frontend: {cfg.frontend_stack} ({cfg.frontend_path})")


@project_cli.command("config")
def project_config(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Exibe a configuração ativa do projeto."""
    from bombe_code.config.project_config import ProjectConfigManager

    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.load()
    typer.echo(f"Configuração do Projeto ({cfg.name}):")
    typer.echo(f"- Tipo: {cfg.type}")
    typer.echo(f"- Backend: {cfg.backend_language}")
    typer.echo(f"- Frontend: {cfg.frontend_stack}")
    typer.echo(f"- Modo de Engenharia: {cfg.mode}")
    typer.echo(f"- Autonomia: {cfg.autonomy}")


@app.command("mode")
def set_mode_cmd(
    mode_str: Annotated[
        str,
        typer.Argument(
            help="Modo de autonomia (auto, semi-auto, manual) ou engenharia (tdd, vibe)"
        ),
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Alterna modo de autonomia ou modo de engenharia."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.set_mode(mode_str)
    if res.get("success"):
        typer.echo(res.get("message", "Modo atualizado com sucesso."))
    else:
        typer.echo(f"Erro: {res.get('error')}", err=True)


@app.command("rca")
def rca_cmd(
    incident: Annotated[
        str, typer.Argument(help="Descrição do incidente para análise de causa raiz")
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa Análise de Causa Raiz determinística com @unclebob."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_rca(incident)
    typer.echo(f"RCA executada por {res.get('agent')}:")
    typer.echo(res.get("report"))


@app.command("simplify")
def simplify_cmd(
    target: Annotated[
        str, typer.Argument(help="Caminho do arquivo ou módulo para auditoria de simplificação")
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa auditoria de simplificação de código com @ieru e @unclebob."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_simplify(target)
    typer.echo(f"Simplificação executada por {res.get('agent')}:")
    typer.echo(res.get("output"))


@app.command("task")
def task_cmd(
    description: Annotated[str, typer.Argument(help="Descrição da tarefa avulsa")],
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Especialista para despachar (ex: @unclebob)"),
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa uma tarefa técnica avulsa sem alterar o estágio da ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_task(description, agent_handle=agent)
    typer.echo(f"Task executada ({res.get('agent')}):")
    typer.echo(res.get("output"))


@app.command("report")
def report_cmd(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Gera um relatório consolidado do projeto e da ONDA ativa."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    rep = orch.generate_status_report()
    typer.echo(f"Relatório Consolidado — ONDA {rep['wave_id']} (Estágio: {rep['stage']}):")
    typer.echo(f"- Modo: Autonomia={rep['autonomy_mode']}, Engenharia={rep['engineering_mode']}")
    typer.echo(
        f"- Projeto: {rep['config']['name']} ({rep['config']['backend_language']}/{rep['config']['frontend_stack']})"
    )
    typer.echo(f"- Total de Tasks Registradas: {rep['tasks_summary']['total']}")


@app.command("version")
def version() -> None:
    """Exibe a versão instalada do Bombe Code."""
    typer.echo(f"bombe-code {__version__}")


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
) -> None:
    """Abre a interface interativa de terminal (TUI Textual)."""
    from ..tui.app import BombeTuiApp
    from ..tui.client import BombeClient

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

    try:
        try:
            client = BombeClient(base_url, auth=auth)
            tui_app = BombeTuiApp(
                client=client, session_id=session, model=model, agent=agent, project_dir=project_dir
            )
            tui_app.run()
        finally:
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
