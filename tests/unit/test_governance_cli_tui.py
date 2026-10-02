"""Testes para comandos CLI e TUI de governança e configuração de projeto (ST-019 a ST-022).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.tui.commands import COMMAND_HELP_CATALOG, handle_slash_command

runner = CliRunner()


def test_cli_project_config_and_detect(tmp_path: Path):
    # 1. Detect em pasta limpa com pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test-proj'\n", encoding="utf-8")

    result_detect = runner.invoke(app, ["project", "detect", "--project-dir", str(tmp_path)])
    assert result_detect.exit_code == 0
    assert "Stack autodetectada" in result_detect.output

    # Verifica se .bombeconfig foi gravado
    cfg_mgr = ProjectConfigManager(str(tmp_path))
    cfg = cfg_mgr.load()
    assert cfg.backend_language == "python"

    # 2. Exibe config
    result_config = runner.invoke(app, ["project", "config", "--project-dir", str(tmp_path)])
    assert result_config.exit_code == 0
    assert "Configuração do Projeto" in result_config.output
    assert "python" in result_config.output


def test_cli_mode_rca_simplify_task_report(tmp_path: Path):
    # 1. Mode
    res_mode = runner.invoke(app, ["mode", "manual", "--project-dir", str(tmp_path)])
    assert res_mode.exit_code == 0
    assert "Modo de autonomia alterado" in res_mode.output

    res_vibe = runner.invoke(app, ["mode", "vibe", "--project-dir", str(tmp_path)])
    assert res_vibe.exit_code == 0
    assert "Modo de engenharia alterado" in res_vibe.output

    # 2. RCA
    res_rca = runner.invoke(app, ["rca", "Timeout no banco", "--project-dir", str(tmp_path)])
    assert res_rca.exit_code == 0
    assert "RCA" in res_rca.output

    # 3. Simplify
    res_simp = runner.invoke(app, ["simplify", "src/foo.py", "--project-dir", str(tmp_path)])
    assert res_simp.exit_code == 0
    assert "Simplificação" in res_simp.output

    # 4. Task
    res_task = runner.invoke(app, ["task", "Revisar segurança", "--project-dir", str(tmp_path)])
    assert res_task.exit_code == 0
    assert "Task executada" in res_task.output

    # 5. Report
    res_rep = runner.invoke(app, ["report", "--project-dir", str(tmp_path)])
    assert res_rep.exit_code == 0
    assert "Relatório Consolidado" in res_rep.output


@pytest.mark.anyio
async def test_tui_governance_commands():
    # Verifica presença no catálogo
    cmd_names = [c["name"] for c in COMMAND_HELP_CATALOG]
    assert any("/project" in c for c in cmd_names)
    assert any("/mode" in c for c in cmd_names)
    assert any("/rca" in c for c in cmd_names)
    assert any("/simplify" in c for c in cmd_names)
    assert any("/task" in c for c in cmd_names)
    assert any("/report" in c for c in cmd_names)

    # Mock de app e chat
    mock_app = MagicMock()
    mock_app.project_dir = "."
    mock_chat = MagicMock()

    async def mock_mount(w):
        pass

    mock_chat.mount = mock_mount
    mock_app.query_one.return_value = mock_chat

    # Testa /mode manual
    handled = await handle_slash_command(mock_app, "/mode manual")
    assert handled is True
