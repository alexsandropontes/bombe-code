"""Detector e executor resiliente de formatadores de código."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    ".py": "ruff",
    ".ts": "prettier",
    ".tsx": "prettier",
    ".js": "prettier",
    ".jsx": "prettier",
    ".json": "prettier",
    ".css": "prettier",
    ".scss": "prettier",
    ".html": "prettier",
    ".md": "prettier",
    ".go": "gofmt",
    ".rs": "rustfmt",
}


def detect_formatter_for_file(file_path: str | Path) -> str | None:
    """Retorna o formatador recomendado baseado na extensão do arquivo."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def format_code_file(file_path: str | Path, cwd: str = ".") -> bool:
    """Executa o formatador apropriado no arquivo. Retorna True se formatado com sucesso."""
    target_path = Path(file_path)
    if not target_path.exists():
        return False

    formatter = detect_formatter_for_file(target_path)
    if not formatter:
        return False

    resolved_file = str(target_path.resolve())

    try:
        if formatter == "ruff":
            # Tenta ruff direto, via python do ambiente ou via uv
            if shutil.which("ruff"):
                res = subprocess.run(
                    ["ruff", "format", resolved_file], cwd=cwd, capture_output=True, check=False
                )
                if res.returncode == 0:
                    return True
            res = subprocess.run(
                [sys.executable, "-m", "ruff", "format", resolved_file],
                cwd=cwd,
                capture_output=True,
                check=False,
            )
            if res.returncode == 0:
                return True
            if shutil.which("uv"):
                res = subprocess.run(
                    ["uv", "run", "ruff", "format", resolved_file],
                    cwd=cwd,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0

        elif formatter == "prettier":
            if shutil.which("prettier"):
                res = subprocess.run(
                    ["prettier", "--write", resolved_file],
                    cwd=cwd,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0
            if shutil.which("npx"):
                res = subprocess.run(
                    ["npx", "prettier", "--write", resolved_file],
                    cwd=cwd,
                    capture_output=True,
                    check=False,
                )
                return res.returncode == 0

        elif formatter == "gofmt":
            if shutil.which("gofmt"):
                res = subprocess.run(
                    ["gofmt", "-w", resolved_file], cwd=cwd, capture_output=True, check=False
                )
                return res.returncode == 0

        elif formatter == "rustfmt":
            if shutil.which("rustfmt"):
                res = subprocess.run(
                    ["rustfmt", resolved_file], cwd=cwd, capture_output=True, check=False
                )
                return res.returncode == 0

    except (OSError, subprocess.SubprocessError):
        return False

    return False
