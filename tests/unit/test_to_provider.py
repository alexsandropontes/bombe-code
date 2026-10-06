"""Unit: mapeamento histórico → mensagens de provedor (F3 RN4 / CA3)."""

from bombe_code.session.models import Message, TextPart, ToolPart
from bombe_code.session.to_provider import to_provider_messages


def _history():
    user = Message(session_id="ses_1", role="user")
    assistant = Message(session_id="ses_1", role="assistant")
    return [
        (user, [TextPart(message_id=user.id, text="faz um endpoint")]),
        (assistant, [TextPart(message_id=assistant.id, text="pronto")]),
    ]


def test_openai_formato_roles_e_content_string():
    result = to_provider_messages(_history(), provider="openai")
    assert [m["role"] for m in result] == ["user", "assistant"]
    assert result[0]["content"] == "faz um endpoint"
    assert result[1]["content"] == "pronto"


def test_anthropic_formato_content_blocos():
    result = to_provider_messages(_history(), provider="anthropic")
    assert [m["role"] for m in result] == ["user", "assistant"]
    assert result[0]["content"] == [{"type": "text", "text": "faz um endpoint"}]
    assert result[1]["content"] == [{"type": "text", "text": "pronto"}]


def test_system_message_vira_role_system_no_openai():
    system = Message(session_id="ses_1", role="system")
    history = [(system, [TextPart(message_id=system.id, text="resumo compactado")])]
    result = to_provider_messages(history, provider="openai")
    assert result == [{"role": "system", "content": "resumo compactado"}]


def test_openai_tool_completed_vira_mensagem_tool():
    user = Message(session_id="ses_1", role="user")
    assistant = Message(session_id="ses_1", role="assistant")
    history = [
        (user, [TextPart(message_id=user.id, text="leia o arquivo")]),
        (
            assistant,
            [
                ToolPart(
                    message_id=assistant.id,
                    tool="read",
                    state="completed",
                    tool_call_id="call_1",
                    arguments={"path": "a.py"},
                    output="conteudo",
                )
            ],
        ),
    ]
    result = to_provider_messages(history, provider="openai")
    tool_msgs = [m for m in result if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["tool_call_id"] == "call_1"
    assert tool_msgs[0]["content"] == "conteudo"
