"""Unit: modelos de sessão (F3 RN1)."""

import pytest
from pydantic import ValidationError

from bombe_code.session.models import Message, Session, TextPart, ToolPart


def test_session_id_tem_prefixo_ses():
    session = Session(title="t", directory="/tmp")
    assert session.id.startswith("ses_")
    assert session.agent is None
    assert session.tokens == 0
    assert session.cost == 0.0


def test_message_id_tem_prefixo_msg():
    message = Message(session_id="ses_x", role="user")
    assert message.id.startswith("msg_")


def test_tool_part_estados_validos():
    for state in ("pending", "running", "completed", "error"):
        part = ToolPart(message_id="msg_x", tool="shell", state=state)
        assert part.state == state
        assert part.id.startswith("prt_")


def test_tool_part_estado_invalido_rejeitado():
    with pytest.raises(ValidationError):
        ToolPart(message_id="msg_x", tool="shell", state="queued")


def test_text_part_roundtrip_dict():
    part = TextPart(message_id="msg_x", text="ola")
    clone = TextPart.model_validate(part.model_dump())
    assert clone == part
