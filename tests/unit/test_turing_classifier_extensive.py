"""Testes unitários para o classificador com vocabulário extenso e briefings markdown."""

from __future__ import annotations

from bombe_code.turing.classifier import TuringIntentClassifier, TuringIntentResult


def test_classify_markdown_briefing_drops_mvp():
    classifier = TuringIntentClassifier()
    briefing_text = """# BRIEFING — DROPS MVP

## 1. Visão do produto

**Drops** é um aplicativo de microconteúdo diário voltado a **bem-estar (wellness), leveza, inspiração e desenvolvimento pessoal**.

> **Uma pequena dose de conteúdo para melhorar o seu momento e depois seguir a vida.**

O Drops **não** deve maximizar tempo de tela, retenção ou consumo infinito. A experiência deve ser **curta, finita, leve e prazerosa**.

O usuário entra, recebe sua dose, consome e sai. **Não criar feed infinito.**

### Frase de posicionamento

> **Drops não é um aplicativo para fazer o usuário ficar. É um aplicativo para fazer o usuário começar melhor e ir viver.**

---

## 2. Conceito central

Conteúdo organizado por **temas**. Os 20 temas iniciais:
1. Motivação
2. Superação
3. Autoconhecimento

---

## 3. Regra de ouro

### UMA DOSE POR MOMENTO.

Parte da identidade do produto. O usuário **não** pode solicitar mais Drops.

---

## 4. Escopo do MVP

### Objetivos de validação
1. Validar se as pessoas gostam do conceito.
2. Validar se retornam diariamente.

### Funcionalidades (IN)
F1: Cadastro/login
F2: Seleção de temas
F3: Definição de ordem/preferência
F4: Um Drop diário por tema selecionado
"""
    result = classifier.classify(briefing_text, stage="DISCUSS", is_greenfield=True)
    assert isinstance(result, TuringIntentResult)
    assert result.intention == "start_discuss"
    assert result.confidence >= 0.90
    assert not result.needs_llm
    assert "DROPS MVP" in result.slots.get("topic", "") or "Drops" in result.slots.get("topic", "")


def test_classify_workflow_resume_variations():
    classifier = TuringIntentClassifier()
    for phrase in [
        "continue de onde parou",
        "retome de onde parou",
        "continua da onde parou",
        "retoma o fluxo",
        "deu erro e parou no meio",
        "segue dai com o workflow",
    ]:
        res = classifier.classify(phrase)
        assert res.intention == "workflow_resume", f"Falhou para: {phrase}"
        assert not res.needs_llm


def test_classify_approve_execution_variations():
    classifier = TuringIntentClassifier()
    for phrase in [
        "pode executar",
        "pronto pode executar sim",
        "aprovado execute o plano",
        "está liberado, começa a execução",
        "plano aprovado",
    ]:
        res = classifier.classify(phrase)
        assert res.intention == "approve_execution", f"Falhou para: {phrase}"
        assert not res.needs_llm


def test_classify_natural_project_creation():
    classifier = TuringIntentClassifier()
    res = classifier.classify(
        "quero criar um app de onboarding com quiz financeiro e validação de leads"
    )
    assert res.intention == "start_discuss"
    assert not res.needs_llm
    assert (
        "onboarding" in res.slots.get("topic", "").lower()
        or "quiz" in res.slots.get("topic", "").lower()
    )


def test_classify_stage_context_in_discuss():
    classifier = TuringIntentClassifier()
    res = classifier.classify(
        "Sistema de gestão para barbearias com agendamento online e pagamentos",
        stage="DISCUSS",
        is_greenfield=True,
    )
    assert res.intention == "start_discuss"
    assert not res.needs_llm


def test_classify_ambiguous_question_flags_needs_llm():
    classifier = TuringIntentClassifier()
    res = classifier.classify("Qual é a capital da Islândia?")
    assert res.needs_llm is True
    assert res.confidence < 0.60
