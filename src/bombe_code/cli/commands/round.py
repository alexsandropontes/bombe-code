"""CLI commands for Round execution triad (round-start, round-full, round-all)."""

from __future__ import annotations

import typer
from rich.console import Console

from bombe_code.orchestration.engine import (
    InvalidRoundScopeError,
    PendingDoDError,
    RoundExecutionEngine,
)

console = Console()
round_app = typer.Typer(
    name="round", help="Comandos da Tríade de Rounds (Manual, Semi-Auto e Pipeline)."
)


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
        console.print(
            f"[bold green]✓[/bold green] [cyan]Round {round_num}[/cyan] ({res['story_id']}) iniciado."
        )
        console.print(f"[bold yellow]PARADA DETERMINÍSTICA:[/bold yellow] {res['message']}")
    except (InvalidRoundScopeError, PendingDoDError, FileNotFoundError) as exc:
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
