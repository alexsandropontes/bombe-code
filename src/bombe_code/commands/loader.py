"""Carregador de templates de comandos customizados."""

from __future__ import annotations

import os
from pathlib import Path

from .templates import CustomCommand


def load_custom_commands(project_dir: str | Path) -> dict[str, CustomCommand]:
    """Carrega comandos customizados em .bombe/commands/ e .opencode/commands/."""
    base = Path(project_dir).resolve()
    commands: dict[str, CustomCommand] = {}

    search_dirs = [
        base / ".bombe" / "commands",
        base / ".opencode" / "commands",
        base / "commands",
    ]

    for s_dir in search_dirs:
        if not s_dir.exists() or not s_dir.is_dir():
            continue
        for root, _, files in os.walk(s_dir):
            for f in files:
                if f.endswith(".md"):
                    cmd_path = Path(root) / f
                    try:
                        cmd = CustomCommand.from_file(cmd_path)
                        commands[cmd.name.lower()] = cmd
                    except (OSError, ValueError):
                        continue

    return commands
