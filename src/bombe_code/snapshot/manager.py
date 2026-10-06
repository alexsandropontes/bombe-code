"""Gerenciador de snapshots baseado em git para rollback e diffs por step."""

from __future__ import annotations

import subprocess
from pathlib import Path


class SnapshotManager:
    """Gerencia snapshots e patches no repositório de trabalho via git."""

    def __init__(self, repo_dir: str | Path = ".") -> None:
        self.repo_dir = str(repo_dir)
        self._snapshots: dict[str, str] = {}

    def _run_git(self, args: list[str]) -> str:
        res = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip()

    def create_snapshot(self, step_id: str) -> str:
        """Registra o estado atual da árvore de trabalho."""
        # Se houver mudanças não commitadas, cria um stash ou lê commit atual
        commit = self._run_git(["rev-parse", "HEAD"])
        if not commit:
            commit = "HEAD"
        self._snapshots[step_id] = commit
        return commit

    def get_diff(self, step_id: str) -> str:
        """Retorna o diff entre o snapshot e o estado atual."""
        commit = self._snapshots.get(step_id, "HEAD")
        diff = self._run_git(["diff", commit])
        if not diff:
            diff = self._run_git(["diff"])
        return diff

    def revert(self, step_id: str) -> bool:
        """Restaura o estado do repositório para o snapshot."""
        commit = self._snapshots.get(step_id)
        if not commit:
            return False
        # Limpa modificações na árvore de trabalho
        self._run_git(["checkout", commit, "--", "."])
        self._run_git(["clean", "-fd"])
        return True
