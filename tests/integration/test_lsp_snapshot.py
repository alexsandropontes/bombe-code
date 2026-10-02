"""Integration tests for F12 lsp-snapshot."""

import subprocess
from pathlib import Path

import pytest

from bombe_code.lsp.diagnostics import DiagnosticsManager
from bombe_code.snapshot.manager import SnapshotManager

pytestmark = pytest.mark.integration


def test_snapshot_create_diff_and_revert(tmp_path: Path):
    # Inicializa repo git temporário
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True
    )

    test_file = tmp_path / "hello.txt"
    test_file.write_text("v1 inicial\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True)

    mgr = SnapshotManager(repo_dir=str(tmp_path))
    snap1 = mgr.create_snapshot("step-1")
    assert snap1 is not None

    # Modifica arquivo
    test_file.write_text("v2 modificado\n", encoding="utf-8")
    diff = mgr.get_diff("step-1")
    assert "+v2 modificado" in diff

    # Reverte
    success = mgr.revert("step-1")
    assert success is True
    assert test_file.read_text(encoding="utf-8") == "v1 inicial\n"


def test_lsp_diagnostics_syntax_check(tmp_path: Path):
    diag_mgr = DiagnosticsManager()
    py_file = tmp_path / "invalid.py"
    py_file.write_text("def broken_func(: pass\n", encoding="utf-8")

    diags = diag_mgr.get_diagnostics(str(py_file))
    assert len(diags) > 0
    assert any("syntax" in d.message.lower() or "invalid" in d.message.lower() for d in diags)

    injected = diag_mgr.inject_into_output("Arquivo editado com sucesso.", str(py_file))
    assert "Diagnostics:" in injected
