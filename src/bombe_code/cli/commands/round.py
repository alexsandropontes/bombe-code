"""CLI commands for Round execution triad and manual lifecycle with DoR gates."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bombe_code.domain.contracts.round import (
    InvalidRoundStateError,
    RoundNotReadyError,
    RoundState,
)
from bombe_code.orchestration.engine import (
    InvalidRoundScopeError,
    PendingDoDError,
    RoundExecutionEngine,
)

console = Console()
round_app = typer.Typer(
    name="round", help="Comandos da Tríade de Rounds (Manual, Semi-Auto e Pipeline)."
)


def _get_status_color(status: str) -> str:
    """Map round status to appropriate rich color."""
    colors = {
        "pending": "dim",
        "dor_ready": "yellow",
        "burning": "cyan",
        "reviewing": "magenta",
        "validated": "green",
    }
    return colors.get(status, "white")


@round_app.command("round-start")
@round_app.command("start")
def round_start_cmd(
    round_num: int = typer.Argument(..., help="Número do round a ser iniciado"),
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo MANUAL: Executa Upstream, valida DoR e para deterministamente na fronteira do DoR."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        res = engine.start_round(round_num)
        panel_content = (
            f"[bold green]✓ Round {round_num}[/bold green] ([cyan]{res.story_id}[/cyan]) iniciado.\n"
            f"[bold yellow]DoR Gate:[/bold yellow] [green]READY[/green]\n"
            f"[bold yellow]PARADA DETERMINÍSTICA:[/bold yellow] {res.message}"
        )
        console.print(
            Panel.fit(panel_content, title="[bold]Round Start (DoR Gate)[/bold]", border_style="green")
        )
    except (InvalidRoundScopeError, PendingDoDError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("burn")
def round_burn_cmd(
    round_num: int = typer.Argument(..., help="Número do round a queimar"),
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo MANUAL: Queima downstream dos slices (apenas após DoR atingido)."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        res = engine.burn_round(round_num)
        slices_str = ", ".join(f"{s.slice_id} ({s.status})" for s in res.slices)
        panel_content = (
            f"[bold green]✓ Round {round_num}[/bold green] ([cyan]{res.story_id}[/cyan]) queimado.\n"
            f"[bold cyan]Slices:[/bold cyan] {slices_str}\n"
            f"[bold yellow]Próximo passo:[/bold yellow] bombe round review {round_num}"
        )
        console.print(
            Panel.fit(panel_content, title="[bold]Round Burn (Slices Concluídos)[/bold]", border_style="cyan")
        )
    except RoundNotReadyError as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE (DoR Gate):[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except (InvalidRoundScopeError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("review")
def round_review_cmd(
    round_num: int = typer.Argument(..., help="Número do round a revisar"),
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo MANUAL: Executa code review e story compliance do round."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        res = engine.review_round(round_num)
        console.print(
            f"[bold green]✓[/bold green] [cyan]Round {round_num}[/cyan] ({res.story_id}) [green]REVISADO[/green]."
        )
        console.print(f"[bold green]STATUS:[/bold green] {res.message}")
    except (InvalidRoundStateError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("validate")
def round_validate_cmd(
    round_num: int = typer.Argument(..., help="Número do round a validar"),
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo MANUAL: Valida checklist de Definition of Done (DoD) e conclui o round."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        res = engine.validate_round(round_num)
        panel_content = (
            f"[bold green]✓ Round {round_num}[/bold green] ([cyan]{res.story_id}[/cyan]) [bold green]VALIDADO[/bold green].\n"
            f"[bold green]DoD Gate:[/bold green] [green]VALIDATED[/green]\n"
            f"[bold yellow]PARADA DETERMINÍSTICA:[/bold yellow] {res.message}"
        )
        console.print(
            Panel.fit(panel_content, title="[bold]Round Validate (DoD Validado)[/bold]", border_style="green")
        )
    except (InvalidRoundScopeError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("status")
def round_status_cmd(
    round_num: Annotated[int | None, typer.Argument(help="Número do round específico (opcional)")] = None,
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Exibe tabela com status, slices e gates (DoR e DoD) dos rounds."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        result = engine.status_round(round_num)
        rounds_list = [result] if isinstance(result, RoundState) else result

        table = Table(title="Status dos Rounds da Missão", header_style="bold magenta")
        table.add_column("Round", style="cyan", justify="center")
        table.add_column("Story", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Slices", style="dim")
        table.add_column("DoR Gate", justify="center")
        table.add_column("DoD Gate", justify="center")

        for r in rounds_list:
            dor_str = "[green]✓ READY[/green]" if r.dor_ready else "[yellow]PENDING[/yellow]"
            dod_str = "[green]✓ VALIDATED[/green]" if r.dod_validated else "[yellow]PENDING[/yellow]"
            slices_summary = (
                f"{len([s for s in r.slices if s.status == 'done'])}/{len(r.slices)} done"
                if r.slices
                else "-"
            )
            table.add_row(
                f"Round {r.round_number}",
                r.story_id,
                f"[{_get_status_color(r.status.value)}]{r.status.value}[/]",
                slices_summary,
                dor_str,
                dod_str,
            )

        console.print(table)
    except FileNotFoundError as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("round-full")
@round_app.command("full")
def round_full_cmd(
    round_num: int = typer.Argument(..., help="Número do round a ser executado"),
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo SEMI-AUTO: Executa Upstream, Queima TDD dos slices, validação e para no final do round."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        res = engine.full_round(round_num)
        console.print(
            f"[bold green]✓[/bold green] [cyan]Round {round_num}[/cyan] ({res['story_id']}) validado com sucesso."
        )
        console.print(f"[bold green]CONCLUÍDO:[/bold green] {res['message']}")
    except (InvalidRoundScopeError, PendingDoDError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@round_app.command("round-all")
@round_app.command("all")
def round_all_cmd(
    project_dir: str = typer.Option(".", "--project-dir", "-p", help="Diretório raiz do projeto"),
) -> None:
    """Modo PIPELINE CONTÍNUO: Itera sequencialmente por todos os rounds pendentes da missão."""
    engine = RoundExecutionEngine(project_dir=project_dir)
    try:
        results = engine.all_rounds()
        if not results:
            console.print("[bold yellow]Nenhum round pendente encontrado na missão.[/bold yellow]")
            return

        console.print(
            f"[bold green]✓ Pipeline concluído:[/bold green] {len(results)} rounds executados com sucesso."
        )
        for r in results:
            console.print(f"  - Round {r['round']} ({r['story_id']}): [green]{r['status']}[/green]")
    except (InvalidRoundScopeError, PendingDoDError, FileNotFoundError) as exc:
        console.print(f"[bold red]ERRO BLOQUEANTE NO PIPELINE:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
