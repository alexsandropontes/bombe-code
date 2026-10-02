"""Testes unitários para a Feature 22: worktree-manager (RED phase)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from bombe_code.worktree.manager import WorktreeInfo, WorktreeManager


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True, capture_output=True)


def test_worktree_lifecycle_real_git(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    manager = WorktreeManager()

    # Listagem inicial (worktree principal)
    initial_wts = manager.list_worktrees(str(repo))
    assert len(initial_wts) >= 1
    assert isinstance(initial_wts[0], WorktreeInfo)

    # Criação de novo worktree
    wt_path = tmp_path / "wt-feature"
    created = manager.create_worktree(str(repo), str(wt_path), branch="feature-test")
    assert created.path == str(wt_path.resolve())
    assert (wt_path / "README.md").exists()

    # Listagem reflete novo worktree
    wts = manager.list_worktrees(str(repo))
    assert len(wts) == len(initial_wts) + 1

    # Remoção do worktree
    removed = manager.remove_worktree(str(repo), str(wt_path))
    assert removed is True
    assert not wt_path.exists()
