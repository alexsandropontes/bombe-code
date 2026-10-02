"""Integration F5 permissions — fluxo ask/reply com persistência REAL em disco."""

import threading
from pathlib import Path

import pytest

from bombe_code.permissions.rules import PermissionService, Rule, from_saved, saved_path

pytestmark = pytest.mark.integration


def test_allow_expansao_tilde_nao_pede_permissao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange — CA1
    fake_home = tmp_path / "home"
    (fake_home / "docs").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    service = PermissionService(
        rules=[Rule(permission="read", pattern="~/docs/*", action="allow")]
    )

    # Act & Assert — imediato, sem ask
    alvo = fake_home / "docs" / "notas.md"
    alvo.write_text("ok", encoding="utf-8")
    assert service.evaluate("read", str(alvo)) == "allow"


def test_always_persiste_e_recarrega_do_disco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange — CA2
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    service = PermissionService(
        rules=[Rule(permission="bash", pattern="rm", action="ask")]
    )
    events: list[dict] = []

    # Act — responder always em paralelo (ask bloqueia até reply)
    threading.Timer(0.05, lambda: service.reply("bash", "rm", "always")).start()
    decision = service.ask("bash", "rm", emit=events.append)

    # Assert
    assert decision == "allow"
    assert events and events[0]["permission"] == "bash"
    assert service.evaluate("bash", "rm") == "allow"

    path = saved_path()
    assert path.is_file()

    recarregada = from_saved(rules=[Rule(permission="bash", pattern="rm", action="ask")])
    assert recarregada.evaluate("bash", "rm") == "allow"


def test_default_ask_e_reject_vira_deny(tmp_path: Path):
    # Arrange — CA3: perigo sem regra = aprovação humana
    service = PermissionService()
    events: list[dict] = []
    threading.Timer(0.05, lambda: service.reply("bash", "rm -rf /", "reject")).start()

    # Act
    decision = service.ask("bash", "rm -rf /", emit=events.append)

    # Assert
    assert decision == "deny"
    assert events, "devia publicar evento de permissao"
    assert service.evaluate("bash", "rm -rf /") == "ask"


def test_once_nao_persiste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    service = PermissionService()
    threading.Timer(0.05, lambda: service.reply("edit", "src/a.py", "once")).start()

    # Act & Assert
    assert service.ask("edit", "src/a.py") == "allow"
    assert not saved_path().exists() or "edit" not in _saved_text()
    assert service.evaluate("edit", "src/a.py") == "ask"


def _saved_text() -> str:
    path = saved_path()
    return path.read_text(encoding="utf-8") if path.exists() else ""
