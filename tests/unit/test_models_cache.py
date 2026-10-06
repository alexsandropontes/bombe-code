"""Unit: cache do catalogo models.dev (F2 RN1 — TTL 5min + stale offline)."""

from bombe_code.providers.models_dev import get_models

CATALOG = {"openai": {"models": {"gpt-4o": {"id": "gpt-4o"}}}}


def test_cache_ttl_evita_segunda_requisicao(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    calls: list[int] = []

    def fetch() -> dict:
        calls.append(1)
        return CATALOG

    clock = [1000.0]

    def now() -> float:
        return clock[0]

    # Act
    first = get_models(fetch=fetch, now=now)
    clock[0] += 60  # < TTL de 5 min
    second = get_models(fetch=fetch, now=now)
    clock[0] += 6 * 60  # > TTL
    third = get_models(fetch=fetch, now=now)

    # Assert
    assert first == CATALOG
    assert second == CATALOG
    assert third == CATALOG
    assert len(calls) == 2


def test_cache_stale_e_servido_quando_offline(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    get_models(fetch=lambda: CATALOG, now=lambda: 1000.0)

    def off() -> dict:
        raise ConnectionError("sem rede")

    # Act — TTL expirou e fetch falha
    result = get_models(fetch=off, now=lambda: 1000.0 + 6 * 60)

    # Assert — cache stale (antigo mas presente) é servido
    assert result == CATALOG


def test_sem_cache_e_sem_rede_levanta_erro(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    def off() -> dict:
        raise ConnectionError("sem rede")

    # Act & Assert
    try:
        get_models(fetch=off, now=lambda: 1000.0)
    except ConnectionError:
        pass
    else:
        raise AssertionError("deveria propagar erro sem cache e sem rede")
