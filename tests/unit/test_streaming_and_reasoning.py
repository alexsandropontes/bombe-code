"""Testes para o pipeline de streaming token-a-token e raciocínio (reasoning-delta)."""

from bombe_code.providers.adapters.anthropic import parse_anthropic_sse
from bombe_code.providers.adapters.openai_compat import parse_sse
from bombe_code.session.processor import TurnProcessor
from bombe_code.tui.widgets.parts_view import PartWidget


def test_openai_compat_emits_reasoning_and_text_deltas():
    """Garante que OpenAICompatAdapter emite reasoning-delta para reasoning_content e text-delta para content."""
    lines = [
        'data: {"choices":[{"index":0,"delta":{"reasoning_content":"Pensando..."}}]}',
        'data: {"choices":[{"index":0,"delta":{"reasoning_content":" resolvi."}}]}',
        'data: {"choices":[{"index":0,"delta":{"content":"Resposta"}}]}',
        'data: {"choices":[{"index":0,"delta":{"content":" final."}}]}',
        'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
        "data: [DONE]",
    ]

    events = list(parse_sse(lines))
    assert len(events) == 5
    assert events[0] == {"type": "reasoning-delta", "text": "Pensando..."}
    assert events[1] == {"type": "reasoning-delta", "text": " resolvi."}
    assert events[2] == {"type": "text-delta", "text": "Resposta"}
    assert events[3] == {"type": "text-delta", "text": " final."}
    assert events[4] == {"type": "finish", "reason": "stop"}


def test_anthropic_emits_reasoning_and_text_deltas():
    """Garante que AnthropicAdapter emite reasoning-delta para thinking_delta e text-delta para text_delta."""
    lines = [
        'data: {"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"Cogitando..."}}',
        'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Saída"}}',
        'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"}}',
    ]

    events = list(parse_anthropic_sse(lines))
    assert len(events) == 3
    assert events[0] == {"type": "reasoning-delta", "text": "Cogitando..."}
    assert events[1] == {"type": "text-delta", "text": "Saída"}
    assert events[2] == {"type": "finish", "reason": "stop"}


def test_turn_processor_accumulates_reasoning_and_text(tmp_path, monkeypatch):
    """Garante que TurnProcessor gerencia reasoning e text separadamente."""
    from bombe_code.config.paths import BombePaths
    from bombe_code.session import crud

    # Isola o storage local da sessão no tmp_path
    mock_paths = BombePaths(
        data=tmp_path / "data",
        config=tmp_path / "config",
        state=tmp_path / "state",
        cache=tmp_path / "cache",
        log=tmp_path / "log",
        tmp=tmp_path / "tmp",
    )
    monkeypatch.setattr("bombe_code.storage.session_store.get_paths", lambda: mock_paths)

    session = crud.create_session(title="Test Reasoning", directory=str(tmp_path))
    emitted = []
    processor = TurnProcessor(session.id, on_event=lambda ev: emitted.append(ev))

    processor.add_reasoning("Etapa 1")
    processor.emit({"type": "reasoning-delta", "text": "Etapa 1"})
    processor.add_reasoning(" concluída.")
    processor.emit({"type": "reasoning-delta", "text": " concluída."})

    processor.add_text("Texto principal")
    processor.emit({"type": "text-delta", "text": "Texto principal"})

    processor.flush()

    assert processor.reasoning == "Etapa 1 concluída."
    assert processor.text == "Texto principal"
    assert len(emitted) == 3

    # Verifica se ambas as parts foram salvas no disco
    parts = crud.load_parts(session.id)
    types = [p.type for p in parts]
    assert "reasoning" in types
    assert "text" in types


def test_part_widget_streaming_and_finalization():
    """Garante que PartWidget suporta update_stream sem travar e consolida em finalize_stream."""
    widget = PartWidget({"type": "text", "text": ""})

    # Simula rajada rápida de tokens
    for token in ["Olá", " ", "Mundo", "!", " Este", " é", " um", " teste"]:
        widget.update_stream(widget.part_data["text"] + token)

    assert widget._is_streaming is True
    assert widget.part_data["text"] == "Olá Mundo! Este é um teste"

    widget.finalize_stream()
    assert widget._is_streaming is False


def test_part_widget_reasoning_streaming():
    """Garante que PartWidget renderiza reasoning com título dinâmico durante streaming."""
    widget = PartWidget({"type": "reasoning", "text": "Pensando..."})
    widget.update_stream("Pensando... analisando requisitos...")
    assert widget._is_streaming is True
    rendered = widget._get_renderable()
    # Título dinâmico de streaming ativo
    assert "tempo real" in str(rendered.title)

    widget.finalize_stream()
    assert widget._is_streaming is False
    rendered_final = widget._get_renderable()
    assert "tempo real" not in str(rendered_final.title)
