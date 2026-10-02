from __future__ import annotations

import shlex
from pathlib import Path

_OPERATORS = frozenset({"&&", "||", ";", "|"})


def scan_shell_command(command: str) -> list[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    bases: list[str] = []
    expect_command = True
    for token in tokens:
        if token in _OPERATORS:
            expect_command = True
            continue
        if expect_command:
            bases.append(token)
            expect_command = False
    return bases


def is_external(path: str, worktree: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(worktree).resolve())
    except ValueError:
        return True
    return False
