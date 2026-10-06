"""Testes unitários para a PydanticAiFactory (ST-005)."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from bombe_code.llm.pydantic_factory import PydanticAiFactory


class ReviewOutput(BaseModel):
    approved: bool
    summary: str
    issues: list[str]


def test_create_agent_with_custom_model_and_result_type():
    factory = PydanticAiFactory()
    agent = factory.create_agent(
        model_name="test",
        result_type=ReviewOutput,
        system_prompt="Você é o Tech Lead avaliador de código.",
    )

    assert isinstance(agent, Agent)
    assert agent.output_type == ReviewOutput


def test_resolve_local_llama_model():
    factory = PydanticAiFactory()
    model_instance = factory.resolve_model("llama.cpp/mimo-qwen-9b")
    # Para modelos locais llama.cpp, deve resolver para OpenAIChatModel apontando para base_url local
    assert model_instance is not None


def test_create_agent_defaults_to_string_result():
    factory = PydanticAiFactory()
    agent = factory.create_agent(model_name="test")
    assert isinstance(agent, Agent)
    assert agent.output_type is str


def test_create_agent_injects_thinking_disabled_for_zai_glm():
    factory = PydanticAiFactory()
    agent = factory.create_agent(model_name="glm-5.3-flash")
    assert isinstance(agent, Agent)
    assert agent.model_settings is not None
    assert agent.model_settings.get("extra_body", {}).get("thinking") == {"type": "disabled"}


def test_resolve_zai_model_uses_fail_fast_timeout():
    factory = PydanticAiFactory()
    model = factory.resolve_model("zai-coding-plan/glm-5.3-flash")
    cli = getattr(model.provider, "client", None)
    assert cli is not None
    assert getattr(cli.timeout, "read", None) == 240.0
    assert getattr(cli.timeout, "connect", None) == 20.0
    assert cli.max_retries == 2


def test_resolve_model_raises_when_no_provider_configured(monkeypatch):
    import pytest

    # Mock sem credenciais e sem env
    monkeypatch.setattr("bombe_code.llm.pydantic_factory.load_auth", dict)
    for k in (
        "ZAI_API_KEY",
        "ZHIPU_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "LLAMA_CPP_BASE_URL",
        "OLLAMA_BASE_URL",
    ):
        monkeypatch.delenv(k, raising=False)

    factory = PydanticAiFactory()
    with pytest.raises(RuntimeError) as exc_info:
        factory.resolve_model(None)

    assert "Nenhum provedor de IA configurado" in str(exc_info.value)
    assert "/connect" in str(exc_info.value)
