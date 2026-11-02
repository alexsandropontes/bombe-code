"""CLI commands for project governance, configuration, and gated promotion."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.domain.contracts.ship import ShipTarget
from bombe_code.orchestration.ship_engine import ShipEngine
from bombe_code.starters.engine import StarterEngine

console = Console()
project_app = typer.Typer(
    name="project", help="Comandos de gestão, configuração e deploy de projetos."
)

starter_cli = typer.Typer(name="starter", help="Gerenciador de starters e scaffolds de projetos.")
project_app.add_typer(starter_cli, name="starter")


@project_app.command("configure")
def project_configure(
    mode: Annotated[
        str | None, typer.Option("--mode", "-m", help="Modo: slice-flow ou vibe-flow")
    ] = None,
    backend_path: Annotated[
        str | None, typer.Option("--backend-path", help="Subdiretório de backend")
    ] = None,
    frontend_path: Annotated[
        str | None, typer.Option("--frontend-path", help="Subdiretório de frontend")
    ] = None,
    backend_language: Annotated[
        str | None, typer.Option("--backend-language", help="Linguagem do backend")
    ] = None,
    frontend_stack: Annotated[
        str | None, typer.Option("--frontend-stack", help="Stack de frontend")
    ] = None,
    autonomy: Annotated[
        str | None, typer.Option("--autonomy", help="Autonomia: auto, semi-auto, manual")
    ] = None,
    delivery_target: Annotated[
        str | None, typer.Option("--delivery-target", help="Maturidade: poc, mvp, enterprise-grade")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Configura e atualiza parâmetros operacionais no .bombeconfig."""
    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.load()

    if mode is not None:
        cfg.mode = mode
    if backend_path is not None:
        cfg.backend_path = backend_path
    if frontend_path is not None:
        cfg.frontend_path = frontend_path
    if backend_language is not None:
        cfg.backend_language = backend_language
    if frontend_stack is not None:
        cfg.frontend_stack = frontend_stack
    if autonomy is not None:
        cfg.autonomy = autonomy
    if delivery_target is not None:
        cfg.delivery_target = delivery_target

    mgr.save(cfg)
    panel = Panel.fit(
        f"[bold green]Configuração atualizada com sucesso em .bombeconfig![/bold green]\n\n"
        f"• Modo: [cyan]{cfg.mode}[/cyan]\n"
        f"• Backend: [cyan]{cfg.backend_language}[/cyan] ({cfg.backend_path})\n"
        f"• Frontend: [cyan]{cfg.frontend_stack}[/cyan] ({cfg.frontend_path})\n"
        f"• Autonomia: [cyan]{cfg.autonomy}[/cyan]\n"
        f"• Maturidade: [cyan]{cfg.delivery_target}[/cyan]",
        title="🛠️ Project Configure",
        border_style="green",
    )
    console.print(panel)


@project_app.command("ship")
def project_ship(
    env: Annotated[
        str,
        typer.Argument(help="Destino do ship: dev | hml | prd"),
    ] = "dev",
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Promoção Git protegida com execução prévia de testes automatizados."""
    try:
        target = ShipTarget(env.strip().lower())
    except ValueError:
        console.print(f"[bold red]ERRO:[/bold red] Destino inválido '{env}'. Use dev, hml ou prd.")
        raise typer.Exit(code=1) from None

    engine = ShipEngine(project_dir=project_dir)
    res = engine.promote_to_environment(target)

    if not res.success:
        console.print(
            f"[bold red]❌ Falha na promoção para {res.target_branch}:[/bold red] {res.message}"
        )
        for d in res.details:
            console.print(f"  • {d}")
        raise typer.Exit(code=1)

    panel = Panel.fit(
        f"[bold green]🚀 Promoção Git concluída com sucesso![/bold green]\n\n"
        f"• Ambiente: [cyan]{res.target_branch}[/cyan]\n"
        f"• Testes Pré-Flight: [green]APROVADOS[/green]\n"
        f"• Mensagem: {res.message}",
        title="🚢 Project Ship",
        border_style="green",
    )
    console.print(panel)


@project_app.command("detect")
def project_detect(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Autodetecta a stack tecnológica e salva no .bombeconfig."""
    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.detect_stack()
    mgr.save(cfg)
    console.print("[bold green]Stack autodetectada e salva em .bombeconfig:[/bold green]")
    console.print(f"- Backend: {cfg.backend_language} ({cfg.backend_path})")
    console.print(f"- Frontend: {cfg.frontend_stack} ({cfg.frontend_path})")


@project_app.command("config")
def project_config(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Exibe a configuração ativa do projeto."""
    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.load()
    console.print(f"[bold]Configuração do Projeto ({cfg.name}):[/bold]")
    console.print(f"- Tipo: {cfg.type}")
    console.print(f"- Backend: {cfg.backend_language}")
    console.print(f"- Frontend: {cfg.frontend_stack}")
    console.print(f"- Modo de Engenharia: {cfg.mode}")
    console.print(f"- Autonomia: {cfg.autonomy}")


@project_app.command("release")
def project_release(
    versao: Annotated[
        str | None, typer.Argument(help="Versão explícita (ex: 0.3.0). Vazio = sugestão automática")
    ] = None,
    mensagem: Annotated[
        str | None, typer.Option("--mensagem", "-m", help="Mensagem do commit de release")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Empacota e TAGA a versão na branch de trabalho."""
    from bombe_code.turing.promocao import PromotorDeBranches

    promotor = PromotorDeBranches(project_dir)
    analise = promotor.analisar_release()
    console.print(f"Última tag: {analise['ultima_tag']} | commits desde: {analise['total']}")
    console.print(
        f"Versão sugerida: {analise['versao_sugerida']}"
        + (f" | imposta: {versao}" if versao else "")
    )
    res = promotor.gerar_release(mensagem=mensagem, versao=versao)
    if res.success:
        console.print(f"✅ {res.mensagem}")
        for d in res.detalhes:
            console.print(f"  • {d}")
    else:
        console.print(f"❌ {res.mensagem}")
        raise typer.Exit(code=1)


@starter_cli.command("list")
def starter_list() -> None:
    """Lista todos os starters disponíveis no catálogo."""
    engine = StarterEngine()
    starters = engine.list_starters()
    console.print("Starters Disponíveis no Bombe Code:")
    for s in starters:
        console.print(f"• {s['id']} [{s['stack']}] — {s['name']}: {s['description']}")


@starter_cli.command("apply")
def starter_apply(
    starter_id: Annotated[str, typer.Argument(help="ID do starter a aplicar")],
    target_dir: Annotated[
        str, typer.Option("--target-dir", "-t", help="Diretório de destino")
    ] = ".",
    name: Annotated[str | None, typer.Option("--name", "-n", help="Nome do projeto")] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Sobrescrever arquivos existentes")
    ] = False,
) -> None:
    """Aplica o scaffolding do starter no diretório de destino."""
    engine = StarterEngine()
    res = engine.apply_starter(
        starter_id=starter_id,
        target_dir=target_dir,
        project_name=name,
        force=force,
    )
    if res.get("success"):
        console.print(res.get("message", "Starter aplicado com sucesso."))
        console.print(f"Arquivos gerados: {len(res.get('created_files', []))}")
    else:
        console.print(f"Erro ao aplicar starter: {res.get('error')}")
        raise typer.Exit(code=1)
