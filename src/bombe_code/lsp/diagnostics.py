"""Módulo de diagnósticos LSP e checagem sintática."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Diagnostic:
    line: int
    column: int
    message: str
    severity: str = "error"


class DiagnosticsManager:
    """Extrai diagnósticos e erros de sintaxe para enriquecer o output de ferramentas."""

    def get_diagnostics(self, file_path: str) -> list[Diagnostic]:
        path = Path(file_path)
        if not path.is_file():
            return []

        diagnostics: list[Diagnostic] = []
        if path.suffix == ".py":
            try:
                content = path.read_text(encoding="utf-8")
                ast.parse(content, filename=str(path))
            except SyntaxError as exc:
                diagnostics.append(
                    Diagnostic(
                        line=exc.lineno or 1,
                        column=exc.offset or 1,
                        message=f"SyntaxError: {exc.msg}",
                        severity="error",
                    )
                )

        return diagnostics

    def inject_into_output(self, tool_output: str, file_path: str) -> str:
        """Injeta diagnósticos no retorno da ferramenta se houver falhas."""
        diags = self.get_diagnostics(file_path)
        if not diags:
            return tool_output

        diag_lines = [f"  • Linha {d.line}:{d.column} [{d.severity}]: {d.message}" for d in diags]
        summary = "\n[LSP Diagnostics:]\n" + "\n".join(diag_lines)
        return f"{tool_output}\n{summary}"
