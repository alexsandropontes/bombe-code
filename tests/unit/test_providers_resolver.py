"""Testes unitários para o resolvedor enterprise de provedores."""

from __future__ import annotations

import pytest

from bombe_code.providers.resolver import (
    ProviderConfigurationError,
    UnconfiguredProviderAdapter,
    resolve_provider_adapter,
)


def test_resolver_explicit_missing_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderConfigurationError):
        resolve_provider_adapter("openai/gpt-4o")


def test_resolver_with_openai_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key")
    adapter = resolve_provider_adapter("openai/gpt-4o")
    assert adapter.provider == "openai"
    assert adapter.model == "gpt-4o"


def test_resolver_with_anthropic_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
    adapter = resolve_provider_adapter("anthropic/claude-3-5-sonnet-20241022")
    assert adapter.provider == "anthropic"
    assert adapter.model == "claude-3-5-sonnet-20241022"


def test_resolver_llama_cpp_explicit():
    adapter = resolve_provider_adapter("llama.cpp/default")
    assert adapter.provider == "openai"
    assert "8080" in adapter.base_url


def test_resolver_unconfigured_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("LLAMA_CPP_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr("bombe_code.providers.resolver.load_auth", dict)

    adapter = resolve_provider_adapter()
    assert isinstance(adapter, UnconfiguredProviderAdapter)
    stream = list(adapter.stream([]))
    assert any("Provedor não configurado" in chunk.get("text", "") for chunk in stream)
