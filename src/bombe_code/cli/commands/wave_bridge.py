"""CLI commands and banner for Wave Bridge backwards compatibility."""

from __future__ import annotations

import re
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from bombe_code.cli.commands.mission import mission_end_cmd
from bombe_code.cli.commands.round import (
    round_all_cmd,
    round_burn_cmd,
    round_start_cmd,
    round_status_cmd,
    round_validate_cmd,
)

console = Console()
wave_app = typer.Typer(
    name="wave",
    help="Ponte de retrocompatibilidade para comandos legados de ondas.",
)


def render_wave_deprecation_banner(legacy_cmd: str, canonical_cmd: str) -> None:
    """Renderiza banner educativo informando a substituição de ONDAS por ROUNDS."""
    content = (
        "[bold yellow]⚠️  AVISO DE DEPRECIAÇÃO (WAVE BRIDGE)[/bold yellow]\n\n"
        f"O comando legado [bold magenta]{legacy_cmd}[/bold magenta] foi redirecionado.\n"
        "No [bold]Bombe Core v4[/bold], o conceito de [bold red]ONDA[/bold red] foi substituído por "
        "[bold green]ROUNDS e SLICES[/bold green] (esteira MISSION).\n\n"
        f"➡️  Comando canônico equivalente: [bold cyan]{canonical_cmd}[/bold cyan]"
    )
    console.print(
        Panel.fit(
            content,
            title="[bold magenta]Bombe Wave Bridge[/bold magenta]",
            border_style="yellow",
        )
    )


def parse_wave_id_to_round_num(wave_id: str | int | None) -> int:
    """Extrai o número inteiro do round a partir do identificador de onda."""
    if wave_id is None:
        return 1
    if isinstance(wave_id, int):
        return wave_id if wave_id > 0 else 1
    cleaned = wave_id.strip()
    if not cleaned:
        return 1
    matches = re.findall(r"\d+", cleaned)
    if not matches:
        return 1
    try:
        val = int(matches[0])
        return val if val > 0 else 1
    except ValueError:
        return 1


@wave_app.command("start")
def wave_start_bridge(
    wave_id: Annotated[
        str,
        typer.Argument(help="ID da onda legada (ex: ONDA-001)"),
    ] = "1",
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave start e redireciona para round-start."""
    round_num = parse_wave_id_to_round_num(wave_id)
    render_wave_deprecation_banner(
        legacy_cmd=f"bombe wave start {wave_id}",
        canonical_cmd=f"bombe round start {round_num}",
    )
    round_start_cmd(round_num=round_num, project_dir=project_dir)


@wave_app.command("run")
def wave_run_bridge(
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave run e redireciona para round-all (pipeline contínuo)."""
    render_wave_deprecation_banner(
        legacy_cmd="bombe wave run",
        canonical_cmd="bombe round all",
    )
    round_all_cmd(project_dir=project_dir)


@wave_app.command("cycle")
def wave_cycle_bridge(
    wave_id: Annotated[
        str,
        typer.Argument(help="ID da onda legada (ex: ONDA-001)"),
    ] = "1",
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave cycle e redireciona para round burn."""
    round_num = parse_wave_id_to_round_num(wave_id)
    render_wave_deprecation_banner(
        legacy_cmd=f"bombe wave cycle {wave_id}",
        canonical_cmd=f"bombe round burn {round_num}",
    )
    round_burn_cmd(round_num=round_num, project_dir=project_dir)


@wave_app.command("validate")
def wave_validate_bridge(
    wave_id: Annotated[
        str,
        typer.Argument(help="ID da onda legada (ex: ONDA-001)"),
    ] = "1",
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave validate e redireciona para round validate."""
    round_num = parse_wave_id_to_round_num(wave_id)
    render_wave_deprecation_banner(
        legacy_cmd=f"bombe wave validate {wave_id}",
        canonical_cmd=f"bombe round validate {round_num}",
    )
    round_validate_cmd(round_num=round_num, project_dir=project_dir)


@wave_app.command("status")
def wave_status_bridge(
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave status e redireciona para round status."""
    render_wave_deprecation_banner(
        legacy_cmd="bombe wave status",
        canonical_cmd="bombe round status",
    )
    round_status_cmd(round_num=None, project_dir=project_dir)


@wave_app.command("promote")
def wave_promote_bridge(
    env: Annotated[
        str,
        typer.Argument(help="Destino da promoção: dev | hml | main"),
    ] = "dev",
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
) -> None:
    """Intercepta wave promote e redireciona para project ship."""
    render_wave_deprecation_banner(
        legacy_cmd=f"bombe wave promote {env}",
        canonical_cmd=f"bombe project ship {env}",
    )
    from bombe_code.turing.promocao import PromotorDeBranches

    promotor = PromotorDeBranches(project_dir)
    destino_norm = env.strip().lower()
    if destino_norm == "dev":
        res = promotor.promover_para_dev(
            "feat: promoção manual do estado aprovado da IA (squash)"
        )
    else:
        res = promotor.promover_fase(destino_norm)
    if res.success:
        console.print(f"[bold green]✓[/bold green] {res.mensagem}")
        for d in res.detalhes:
            console.print(f"  • {d}")
    else:
        console.print(f"[bold red]❌[/bold red] {res.mensagem}")
        raise typer.Exit(code=1)


@wave_app.command("end")
def wave_end_bridge(
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-p", help="Diretório raiz do projeto"),
    ] = ".",
    force_abort: Annotated[
        bool,
        typer.Option(
            "--force-abort",
            "-f",
            help="Força o encerramento da missão mesmo com rounds pendentes",
        ),
    ] = False,
) -> None:
    """Intercepta wave end e redireciona para mission end."""
    render_wave_deprecation_banner(
        legacy_cmd="bombe wave end",
        canonical_cmd="bombe mission end",
    )
    mission_end_cmd(project_dir=project_dir, force_abort=force_abort)
