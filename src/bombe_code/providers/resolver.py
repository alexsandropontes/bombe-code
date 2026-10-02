"""Resolvedor enterprise de provedores e modelos LLM para o Bombe Code (paridade com OpenCode)."""

from __future__ import annotations

import logging
import os
from typing import Any

from .adapters.anthropic import AnthropicAdapter
from .adapters.openai_compat import OpenAICompatAdapter
from .auth import load_auth

logger = logging.getLogger(__name__)


class ProviderConfigurationError(RuntimeError):
    """Lançada quando nenhum provedor de IA compatível está configurado."""


class UnconfiguredProviderAdapter:
    """Adaptador de alerta em runtime quando nenhuma credencial ou servidor local foi configurado."""

    provider = "unconfigured"
    model = "none"

    def __init__(self, message: str) -> None:
        self.message = message

    def stream(
        self, messages: list[dict], tools: list[dict] | None = None, system: str | None = None
    ) -> Any:
        msg = (
            f"⚠️ Provedor não configurado.\n\n{self.message}\n\n"
            "Execute o comando /connect no chat para configurar suas credenciais ou endereço local."
        )
        yield {"type": "text-delta", "text": msg}
        yield {"type": "finish", "reason": "stop"}


def resolve_provider_adapter(model_ref: str | None = None) -> Any:
    """Resolve o adaptador de IA apropriado consultando auth.json, variáveis de ambiente e configurações explícitas."""
    auth_data = load_auth()
    ref = (model_ref or "").strip()

    # 1. Requisição explícita por provedor/modelo
    if ref:
        provider, _, model_name = ref.partition("/")
        if not model_name:
            model_name = provider
            provider = ""

        # OpenAI
        if provider == "openai" or model_name.startswith("gpt-"):
            key = os.environ.get("OPENAI_API_KEY") or auth_data.get("openai", {}).get("api_key")
            if not key:
                raise ProviderConfigurationError(
                    "Chave OPENAI_API_KEY não encontrada no ambiente ou auth.json."
                )
            return OpenAICompatAdapter(api_key=key, model=model_name or "gpt-4o")

        # Anthropic
        if provider == "anthropic" or model_name.startswith("claude-"):
            key = os.environ.get("ANTHROPIC_API_KEY") or auth_data.get("anthropic", {}).get(
                "api_key"
            )
            if not key:
                raise ProviderConfigurationError(
                    "Chave ANTHROPIC_API_KEY não encontrada no ambiente ou auth.json."
                )
            return AnthropicAdapter(api_key=key, model=model_name or "claude-3-5-sonnet-20241022")

        # OpenRouter
        if provider == "openrouter":
            key = os.environ.get("OPENROUTER_API_KEY") or auth_data.get("openrouter", {}).get(
                "api_key"
            )
            if not key:
                raise ProviderConfigurationError(
                    "Chave OPENROUTER_API_KEY não encontrada no ambiente ou auth.json."
                )
            return OpenAICompatAdapter(
                api_key=key, model=model_name, base_url="https://openrouter.ai/api/v1"
            )

        # Groq
        if provider == "groq":
            key = os.environ.get("GROQ_API_KEY") or auth_data.get("groq", {}).get("api_key")
            if not key:
                raise ProviderConfigurationError(
                    "Chave GROQ_API_KEY não encontrada no ambiente ou auth.json."
                )
            return OpenAICompatAdapter(
                api_key=key,
                model=model_name or "llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
            )

        # llama.cpp explícito
        if provider in ("llama.cpp", "llamacpp", "local"):
            base_url = (
                os.environ.get("LLAMA_CPP_BASE_URL")
                or auth_data.get("llama.cpp", {}).get("base_url")
                or "http://127.0.0.1:8080/v1"
            )
            return OpenAICompatAdapter(
                api_key="local", model=model_name or "local", base_url=base_url
            )

        # Ollama explícito
        if provider == "ollama":
            base_url = (
                os.environ.get("OLLAMA_BASE_URL")
                or auth_data.get("ollama", {}).get("base_url")
                or "http://127.0.0.1:11434/v1"
            )
            return OpenAICompatAdapter(
                api_key="ollama", model=model_name or "llama3", base_url=base_url
            )

    # 2. Resolução sem modelo explícito (apenas provedores configurados explicitamente)
    # A) llama.cpp explicitamente configurado no ambiente ou auth.json
    if "LLAMA_CPP_BASE_URL" in os.environ or "llama.cpp" in auth_data:
        llama_url = os.environ.get("LLAMA_CPP_BASE_URL") or auth_data.get("llama.cpp", {}).get(
            "base_url", "http://127.0.0.1:8080/v1"
        )
        return OpenAICompatAdapter(api_key="local", model="local", base_url=llama_url)

    # B) Ollama explicitamente configurado no ambiente ou auth.json
    if "OLLAMA_BASE_URL" in os.environ or "ollama" in auth_data:
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or auth_data.get("ollama", {}).get(
            "base_url", "http://127.0.0.1:11434/v1"
        )
        return OpenAICompatAdapter(api_key="ollama", model="llama3", base_url=ollama_url)

    # C) Chaves remotas no ambiente ou auth.json
    openai_key = os.environ.get("OPENAI_API_KEY") or auth_data.get("openai", {}).get("api_key")
    if openai_key:
        return OpenAICompatAdapter(api_key=openai_key, model="gpt-4o")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or auth_data.get("anthropic", {}).get(
        "api_key"
    )
    if anthropic_key:
        return AnthropicAdapter(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")

    openrouter_key = os.environ.get("OPENROUTER_API_KEY") or auth_data.get("openrouter", {}).get(
        "api_key"
    )
    if openrouter_key:
        return OpenAICompatAdapter(
            api_key=openrouter_key,
            model="anthropic/claude-3.5-sonnet",
            base_url="https://openrouter.ai/api/v1",
        )

    groq_key = os.environ.get("GROQ_API_KEY") or auth_data.get("groq", {}).get("api_key")
    if groq_key:
        return OpenAICompatAdapter(
            api_key=groq_key,
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        )

    # D) Se nenhum provedor configurado
    instructions = (
        "Nenhum provedor de IA configurado.\n"
        "Execute /connect no terminal para conectar um provedor:\n"
        "  • Remoto: export OPENAI_API_KEY='sk-...' ou export ANTHROPIC_API_KEY='...'\n"
        "  • Local (llama.cpp): export LLAMA_CPP_BASE_URL='http://127.0.0.1:8080/v1'\n"
        "  • Local (Ollama): export OLLAMA_BASE_URL='http://127.0.0.1:11434/v1'\n"
        "  • Ou configure via '/connect' dentro da TUI."
    )
    return UnconfiguredProviderAdapter(instructions)
