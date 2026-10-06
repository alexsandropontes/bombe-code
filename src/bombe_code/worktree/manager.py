"""Gerenciador de Git Worktrees para execução e branches isoladas."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel


class WorktreeInfo(BaseModel):
    """Informações de um worktree Git ativo."""

    path: str
    commit: str = ""
    branch: str = ""


class WorktreeManager:
    """Orquestrador de operações de Git Worktree."""

    def list_worktrees(self, repo_dir: str | Path) -> list[WorktreeInfo]:
        """Lista todos os worktrees do repositório via git worktree list --porcelain."""
        res = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return []

        worktrees: list[WorktreeInfo] = []
        curr_path = ""
        curr_commit = ""
        curr_branch = ""

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                if curr_path:
                    worktrees.append(
                        WorktreeInfo(
                            path=curr_path,
                            commit=curr_commit,
                            branch=curr_branch,
                        )
                    )
                    curr_path = ""
                    curr_commit = ""
                    curr_branch = ""
                continue

            if line.startswith("worktree "):
                curr_path = str(Path(line[9:].strip()).resolve())
            elif line.startswith("HEAD "):
                curr_commit = line[5:].strip()
            elif line.startswith("branch "):
                curr_branch = line[7:].strip().replace("refs/heads/", "")

        if curr_path:
            worktrees.append(
                WorktreeInfo(
                    path=curr_path,
                    commit=curr_commit,
                    branch=curr_branch,
                )
            )

        return worktrees

    def create_worktree(
        self,
        repo_dir: str | Path,
        worktree_path: str | Path,
        branch: str,
    ) -> WorktreeInfo:
        """Cria um novo worktree apontando para o branch especificado."""
        target_path = Path(worktree_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Tenta criar com nova branch (-b) ou branch existente
        cmd = ["git", "worktree", "add", "-b", branch, str(target_path)]
        res = subprocess.run(
            cmd,
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            # Se a branch já existir, cria sem -b
            res = subprocess.run(
                ["git", "worktree", "add", str(target_path), branch],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                raise RuntimeError(f"Falha ao criar worktree: {res.stderr.strip()}")

        return WorktreeInfo(
            path=str(target_path),
            branch=branch,
        )

    def remove_worktree(
        self,
        repo_dir: str | Path,
        worktree_path: str | Path,
        force: bool = True,
    ) -> bool:
        """Remove um worktree existente e limpa seu diretório."""
        target_path = Path(worktree_path).resolve()
        cmd = ["git", "worktree", "remove", str(target_path)]
        if force:
            cmd.insert(3, "--force")

        res = subprocess.run(
            cmd,
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode == 0
