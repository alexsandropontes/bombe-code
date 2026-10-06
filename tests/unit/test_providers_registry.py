"""Unit: registry de providers (F2 RN2/RN4)."""

import pytest

from bombe_code.providers.registry import closest_model, default_model, parse_model


def test_parse_model_divide_provider_e_model():
    assert parse_model("openai/gpt-4o") == ("openai", "gpt-4o")


def test_parse_model_sem_barra_e_invalido():
    with pytest.raises(ValueError):
        parse_model("gpt-4o")


def test_parse_model_divide_apenas_na_primeira_barra():
    assert parse_model("openai-compatible/org/model-v2") == (
        "openai-compatible",
        "org/model-v2",
    )


def test_closest_model_prefere_provider_proximo():
    available = ["openai/gpt-4o-mini", "anthropic/claude-sonnet-4"]
    result = closest_model("openai/gpt-4o", available)
    assert result == "openai/gpt-4o-mini"


def test_closest_model_sem_candidato_levanta_erro():
    with pytest.raises(LookupError):
        closest_model("openai/gpt-4o", [])


def test_default_model_usa_flag_default_do_catalogo():
    catalog = {
        "anthropic": {
            "models": {
                "claude-a": {"default": False},
                "claude-b": {"default": True},
            }
        }
    }
    assert default_model("anthropic", catalog) == "claude-b"


def test_default_model_sem_flag_retorna_primeiro():
    catalog = {"openai": {"models": {"gpt-4o": {}, "gpt-4o-mini": {}}}}
    assert default_model("openai", catalog) == "gpt-4o"


def test_default_model_provider_desconhecido_levanta_erro():
    with pytest.raises(KeyError):
        default_model("nao-existe", {})


def test_nove_providers_do_rn4_sao_resolviveis():
    # RN4: paridade open-source — anthopic, openai, google, azure, bedrock,
    # copilot, openrouter, xai, openai-compatible
    providers = (
        "anthropic",
        "openai",
        "google",
        "azure",
        "bedrock",
        "copilot",
        "openrouter",
        "xai",
        "openai-compatible",
    )
    catalog = {p: {"models": {"modelo-x": {}}} for p in providers}
    for provider in providers:
        assert parse_model(f"{provider}/modelo-x") == (provider, "modelo-x")
        assert default_model(provider, catalog) == "modelo-x"
