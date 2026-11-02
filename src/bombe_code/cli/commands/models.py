"""CLI commands for managing the cognitive models matrix, providers, and authentication."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bombe_code.providers.auth import load_auth, save_api_key, save_provider_url
from bombe_code.providers.models_dev import get_models
from bombe_code.routing.matrix import (
    DemandSituation,
    ModelSlot,
    RoutingMatrixConfig,
    load_matrix,
    save_matrix,
)
from bombe_code.routing.quota_manager import QuotaManager

logger = logging.getLogger(__name__)
console = Console()

models_app = typer.Typer(
    name="models",
    help="Gerenciamento da Matriz Cognitiva de Modelos, Provedores e Autenticação.",
    invoke_without_command=True,
)

SITUATION_LABELS = {
    DemandSituation.JUNIOR.value: "Junior (Jr) — Slices leves (<50 linhas, arquivo único)",
    DemandSituation.PLENO.value: "Pleno (PL) — Slices intermediários (50-200 linhas)",
    DemandSituation.SENIOR.value: "Senior (Sr) — Slices críticos (>200 linhas, concorrência/auth)",
    DemandSituation.UPSTREAM_CRITICAL.value: "Upstream Crítico — Inception macro, arquitetura, DDD, PRDs densos",
    DemandSituation.UPSTREAM_LIGHT.value: "Upstream Leve — Discovery inicial, briefings, refinamentos leves",
    DemandSituation.FINAL_REVIEW.value: "Review Final — Portão de qualidade, UncleBob, Hoare e DoD",
}


def _render_matrix_table(matrix: RoutingMatrixConfig, quota_mgr: QuotaManager) -> None:
    table = Table(
        title="🤖 Matriz Cognitiva de Modelos (Bombe Code)",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Situação de Demanda", style="bold yellow", min_width=22)
    table.add_column("Modelo Primário", style="bold green", min_width=25)
    table.add_column("Status Primário", min_width=18)
    table.add_column("Modelo Fallback", style="bold magenta", min_width=25)
    table.add_column("Status Fallback", min_width=18)

    for situation in DemandSituation:
        sit_key = situation.value
        route = matrix.get_route(sit_key)
        label = SITUATION_LABELS.get(sit_key, sit_key)

        # Primário
        if route.primary is not None:
            prim_desc = f"{route.primary.provider}/{route.primary.model}"
            if "local" in route.primary.provider.lower():
                prim_status = "[bold green]⚪ Local Pronto[/bold green]"
            else:
                p_status = quota_mgr.get_provider_status(route.primary.provider)
                if p_status.status == "exhausted":
                    lock_desc = (
                        p_status.locked_until.strftime("%H:%M:%S")
                        if p_status.locked_until
                        else "Ativo"
                    )
                    prim_status = f"[bold yellow]🟡 Cooldown ({lock_desc})[/bold yellow]"
                else:
                    prim_status = "[bold green]🟢 Disponível[/bold green]"
        else:
            prim_desc = "[dim](não configurado)[/dim]"
            prim_status = "[dim]—[/dim]"

        # Fallback
        if route.fallback is not None:
            fb_desc = f"{route.fallback.provider}/{route.fallback.model}"
            if "local" in route.fallback.provider.lower():
                fb_status = "[bold green]⚪ Local Pronto[/bold green]"
            else:
                fb_p_status = quota_mgr.get_provider_status(route.fallback.provider)
                if fb_p_status.status == "exhausted":
                    fb_lock_desc = (
                        fb_p_status.locked_until.strftime("%H:%M:%S")
                        if fb_p_status.locked_until
                        else "Ativo"
                    )
                    fb_status = f"[bold yellow]🟡 Cooldown ({fb_lock_desc})[/bold yellow]"
                else:
                    fb_status = "[bold green]🟢 Disponível[/bold green]"
        else:
            fb_desc = "[dim](nenhum)[/dim]"
            fb_status = "[dim]—[/dim]"

        table.add_row(label, prim_desc, prim_status, fb_desc, fb_status)

    console.print(table)


@models_app.callback()
def models_main(ctx: typer.Context) -> None:
    """Exibe o status da matriz de modelos se nenhum subcomando for chamado."""
    if ctx.invoked_subcommand is None:
        matrix = load_matrix()
        quota_mgr = QuotaManager()
        if not matrix.is_configured():
            console.print(
                Panel.fit(
                    "[bold yellow]⚠️  Nenhuma LLM está configurada no Bombe Code![/bold yellow]\n\n"
                    "Comandos puramente determinísticos funcionam normalmente.\n"
                    "Para habilitar comandos e esteiras que utilizam IA, execute:\n\n"
                    "  [bold green]bombe-code models setup[/bold green]  (Modo Fácil: configura tudo de uma vez)\n"
                    "  [bold cyan]bombe-code models set <situacao>[/bold cyan] (Modo Avançado: por situação)\n"
                    "  [bold magenta]bombe-code models auth <provider> <chave>[/bold magenta] (Configura credenciais)\n",
                    title="Configuração de IA Pendente",
                    border_style="yellow",
                )
            )
            catalog_models()
        else:
            _render_matrix_table(matrix, quota_mgr)


@models_app.command("matrix")
@models_app.command("status")
def matrix_status() -> None:
    """Exibe a tabela detalhada da matriz de roteamento e status de cota/cooldown."""
    matrix = load_matrix()
    quota_mgr = QuotaManager()
    _render_matrix_table(matrix, quota_mgr)


@models_app.command("setup")
def quick_setup(
    provider: Annotated[
        Optional[str],
        typer.Option("--provider", "-p", help="Provedor principal (ex: zai, vllm-local, openai, ollama)"),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Identificador do modelo principal (ex: glm-5.3-flash, qwen-3.8-9b)"),
    ] = None,
    fallback_provider: Annotated[
        Optional[str],
        typer.Option("--fallback-provider", "-fp", help="Provedor de contingência opcional (ex: vllm-local)"),
    ] = None,
    fallback_model: Annotated[
        Optional[str],
        typer.Option("--fallback-model", "-fm", help="Modelo de contingência opcional (ex: qwen-3.8-9b, gemma-4-e4b)"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="Chave de API do provedor (se aplicável)"),
    ] = None,
) -> None:
    """Modo Fácil: Configura o par Primário + Fallback e replica para todas as 6 situações."""
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Modo Fácil: Configuração Global de Modelos[/bold cyan]\n"
            "Esta configuração será aplicada a todas as situações (Jr, Pleno, Senior, Upstream e Reviews).",
            border_style="cyan",
        )
    )

    if not provider:
        provider = typer.prompt("Provedor Principal (ex: zai, vllm-local, openai, ollama)", default="zai")
    if not model:
        model = typer.prompt("Modelo Principal (ex: glm-5.3-flash, qwen-3.8-9b, gpt-4o)", default="glm-5.3-flash")

    if not fallback_provider:
        fallback_provider = typer.prompt(
            "Provedor Fallback (opcional, ex: vllm-local ou deixe em branco)",
            default="vllm-local",
        )
    if fallback_provider and not fallback_model:
        fallback_model = typer.prompt(
            "Modelo Fallback (ex: qwen-3.8-9b, gemma-4-e4b)",
            default="qwen-3.8-9b",
        )

    # Salva chave de API se fornecida
    if api_key and provider:
        save_api_key(provider.strip(), api_key.strip())
        console.print(f"[green]✓ Chave de API gravada com segurança para '{provider}'![/green]")

    matrix = load_matrix()
    primary_slot = ModelSlot(provider=provider.strip(), model=model.strip())
    fb_slot = (
        ModelSlot(provider=fallback_provider.strip(), model=fallback_model.strip())
        if fallback_provider and fallback_model
        else None
    )

    matrix.quick_setup(primary=primary_slot, fallback=fb_slot)
    save_matrix(matrix)

    console.print(
        f"\n[bold green]✓ Configuração concluída com sucesso![/bold green]\n"
        f"  • Principal: [bold]{provider}/{model}[/bold]\n"
        f"  • Fallback:  [bold]{fallback_provider or 'nenhum'}/{fallback_model or 'nenhum'}[/bold]\n"
        f"Replicado deterministicamente para todas as 6 situações de engenharia.\n"
    )


@models_app.command("set")
def set_situation(
    situation: Annotated[
        str,
        typer.Argument(
            help="Situação a configurar: junior, pleno, senior, upstream_critical, upstream_light, final_review"
        ),
    ],
    provider: Annotated[str, typer.Option("--provider", "-p", help="Provedor principal")],
    model: Annotated[str, typer.Option("--model", "-m", help="Modelo principal")],
    fallback_provider: Annotated[
        Optional[str],
        typer.Option("--fallback-provider", "-fp", help="Provedor de fallback"),
    ] = None,
    fallback_model: Annotated[
        Optional[str],
        typer.Option("--fallback-model", "-fm", help="Modelo de fallback"),
    ] = None,
) -> None:
    """Modo Avançado: Customiza individualmente uma situação específica de demanda."""
    matrix = load_matrix()
    sit_clean = situation.strip().lower()

    primary_slot = ModelSlot(provider=provider.strip(), model=model.strip())
    fb_slot = (
        ModelSlot(provider=fallback_provider.strip(), model=fallback_model.strip())
        if fallback_provider and fallback_model
        else None
    )

    try:
        matrix.set_route(sit_clean, primary=primary_slot, fallback=fb_slot)
        save_matrix(matrix)
        console.print(
            f"[bold green]✓ Situação '{sit_clean}' atualizada com sucesso![/bold green]\n"
            f"  • Principal: {provider}/{model}\n"
            f"  • Fallback:  {fallback_provider or 'nenhum'}/{fallback_model or 'nenhum'}"
        )
    except ValueError as exc:
        console.print(f"[bold red]Erro:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@models_app.command("auth")
def auth_provider(
    provider: Annotated[str, typer.Argument(help="Nome do provedor (ex: zai, openai, anthropic, ollama)")],
    api_key: Annotated[Optional[str], typer.Argument(help="Chave de API do provedor (opcional se for local)")] = None,
    base_url: Annotated[Optional[str], typer.Option("--base-url", "-u", help="URL base customizada (ex: http://localhost:11434/v1)")] = None,
) -> None:
    """Configura credenciais e endpoints de provedores de forma segura no Bombe Code."""
    prov_clean = provider.strip().lower()
    if api_key:
        save_api_key(prov_clean, api_key.strip())
        console.print(f"[bold green]✓ Chave de API gravada para '{prov_clean}' em bombe-code/auth.json![/bold green]")
    if base_url:
        save_provider_url(prov_clean, base_url.strip())
        console.print(f"[bold green]✓ Base URL configurada para '{prov_clean}': {base_url}![/bold green]")

    if not api_key and not base_url:
        key_input = typer.prompt(f"Digite a API Key para '{prov_clean}'", hide_input=True)
        if key_input:
            save_api_key(prov_clean, key_input.strip())
            console.print(f"[bold green]✓ Chave de API gravada com sucesso para '{prov_clean}'![/bold green]")


@models_app.command("catalog")
def catalog_models() -> None:
    """Lista catálogo de modelos suportados disponíveis no models.dev e offline."""
    try:
        cat = get_models()
        console.print("[bold cyan]Catálogo Geral de Modelos (models.dev):[/bold cyan]")
        for prov, info in cat.items():
            if isinstance(info, dict) and "models" in info:
                mod_names = ", ".join(list(info["models"].keys())[:5])
                console.print(f"  • [bold]{prov}[/bold]: {mod_names}...")
    except (OSError, RuntimeError, httpx.HTTPError):
        console.print("[bold yellow]Catálogo Geral de Modelos (offline):[/bold yellow]")
        console.print("  • [bold]zai[/bold]: glm-5.3-flash, glm-4-plus, glm-4.7-flash")
        console.print("  • [bold]openai[/bold]: gpt-4o, gpt-4o-mini, o1")
        console.print("  • [bold]anthropic[/bold]: claude-3-5-sonnet, claude-3-5-haiku")
        console.print("  • [bold]google[/bold]: gemini-1.5-pro, gemini-2.0-flash")
        console.print("  • [bold]vllm-local[/bold]: qwen-3.8-9b, gemma-4-e4b, gemma-4-26b-a4b, lfm3")
