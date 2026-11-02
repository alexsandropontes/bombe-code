"""CLI commands for standalone operations and decoupled governance."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bombe_code.config.project_config import InvalidModeError
from bombe_code.orchestration.standalone_engine import StandaloneEngine

console = Console()
standalone_app = typer.Typer(
    name="standalone", help="Comandos de governança e operações standalone."
)


@standalone_app.command("mode")
def mode_cmd(
    mode_str: Annotated[
        str,
        typer.Argument(help="Modo de engenharia: slice-flow ou vibe-flow"),
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Alterna modo de engenharia entre slice-flow e vibe-flow com auditoria."""
    engine = StandaloneEngine(project_dir=project_dir)
    try:
        is_autonomy = mode_str.strip().lower() in {"auto", "semi-auto", "semi_auto", "manual"}
        cfg = engine.switch_mode(mode_str)
        tipo_modo = "autonomia" if is_autonomy else "engenharia"
        panel = Panel.fit(
            f"[bold green]Modo de {tipo_modo} alterado com sucesso![/bold green]\n\n"
            f"• Modo Atual: [cyan]{cfg.autonomy if is_autonomy else cfg.mode}[/cyan]\n"
            + (
                f"• Modo Anterior: [yellow]{cfg.mode_origin}[/yellow]\n• Migrado em: {cfg.mode_migrated_at}"
                if not is_autonomy
                else ""
            ),
            title="🔄 Bombe Mode",
            border_style="green",
        )
        console.print(panel)
    except InvalidModeError as exc:
        console.print(f"[bold red]ERRO:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@standalone_app.command("task")
def task_cmd(
    description: Annotated[str, typer.Argument(help="Descrição da tarefa avulsa")],
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Especialista para despachar (ex: @unclebob, @grace)"),
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa e despacha tarefa avulsa via Protocolo Garçom."""
    engine = StandaloneEngine(project_dir=project_dir)
    res = engine.dispatch_task(description=description, agent=agent)
    panel = Panel.fit(
        f"[bold green]Task executada e despachada com sucesso![/bold green]\n\n"
        f"• Especialista: [cyan]{res['agent']}[/cyan]\n"
        f"• Status: [yellow]{res['status']}[/yellow]\n"
        f"• Tarefa: {res['task']}\n\n"
        f"{res['output']}",
        title="🎯 Bombe Task",
        border_style="cyan",
    )
    console.print(panel)


@standalone_app.command("rca")
def rca_cmd(
    incident: Annotated[
        str, typer.Argument(help="Descrição do incidente para análise de causa raiz")
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa Análise de Causa Raiz determinística (5 Whys) sob @unclebob."""
    engine = StandaloneEngine(project_dir=project_dir)
    res = engine.run_rca(incident=incident)
    panel = Panel.fit(
        f"[bold red]Incidente:[/bold red] {res['incident']}\n"
        f"[bold cyan]Auditor:[/bold cyan] {res['agent']} ({res['methodology']})\n\n"
        f"[bold]Cadeia Causal (5 Porquês):[/bold]\n"
        + "\n".join(f"  • {c}" for c in res["causes"])
        + "\n\n[bold]Ações Corretivas Propostas:[/bold]\n"
        + "\n".join(f"  [green]✓[/green] {a}" for a in res["corrective_actions"]),
        title="🔧 Root Cause Analysis (RCA)",
        border_style="red",
    )
    console.print(panel)


@standalone_app.command("review")
def review_cmd(
    target: Annotated[
        str | None,
        typer.Argument(help="Caminho do diretório ou arquivo alvo para revisão"),
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa auditoria técnica avulsa multi-eixo sob personas @hoare e @unclebob."""
    engine = StandaloneEngine(project_dir=project_dir)
    res = engine.run_review(target_path=target)
    table = Table(title=f"Auditoria de Qualidade — Alvo: {res['target']}")
    table.add_column("Eixo de Qualidade", style="cyan")
    table.add_column("Status", style="green")
    for eixo, status in res["axes"].items():
        table.add_row(eixo.capitalize(), f"[green]✓ {status}[/green]")

    console.print(table)
    console.print(f"[bold green]Parecer:[/bold green] {res['summary']}")


@standalone_app.command("simplify")
def simplify_cmd(
    target: Annotated[
        str | None,
        typer.Argument(help="Caminho do arquivo ou módulo para auditoria de simplificação"),
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa auditoria de simplificação de código sob @unclebob."""
    engine = StandaloneEngine(project_dir=project_dir)
    res = engine.run_simplify(target_path=target)
    panel = Panel.fit(
        f"[bold]Alvo:[/bold] {res['target']}\n"
        f"[bold]Complexidade:[/bold] [green]{res['cyclomatic_complexity']}[/green]\n\n"
        f"[bold]Propostas de Simplificação:[/bold]\n"
        + "\n".join(f"  • {p}" for p in res["simplification_proposals"])
        + f"\n\n{res['output']}",
        title="✨ Code Simplification Audit",
        border_style="magenta",
    )
    console.print(panel)


@standalone_app.command("status-report")
@standalone_app.command("report")
def status_report_cmd(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Gera relatório executivo geral do repositório."""
    engine = StandaloneEngine(project_dir=project_dir)
    rep = engine.generate_status_report()
    panel = Panel.fit(
        f"[bold]Projeto:[/bold] [cyan]{rep['project_name']}[/cyan]\n"
        f"• Relatório Consolidado do Projeto\n"
        f"• Modo de Engenharia: [green]{rep['mode']}[/green]\n"
        f"• Backend / Frontend: {rep['backend_language']} / {rep['frontend_stack']}\n"
        f"• Autonomia: {rep['autonomy']}\n"
        f"• Missões Encontradas: {rep['missions_count']}\n"
        f"• Relatório Gerado em: {rep['generated_at']}",
        title="📊 Status Report do Projeto",
        border_style="blue",
    )
    console.print(panel)
