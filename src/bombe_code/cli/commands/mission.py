"""Typer CLI commands for mission lifecycle (new, status, end)."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bombe_code.domain.contracts.mission import (
    NoActiveMissionError,
    OpenMissionBlockedError,
    PendingDoDError,
)
from bombe_code.orchestration.mission_engine import MissionLifecycleEngine

console = Console()
mission_app = typer.Typer(
    name="mission", help="Comandos de ciclo de vida de missões (new, status, end)."
)


@mission_app.command("new")
def mission_new_cmd(
    demand: Annotated[str, typer.Argument(help="Demanda principal que originou a missão")],
    title: Annotated[
        str | None, typer.Option("--title", "-t", help="Título descritivo da missão")
    ] = None,
    project_dir: Annotated[
        str, typer.Option("--project-dir", "-p", help="Diretório raiz do projeto")
    ] = ".",
) -> None:
    """Inicia uma nova missão com scaffolding físico após validar porteiro atômico."""
    engine = MissionLifecycleEngine(project_dir=project_dir)
    try:
        state = engine.init_mission(demand=demand, title=title)
        panel = Panel.fit(
            f"[bold green]Missão {state.id} inicializada com sucesso![/bold green]\n\n"
            f"[bold]Título:[/bold] {state.title}\n"
            f"[bold]Status:[/bold] {state.status.value}\n"
            f"[bold]Demanda:[/bold] {state.demand}\n"
            f"[bold]Manifesto:[/bold] {state.path}",
            title="🎯 Nova Missão",
            border_style="green",
        )
        console.print(panel)
    except OpenMissionBlockedError as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE (Porteiro Atômico):[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@mission_app.command("status")
def mission_status_cmd(
    project_dir: Annotated[
        str, typer.Option("--project-dir", "-p", help="Diretório raiz do projeto")
    ] = ".",
) -> None:
    """Exibe o status da missão atualmente ativa no projeto."""
    engine = MissionLifecycleEngine(project_dir=project_dir)
    active = engine.get_active_mission()

    if active is None:
        console.print(
            "[bold yellow]Nenhuma missão ativa no momento.[/bold yellow] "
            "Use 'bombe mission new <demanda>' para iniciar."
        )
        return

    table = Table(title=f"🎯 Missão Ativa: {active.title} ({active.id})", border_style="cyan")
    table.add_column("Campo", style="bold cyan")
    table.add_column("Valor", style="white")

    table.add_row("ID", active.id)
    table.add_row("Título", active.title)
    table.add_row("Status", active.status.value)
    table.add_row("Round Atual", str(active.current_round or "N/A"))
    table.add_row("Total de Rounds", str(active.total_rounds))
    table.add_row("Criada em", active.created_at)

    console.print(table)


@mission_app.command("end")
def mission_end_cmd(
    project_dir: Annotated[
        str, typer.Option("--project-dir", "-p", help="Diretório raiz do projeto")
    ] = ".",
    force_abort: Annotated[
        bool,
        typer.Option(
            "--force-abort",
            "-f",
            help="Força o encerramento da missão mesmo com rounds ou DoDs pendentes",
        ),
    ] = False,
) -> None:
    """Encerra a missão ativa após validação de DoD ou de forma forçada."""
    engine = MissionLifecycleEngine(project_dir=project_dir)
    try:
        completed = engine.complete_mission(force=force_abort)
        panel = Panel.fit(
            f"[bold green]Missão {completed.id} encerrada com sucesso![/bold green]\n\n"
            f"[bold]Status final:[/bold] {completed.status.value}\n"
            f"[bold]Concluída em:[/bold] {completed.completed_at}",
            title="🏁 Missão Concluída",
            border_style="green",
        )
        console.print(panel)
    except PendingDoDError as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE (DoD Pendente):[/bold red] {exc}")
        console.print("[yellow]Dica: use --force-abort para forçar o encerramento.[/yellow]")
        raise typer.Exit(code=1) from exc
    except NoActiveMissionError as exc:
        console.print(f"[bold yellow]Aviso:[/bold yellow] {exc}")
        raise typer.Exit(code=1) from exc
