"""Pydantic AI Factory — Instanciação e Execução Tipada de Agentes de IA (ST-005)."""

from __future__ import annotations

import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from bombe_code.providers.auth import load_auth


class PydanticAiFactory:
    """Fábrica central para criação de agentes tipados com Pydantic AI."""

    DEFAULT_LOCAL_URL = "http://127.0.0.1:8080/v1"
    DEFAULT_ZAI_URL = "https://api.z.ai/api/coding/paas/v4"

    def resolve_model(self, model_name: str | None) -> Any:
        """Resolve uma string de modelo para o objeto de modelo do Pydantic AI."""
        auth_data = load_auth()

        # Verifica se credenciais do Z.ai estão disponíveis
        zai_key = (
            os.environ.get("ZAI_API_KEY")
            or os.environ.get("ZHIPU_API_KEY")
            or auth_data.get("zai-coding-plan", {}).get("key")
            or auth_data.get("zai-coding-plan", {}).get("api_key")
            or auth_data.get("zai", {}).get("key")
            or auth_data.get("zai", {}).get("api_key")
        )
        zai_url = (
            os.environ.get("ZAI_BASE_URL")
            or auth_data.get("zai-coding-plan", {}).get("base_url")
            or auth_data.get("zai-coding-plan", {}).get("url")
            or auth_data.get("zai", {}).get("base_url")
            or auth_data.get("zai", {}).get("url")
            or self.DEFAULT_ZAI_URL
        )

        name = (model_name or "").strip()

        # Z.ai explícito ou modelo GLM
        if name in ("zai", "zhipu", "zai-coding-plan") or name.startswith(
            ("zai/", "zai-coding-plan/", "glm-")
        ):
            model_id = name
            if "/" in name:
                model_id = name.split("/", 1)[1]
            if model_id in ("", "zai", "zhipu", "zai-coding-plan"):
                model_id = "glm-5.3-flash"
            from openai import AsyncOpenAI
            openai_cli = AsyncOpenAI(base_url=zai_url, api_key=zai_key or "dummy", timeout=600.0, max_retries=2)
            provider = OpenAIProvider(openai_client=openai_cli)
            return OpenAIChatModel(model_id, provider=provider)

        # Se for default/vazio e tiver chave Z.ai, usa Z.ai com glm-5.3-flash como padrão
        if (not name or name in ("padrão", "default")) and zai_key:
            from openai import AsyncOpenAI
            openai_cli = AsyncOpenAI(base_url=zai_url, api_key=zai_key, timeout=600.0, max_retries=2)
            provider = OpenAIProvider(openai_client=openai_cli)
            return OpenAIChatModel("glm-5.3-flash", provider=provider)

        if not name or name in ("padrão", "default"):
            name = "llama.cpp/mimo-qwen-9b"

        # Modelos locais llama.cpp ou custom local
        if name.startswith(("llama.cpp/", "local/")):
            raw_model = name.split("/", 1)[1] if "/" in name else name
            provider = OpenAIProvider(base_url=self.DEFAULT_LOCAL_URL, api_key="dummy")
            return OpenAIChatModel(raw_model, provider=provider)

        # Provedores padrão suportados nativamente pelo Pydantic AI (ex: 'openai:gpt-4o', 'anthropic:claude-3-5-sonnet')
        if ":" in name:
            return name

        if "/" in name:
            prov, mod = name.split("/", 1)
            return f"{prov}:{mod}"

        return name

    def create_agent(
        self,
        model_name: str | None = None,
        result_type: type[Any] | None = None,
        system_prompt: str = "",
        tools: list[Any] | None = None,
    ) -> Agent:
        """Cria e retorna uma instância tipada de Agent do Pydantic AI."""
        resolved = self.resolve_model(model_name)
        res_type = result_type if result_type is not None else str

        agent = Agent(
            model=resolved,
            output_type=res_type,
            system_prompt=system_prompt,
            tools=tools or [],
        )
        return agent
