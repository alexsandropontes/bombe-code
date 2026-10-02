"""Testes unitários para comandos CLI e TUI de Starters e Snippets (ST-023 a ST-026).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.tui.commands import COMMAND_HELP_CATALOG, handle_slash_command

runner = CliRunner()


def test_cli_project_starter_list_and_apply(tmp_path: Path):
    # 1. List
    res_list = runner.invoke(app, ["project", "starter", "list"])
    assert res_list.exit_code == 0
    assert "Starters Disponíveis" in res_list.output
    assert "python-fastapi-clean" in res_list.output

    # 2. Apply
    target_dir = tmp_path / "meu_novo_app"
    res_apply = runner.invoke(
        app,
        [
            "project",
            "starter",
            "apply",
            "python-fastapi-clean",
            "--target-dir",
            str(target_dir),
            "--name",
            "meu-novo-app",
        ],
    )
    assert res_apply.exit_code == 0
    assert "aplicado com sucesso" in res_apply.output
    assert (target_dir / "pyproject.toml").is_file()


def test_cli_snippet_list_search_install(tmp_path: Path):
    # 1. List
    res_list = runner.invoke(app, ["snippet", "list"])
    assert res_list.exit_code == 0
    assert "validar-cpf" in res_list.output

    # 2. Search
    res_search = runner.invoke(app, ["snippet", "search", "cpf"])
    assert res_search.exit_code == 0
    assert "validar-cpf" in res_search.output

    # 3. Install
    dest = tmp_path / "src" / "utils"
    res_install = runner.invoke(
        app,
        ["snippet", "install", "validar-cpf", "--to", str(dest), "--platform", "python"],
    )
    assert res_install.exit_code == 0
    assert "instalado com sucesso" in res_install.output
    assert (dest / "validar_cpf.py").is_file()


@pytest.mark.anyio
async def test_tui_starter_and_snippet_commands():
    cmd_names = [c["name"] for c in COMMAND_HELP_CATALOG]
    assert any("/snippet" in c for c in cmd_names)

    mock_app = MagicMock()
    mock_app.project_dir = "."
    mock_chat = MagicMock()

    async def mock_mount(w):
        pass

    mock_chat.mount = mock_mount
    mock_app.query_one.return_value = mock_chat

    # Testa /project starter list
    handled_starter = await handle_slash_command(mock_app, "/project starter list")
    assert handled_starter is True

    # Testa /snippet list
    handled_snippet = await handle_slash_command(mock_app, "/snippet list")
    assert handled_snippet is True
