"""Testes unitários para o Turing Prompt Assembler (Lego de Prompts).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from __future__ import annotations

from bombe_code.turing.prompt_assembler import (
    DeliveryTarget,
    TuringPromptAssembler,
)


def test_delivery_target_enum_values():
    assert DeliveryTarget.SNIPPET.value == "snippet"
    assert DeliveryTarget.PROTOTYPE.value == "prototype"
    assert DeliveryTarget.POC.value == "poc"
    assert DeliveryTarget.MVP.value == "mvp"
    assert DeliveryTarget.PRODUCTION.value == "production"
    assert DeliveryTarget.ENTERPRISE.value == "enterprise"


def test_vibe_code_mode_returns_unrestricted_prompt():
    assembler = TuringPromptAssembler()
    prompt = assembler.assemble(
        agent_handle="@valim",
        task_instruction="Escreva um componente de quiz",
        delivery_target=DeliveryTarget.MVP,
        mode="vibe-code",
    )
    # No vibe-code o prompt é leve e direto, sem as amarras rígidas de profundidade
    assert "Escreva um componente de quiz" in prompt
    assert "ANTI-SCOPE CREEP" not in prompt


def test_tdd_code_mode_mvp_includes_operational_mvp_and_anti_scope_creep():
    assembler = TuringPromptAssembler()
    prompt = assembler.assemble(
        agent_handle="@grace",
        task_instruction="Elabore o PRD para o formulário de onboarding",
        delivery_target=DeliveryTarget.MVP,
        mode="tdd-code",
    )
    # Modo TDD com MVP Operacional
    assert "ANTI-SCOPE CREEP / YAGNI RADICAL" in prompt
    assert "TETO MÁXIMO DA DEMANDA" in prompt
    assert "MVP OPERACIONAL" in prompt
    assert (
        "versão mínima funcional capaz de ser utilizada por usuários externos reais"
        in prompt.lower()
    )
    assert "funcionalidades essenciais não podem ser simuladas por mocks" in prompt.lower()
    assert (
        "The system MUST NOT assume MVP, production or enterprise requirements unless explicitly required"
        in prompt
    )
    assert "Elabore o PRD para o formulário de onboarding" in prompt


def test_tdd_code_mode_poc_allows_hypothesis_mocks():
    assembler = TuringPromptAssembler()
    prompt = assembler.assemble(
        agent_handle="@ieru",
        task_instruction="Projete a arquitetura para validar a conexão com API X",
        delivery_target=DeliveryTarget.POC,
        mode="tdd-code",
    )
    assert "DELIVERY TARGET: POC" in prompt
    assert "Mocks são permitidos onde não invalidarem a hipótese" in prompt
    assert "Hardening de produção não é necessário" in prompt


def test_tdd_code_mode_snippet_restricts_to_isolated_function():
    assembler = TuringPromptAssembler()
    prompt = assembler.assemble(
        agent_handle="@valim",
        task_instruction="Implemente uma função de ordenação rápida",
        delivery_target=DeliveryTarget.SNIPPET,
        mode="tdd-code",
    )
    assert "DELIVERY TARGET: SNIPPET" in prompt
    assert "Zero infraestrutura, zero persistência" in prompt


def test_prompt_assembler_from_string_target():
    assembler = TuringPromptAssembler()
    prompt = assembler.assemble(
        agent_handle="@alan",
        task_instruction="Mapeie as telas",
        delivery_target="production",
        mode="tdd-code",
    )
    assert "DELIVERY TARGET: PRODUCTION" in prompt
