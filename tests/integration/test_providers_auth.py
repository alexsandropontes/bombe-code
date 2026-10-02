"""Integration F2 providers-auth — auth.json em disco REAL (permissão 600)."""

from pathlib import Path

import pytest

from bombe_code.providers.auth import load_auth, save_api_key, save_oauth_token

pytestmark = pytest.mark.integration


def test_oauth_token_gravado_em_auth_json_600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    # Act
    save_oauth_token(
        "github-copilot", {"access_token": "tok-1", "refresh_token": "ref-1"}
    )

    # Assert
    auth_path = tmp_path / "bombe-code" / "auth.json"
    assert oct(auth_path.stat().st_mode & 0o777) == "0o600"
    assert load_auth()["github-copilot"]["oauth"] == {
        "access_token": "tok-1",
        "refresh_token": "ref-1",
    }


def test_auth_json_criado_com_permissao_600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    # Act
    save_api_key("anthropic", "sk-ant-teste")

    # Assert
    auth_path = tmp_path / "bombe-code" / "auth.json"
    assert auth_path.is_file()
    assert oct(auth_path.stat().st_mode & 0o777) == "0o600"
    assert load_auth()["anthropic"]["api_key"] == "sk-ant-teste"


def test_auth_json_mantem_600_apos_atualizacao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    save_api_key("anthropic", "sk-ant-1")

    # Act
    save_api_key("anthropic", "sk-ant-2")
    save_api_key("openai", "sk-oai-1")

    # Assert
    auth_path = tmp_path / "bombe-code" / "auth.json"
    assert oct(auth_path.stat().st_mode & 0o777) == "0o600"
    auth = load_auth()
    assert auth["anthropic"]["api_key"] == "sk-ant-2"
    assert auth["openai"]["api_key"] == "sk-oai-1"
    assert auth_path.stat().st_mode & 0o777 != 0o644
