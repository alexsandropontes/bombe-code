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
