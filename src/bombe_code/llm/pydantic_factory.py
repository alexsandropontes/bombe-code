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
            import httpx
            from openai import AsyncOpenAI

            timeout_cfg = httpx.Timeout(
                timeout=240.0, connect=20.0, read=240.0, write=30.0, pool=10.0
            )
            http_cli = httpx.AsyncClient(
                timeout=timeout_cfg,
                limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=30.0),
            )
            openai_cli = AsyncOpenAI(
                base_url=zai_url, api_key=zai_key or "dummy", http_client=http_cli, max_retries=2
            )
            provider = OpenAIProvider(openai_client=openai_cli)
            return OpenAIChatModel(model_id, provider=provider)

        # Se for default/vazio, resolve o provedor na ordem de prioridade
        if not name or name in ("padrão", "default"):
            if zai_key:
                import httpx
                from openai import AsyncOpenAI

                timeout_cfg = httpx.Timeout(
                    timeout=240.0, connect=20.0, read=240.0, write=30.0, pool=10.0
                )
                http_cli = httpx.AsyncClient(
                    timeout=timeout_cfg,
                    limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=30.0),
                )
                openai_cli = AsyncOpenAI(
                    base_url=zai_url, api_key=zai_key, http_client=http_cli, max_retries=2
                )
                provider = OpenAIProvider(openai_client=openai_cli)
                return OpenAIChatModel("glm-5.3-flash", provider=provider)

            openai_key = os.environ.get("OPENAI_API_KEY") or auth_data.get("openai", {}).get(
                "api_key"
            )
            if openai_key:
                return "openai:gpt-4o"

            anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or auth_data.get(
                "anthropic", {}
            ).get("api_key")
            if anthropic_key:
                return "anthropic:claude-3-5-sonnet-20241022"

            openrouter_key = os.environ.get("OPENROUTER_API_KEY") or auth_data.get(
                "openrouter", {}
            ).get("api_key")
            if openrouter_key:
                return "openrouter:anthropic/claude-3.5-sonnet"

            groq_key = os.environ.get("GROQ_API_KEY") or auth_data.get("groq", {}).get("api_key")
            if groq_key:
                return "groq:llama-3.3-70b-versatile"

            if "LLAMA_CPP_BASE_URL" in os.environ or "llama.cpp" in auth_data:
                llama_url = os.environ.get("LLAMA_CPP_BASE_URL") or auth_data.get(
                    "llama.cpp", {}
                ).get("base_url", self.DEFAULT_LOCAL_URL)
                provider = OpenAIProvider(base_url=llama_url, api_key="dummy")
                return OpenAIChatModel("mimo-qwen-9b", provider=provider)

            if "OLLAMA_BASE_URL" in os.environ or "ollama" in auth_data:
                ollama_url = os.environ.get("OLLAMA_BASE_URL") or auth_data.get("ollama", {}).get(
                    "base_url", "http://127.0.0.1:11434/v1"
                )
                provider = OpenAIProvider(base_url=ollama_url, api_key="ollama")
                return OpenAIChatModel("llama3", provider=provider)

            raise RuntimeError(
                "⚠️ Nenhum provedor de IA configurado.\n\n"
                "Para começar a usar o Bombe Code, conecte um provedor usando:\n"
                "  • Comando /connect (ex: /connect zai <sua_chave>)\n"
                "  • Ou comando /models para selecionar um modelo\n"
                "  • Ou configure a variável ZAI_API_KEY no seu ambiente."
            )

        # Modelos locais llama.cpp ou custom local explícitos
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

        model_settings: dict[str, Any] = {}
        # Para Z.ai Coding Plan (GLM-5.3), desativa o thinking excessivo em segundo plano para evitar timeouts de dezenas de minutos
        is_zai = False
        if isinstance(resolved, OpenAIChatModel):
            if "glm" in resolved.model_name.lower():
                is_zai = True
            elif hasattr(resolved.provider, "openai_client"):
                base_u = str(getattr(resolved.provider.openai_client, "base_url", ""))
                if "z.ai" in base_u or "zhipu" in base_u:
                    is_zai = True
        elif isinstance(resolved, str) and ("zai" in resolved.lower() or "glm" in resolved.lower()):
            is_zai = True

        if is_zai:
            model_settings["extra_body"] = {"thinking": {"type": "disabled"}}

        agent = Agent(
            model=resolved,
            output_type=res_type,
            system_prompt=system_prompt,
            tools=tools or [],
            model_settings=model_settings or None,
        )
        return agent
