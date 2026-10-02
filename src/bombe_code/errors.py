"""Tratamento global e elegante de erros para o Bombe Code."""

from __future__ import annotations

import datetime
import logging
import os
import traceback
from pathlib import Path

from rich.panel import Panel

from .config.paths import get_paths

logger = logging.getLogger(__name__)


def is_debug_mode() -> bool:
    """Retorna True se o modo de depuração detalhada estiver ativado."""
    return os.environ.get("BOMBE_DEBUG") == "1"


def record_exception(exc: BaseException | None = None, context: str = "TUI") -> Path:
    """Grava o traceback técnico completo em arquivo de log de forma segura.

    Retorna o Path do arquivo de log onde o erro foi registrado.
    """
    try:
        log_dir = get_paths().log
        log_dir.mkdir(parents=True, exist_ok=True)
        err_file = log_dir / "error.log"
    except OSError:
        err_file = Path.home() / ".bombe_error.log"

    ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"\n{'=' * 72}\n[{ts}] ERRO INESPERADO (Contexto: {context})\n"
    footer = f"\n{'=' * 72}\n"

    try:
        with open(err_file, "a", encoding="utf-8") as f:
            f.write(header)
            if exc is not None:
                f.write(f"Tipo: {type(exc).__name__}\n")
                f.write(f"Mensagem: {exc}\n\n")
                f.write("Traceback:\n")
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            else:
                f.write("Traceback:\n")
                f.write(traceback.format_exc())
            f.write(footer)
    except OSError as log_err:
        logger.warning("Falha ao registrar exceção no arquivo de log: %s", log_err)

    return err_file


def format_error_panel(
    exc: BaseException | None,
    log_file: Path,
    title: str = "Bombe Code — Erro Inesperado",
) -> Panel:
    """Gera um painel Rich elegante para exibição ao usuário final, sem vazar código."""
    if exc and str(exc).strip():
        exc_summary = str(exc)
    elif exc:
        exc_summary = type(exc).__name__
    else:
        exc_summary = "Erro interno de execução"
    # Limita mensagem para não vazar estruturas gigantes ou dados sensíveis
    if len(exc_summary) > 200:
        exc_summary = exc_summary[:197] + "..."

    content = (
        f"[bold red]Ocorreu um erro inesperado no Bombe Code.[/bold red]\n\n"
        f"[dim]{exc_summary}[/dim]\n\n"
        f"A aplicação foi finalizada com segurança para proteger seus dados e sessão.\n"
        f"Os detalhes técnicos completos foram gravados em:\n"
        f"[cyan underline]{log_file}[/cyan underline]\n\n"
        f"[dim]Para desenvolvedores: execute com BOMBE_DEBUG=1 para ver o traceback no terminal.[/dim]"
    )

    return Panel(
        content,
        title=f"[bold red]{title}[/bold red]",
        border_style="red",
        expand=False,
    )
