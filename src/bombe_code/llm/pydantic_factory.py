"""Pydantic AI Factory — Instanciação e Execução Tipada de Agentes de IA (ST-005)."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class PydanticAiFactory:
    """Fábrica central para criação de agentes tipados com Pydantic AI."""

    DEFAULT_LOCAL_URL = "http://127.0.0.1:8080/v1"

    def resolve_model(self, model_name: str | None) -> Any:
        """Resolve uma string de modelo para o objeto de modelo do Pydantic AI."""
        if not model_name or model_name in ("padrão", "default"):
            model_name = "llama.cpp/mimo-qwen-9b"

        # Modelos locais llama.cpp ou custom local
        if model_name.startswith(("llama.cpp/", "local/")):
            raw_model = model_name.split("/", 1)[1] if "/" in model_name else model_name
            provider = OpenAIProvider(base_url=self.DEFAULT_LOCAL_URL, api_key="dummy")
            return OpenAIChatModel(raw_model, provider=provider)

        # Provedores padrão suportados nativamente pelo Pydantic AI (ex: 'openai:gpt-4o', 'anthropic:claude-3-5-sonnet')
        if ":" in model_name:
            return model_name

        if "/" in model_name:
            prov, mod = model_name.split("/", 1)
            return f"{prov}:{mod}"

        return model_name

    def create_agent(
        self,
        model_name: str | None = None,
        result_type: type[Any] | None = None,
        system_prompt: str = "",
    ) -> Agent:
        """Cria e retorna uma instância tipada de Agent do Pydantic AI."""
        resolved = self.resolve_model(model_name)
        res_type = result_type if result_type is not None else str

        agent = Agent(
            model=resolved,
            output_type=res_type,
            system_prompt=system_prompt,
        )
        return agent
