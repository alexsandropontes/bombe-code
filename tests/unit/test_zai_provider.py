"""Testes unitários para o provedor Z.ai / Zhipu AI e carregamento seguro de credenciais locais.
TDD Estrito: RED -> GREEN.
"""

from pathlib import Path

from bombe_code.providers.adapters.openai_compat import OpenAICompatAdapter
from bombe_code.providers.auth import load_auth
from bombe_code.providers.resolver import resolve_provider_adapter


def test_load_auth_reads_local_project_auth(tmp_path: Path, monkeypatch):
    bombe_dir = tmp_path / ".bombe"
    bombe_dir.mkdir()
    auth_file = bombe_dir / "auth.json"
    auth_file.write_text(
        '{"zai-coding-plan": {"key": "test-key-123", "base_url": "https://api.z.ai/api/coding/paas/v4"}}',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    auth = load_auth()
    assert "zai-coding-plan" in auth
    assert auth["zai-coding-plan"]["key"] == "test-key-123"


def test_resolve_zai_provider_adapter(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    adapter = resolve_provider_adapter("zai-coding-plan/glm-5.3-flash")

    assert isinstance(adapter, OpenAICompatAdapter)
    assert adapter.api_key == "test-zai-key"
    assert adapter.model == "glm-5.3-flash"
    assert "api.z.ai/api/coding/paas/v4" in adapter.base_url


def test_resolve_zai_default_model_and_url(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    adapter = resolve_provider_adapter("zai")

    assert isinstance(adapter, OpenAICompatAdapter)
    assert adapter.model == "glm-5.3-flash"
    assert adapter.base_url == "https://api.z.ai/api/coding/paas/v4"
