"""Testes unitários para o ConsumerHandoffGate do Turing Runtime."""

from __future__ import annotations

from bombe_code.turing.handoff_gate import ConsumerHandoffGate, HandoffStatus


def test_handoff_gate_accepts_dense_input_with_required_topics():
    gate = ConsumerHandoffGate()
    content = """
    # Arquitetura do Sistema
    Definimos a stack tecnológica como FastAPI e PostgreSQL.
    O banco terá tabelas relacionais com chaves estrangeiras e índices.
    A comunicação será via REST API com autenticação por token.
    """
    evaluation = gate.evaluate_input(
        consumer_persona="@codd",
        producer_persona="@ieru",
        artifact_path="docs/architecture/SYSTEM_ARCHITECTURE.md",
        content=content,
        required_topics=["banco", "postgresql"],
        min_substantive_words=10,
    )
    assert evaluation.status == HandoffStatus.ACCEPTED
    assert len(evaluation.required_improvements) == 0


def test_handoff_gate_blocks_shallow_content():
    gate = ConsumerHandoffGate()
    shallow_content = "# Doc\nFazer tudo."
    evaluation = gate.evaluate_input(
        consumer_persona="@codd",
        producer_persona="@ieru",
        artifact_path="docs/architecture/SYSTEM_ARCHITECTURE.md",
        content=shallow_content,
        min_substantive_words=15,
    )
    assert evaluation.status == HandoffStatus.BLOCKED
    assert any("Densidade de conteúdo insuficiente" in imp for imp in evaluation.required_improvements)


def test_handoff_gate_blocks_missing_topics_and_builds_rework_prompt():
    gate = ConsumerHandoffGate()
    content = """
    # Mapeamento do Sistema
    Texto com muitas palavras estruturadas para passar na densidade exigida.
    Mais palavras adicionais para garantir que o numero total de termos seja bem grande e suficiente.
    """
    evaluation = gate.evaluate_input(
        consumer_persona="@barbara",
        producer_persona="@ieru",
        artifact_path="docs/architecture/SYSTEM_ARCHITECTURE.md",
        content=content,
        required_topics=["autenticação", "banco"],
        min_substantive_words=10,
    )
    assert evaluation.status == HandoffStatus.BLOCKED
    assert any("autenticação" in imp for imp in evaluation.required_improvements)

    prompt = gate.build_rework_prompt(evaluation, original_demand="Criar arquitetura completa")
    assert "@ieru" in prompt
    assert "@barbara" in prompt
    assert "MELHORIAS OBRIGATÓRIAS" in prompt
    assert "docs/architecture/SYSTEM_ARCHITECTURE.md" in prompt
