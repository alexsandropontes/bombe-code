"""Testes unitários para o módulo de upgrade e comando CLI do Bombe Code."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.cli.updater import (
    detect_remote_default_branch,
    get_remote_ref_sha,
    get_uv_executable,
    run_upgrade,
)

runner = CliRunner()


def test_get_uv_executable():
    with patch("shutil.which", return_value="/usr/local/bin/uv"):
        assert get_uv_executable() == "/usr/local/bin/uv"

    with patch("shutil.which", return_value=None), patch("pathlib.Path.is_file", return_value=False):
        # Fallback to None if not found
        assert get_uv_executable() is None


def test_detect_remote_default_branch():
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "ref: refs/heads/dev-working-ia\tHEAD\n0699cc HEAD\n"

    with patch("subprocess.run", return_value=mock_proc):
        branch = detect_remote_default_branch("https://github.com/alexsandropontes/bombe-code.git")
        assert branch == "dev-working-ia"

    # Fallback on failure
    mock_fail = MagicMock()
    mock_fail.returncode = 1
    with patch("subprocess.run", return_value=mock_fail):
        branch = detect_remote_default_branch("https://github.com/alexsandropontes/bombe-code.git")
        assert branch == "main"


def test_get_remote_ref_sha():
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "0699cc5a555fd8c930fe6565c96c73bafe8adbfa\trefs/heads/dev-working-ia\n"

    with patch("subprocess.run", return_value=mock_proc):
        sha = get_remote_ref_sha(
            "https://github.com/alexsandropontes/bombe-code.git", "refs/heads/dev-working-ia"
        )
        assert sha == "0699cc5a555fd8c930fe6565c96c73bafe8adbfa"


def test_run_upgrade_uv_missing():
    with patch("bombe_code.cli.updater.get_uv_executable", return_value=None):
        res = run_upgrade()
        assert res["success"] is False
        assert "uv não encontrado" in res["error"]


def test_run_upgrade_check_only():
    with patch("bombe_code.cli.updater.get_uv_executable", return_value="/bin/uv"), \
         patch("bombe_code.cli.updater.detect_remote_default_branch", return_value="main"), \
         patch("bombe_code.cli.updater.get_remote_ref_sha", return_value="abcdef123456"):

        res = run_upgrade(check_only=True)
        assert res["success"] is True
        assert res["check_only"] is True
        assert res["target_ref"] == "main"
        assert res["remote_sha"] == "abcdef123456"


def test_run_upgrade_with_tag_and_branch():
    mock_install = MagicMock()
    mock_install.returncode = 0
    mock_install.stdout = "Installed 2 executables"

    with patch("bombe_code.cli.updater.get_uv_executable", return_value="/bin/uv"), \
         patch("subprocess.run", return_value=mock_install):

        # Tag
        res_tag = run_upgrade(tag="v0.1.2")
        assert res_tag["success"] is True
        assert res_tag["target_ref"] == "v0.1.2"

        # Branch
        res_branch = run_upgrade(branch="dev")
        assert res_branch["success"] is True
        assert res_branch["target_ref"] == "dev"


def test_cli_upgrade_command_check():
    with patch("bombe_code.cli.updater.get_uv_executable", return_value="/bin/uv"), \
         patch("bombe_code.cli.updater.detect_remote_default_branch", return_value="main"), \
         patch("bombe_code.cli.updater.get_remote_ref_sha", return_value="1234567890"):

        result = runner.invoke(app, ["upgrade", "--check"])
        assert result.exit_code == 0
        assert "Verificando atualizações" in result.output
        assert "Versão instalada:" in result.output
