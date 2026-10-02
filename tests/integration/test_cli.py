from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app

pytestmark = pytest.mark.integration
runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "bombe-code" in result.stdout


def test_cli_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "Catálogo de Modelos" in result.stdout or "openai" in result.stdout.lower()


def test_cli_run_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    # Test run subcommand
    result = runner.invoke(app, ["run", "Diga olá mundo", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert len(result.stdout.strip()) > 0


def test_cli_serve_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    from bombe_code.cli.main import start_server_in_process

    server_thread, port, password = start_server_in_process(port=0, project_dir=str(tmp_path))
    try:
        url = f"http://127.0.0.1:{port}/api/health"
        resp = httpx.get(url, auth=("bombe", password), timeout=5.0)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    finally:
        server_thread.stop()
