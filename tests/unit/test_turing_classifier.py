"""Testes unitários para o TuringIntentClassifier (ST-001)."""

from __future__ import annotations

from bombe_code.turing.classifier import TuringIntentClassifier, TuringIntentResult


def test_classify_wave_status():
    classifier = TuringIntentClassifier()
    result = classifier.classify("qual o status da onda atual?")
    assert isinstance(result, TuringIntentResult)
    assert result.intention == "wave_status"
    assert result.confidence >= 0.8
    assert not result.needs_llm


def test_classify_start_discuss():
    classifier = TuringIntentClassifier()
    result = classifier.classify("iniciar fase discuss do projeto")
    assert result.intention == "start_discuss"
    assert result.confidence >= 0.8
    assert not result.needs_llm


def test_classify_start_plan():
    classifier = TuringIntentClassifier()
    result = classifier.classify("vamos planejar a arquitetura e backlog")
    assert result.intention == "start_plan"
    assert not result.needs_llm


def test_classify_start_cycle_with_slot():
    classifier = TuringIntentClassifier()
    result = classifier.classify("executar ciclo da story ST-002")
    assert result.intention == "start_cycle"
    assert result.slots.get("story_id") == "ST-002"
    assert not result.needs_llm


def test_classify_review_cycle():
    classifier = TuringIntentClassifier()
    result = classifier.classify("solicitar code review do tech lead")
    assert result.intention == "review_cycle"
    assert not result.needs_llm


def test_classify_validate_wave():
    classifier = TuringIntentClassifier()
    result = classifier.classify("validar entrega da onda e auditar contrato")
    assert result.intention == "validate_wave"
    assert not result.needs_llm


def test_classify_toggle_mode():
    classifier = TuringIntentClassifier()
    result = classifier.classify("mudar para modo auto")
    assert result.intention == "toggle_mode"
    assert result.slots.get("mode") == "auto"
    assert not result.needs_llm


def test_classify_unknown_triggers_needs_llm():
    classifier = TuringIntentClassifier()
    result = classifier.classify("como calcular a velocidade da luz em Marte?")
    assert result.needs_llm is True
    assert result.confidence < 0.5
