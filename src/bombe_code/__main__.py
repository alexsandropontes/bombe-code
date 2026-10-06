"""Ponto de entrada de execução do pacote bombe_code."""

from __future__ import annotations

import sys

from bombe_code.cli.main import app
from bombe_code.errors import format_error_panel, is_debug_mode, record_exception

if __name__ == "__main__":
    try:
        app()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except BaseException as exc:
        if is_debug_mode():
            raise
        log_file = record_exception(exc, context="CLI Entrypoint")
        from rich.console import Console

        console = Console(stderr=True)
        console.print(format_error_panel(exc, log_file))
        sys.exit(1)
