"""Integration F3 session-core — CRUD em storage REAL, roundtrip (CA1/CA2)."""

from pathlib import Path

import pytest

from bombe_code.session import crud
from bombe_code.session.models import Message, TextPart, ToolPart

pytestmark = pytest.mark.integration


def test_roundtrip_sessao_mensagens_parts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    # Act
    session = crud.create_session(title="sessao f3", directory=str(tmp_path))
    message = Message(session_id=session.id, role="user")
    crud.save_message(message)
    part = TextPart(message_id=message.id, text="ola mundo")
    crud.save_part(session.id, part)

    # Assert — instâncias novas lendo do disco real
    assert crud.load_session(session.id) == session
    assert crud.load_messages(session.id) == [message]
    assert crud.load_parts(session.id) == [part]


def test_tool_part_running_preservado_no_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    session = crud.create_session(title="tool", directory=str(tmp_path))
    message = Message(session_id=session.id, role="assistant")
    crud.save_message(message)
    tool = ToolPart(
        message_id=message.id,
        tool="shell",
        state="running",
        tool_call_id="call_9",
        arguments={"command": "ls"},
    )

    # Act
    crud.save_part(session.id, tool)
    loaded = crud.load_parts(session.id)

    # Assert
    assert loaded == [tool]
    assert loaded[0].state == "running"


def test_listagem_de_sessoes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    # Act
    first = crud.create_session(title="a", directory=str(tmp_path))
    second = crud.create_session(title="b", directory=str(tmp_path))

    # Assert
    sessions = crud.list_sessions()
    ids = [s.id for s in sessions]
    assert first.id in ids
    assert second.id in ids
