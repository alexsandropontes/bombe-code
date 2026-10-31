from __future__ import annotations

import concurrent.futures

import pytest

from bombe_code.features.rate_limiter import TokenBucketRateLimiter


def test_init_validation() -> None:
    """Valida que capacidade e taxa de recarga devem ser estritamente positivas."""
    with pytest.raises(ValueError, match="refill_rate must be greater than zero"):
        TokenBucketRateLimiter(refill_rate=0.0, capacity=10.0)

    with pytest.raises(ValueError, match="refill_rate must be greater than zero"):
        TokenBucketRateLimiter(refill_rate=-1.5, capacity=10.0)

    with pytest.raises(ValueError, match="capacity must be greater than zero"):
        TokenBucketRateLimiter(refill_rate=5.0, capacity=0.0)

    with pytest.raises(ValueError, match="capacity must be greater than zero"):
        TokenBucketRateLimiter(refill_rate=5.0, capacity=-10.0)


def test_burst_consumption_until_exhaustion() -> None:
    """Valida consumo imediato em rajada até o esgotamento dos tokens."""
    limiter = TokenBucketRateLimiter(refill_rate=1.0, capacity=5.0)

    assert limiter.capacity == 5.0
    assert limiter.refill_rate == 1.0
    assert limiter.tokens == 5.0

    # Consome 3 tokens
    assert limiter.consume(3) is True
    assert pytest.approx(limiter.tokens, rel=1e-2) == 2.0

    # Consome 2 tokens restantes
    assert limiter.consume(2) is True
    assert pytest.approx(limiter.tokens, abs=0.01) == 0.0

    # Tentativa de consumir com balde vazio deve falhar
    assert limiter.consume(1) is False
    assert limiter.consume() is False


def test_consume_invalid_token_amount() -> None:
    """Valida que quantidade de tokens solicitados deve ser maior que zero."""
    limiter = TokenBucketRateLimiter(refill_rate=5.0, capacity=10.0)

    with pytest.raises(ValueError, match="tokens to consume must be greater than zero"):
        limiter.consume(0)

    with pytest.raises(ValueError, match="tokens to consume must be greater than zero"):
        limiter.consume(-2)


def test_deterministic_temporal_refill() -> None:
    """Valida recarga de tokens determinística usando time_fn injetada."""
    simulated_time = 1000.0

    def mock_time() -> float:
        return simulated_time

    # 2 tokens por segundo, capacidade 10
    limiter = TokenBucketRateLimiter(refill_rate=2.0, capacity=10.0, time_fn=mock_time)

    # Esgota todos os 10 tokens
    assert limiter.consume(10) is True
    assert pytest.approx(limiter.tokens, abs=0.01) == 0.0
    assert limiter.consume(1) is False

    # Avança 1.5 segundos: deve gerar 3.0 tokens
    simulated_time += 1.5
    assert pytest.approx(limiter.tokens, rel=1e-2) == 3.0
    assert limiter.consume(2) is True
    assert pytest.approx(limiter.tokens, rel=1e-2) == 1.0

    # Avança 10 segundos: deve recarregar no máximo até a capacidade (10.0)
    simulated_time += 10.0
    assert pytest.approx(limiter.tokens, rel=1e-2) == 10.0
    assert limiter.consume(10) is True
    assert limiter.consume(1) is False


def test_multithreaded_concurrency_thread_safety() -> None:
    """Valida thread-safety com 50 threads consumindo tokens simultaneamente sem race conditions."""
    total_capacity = 100
    limiter = TokenBucketRateLimiter(refill_rate=0.0001, capacity=total_capacity)

    num_threads = 50
    requests_per_thread = 4  # Total de 200 requisições para 100 tokens

    success_count = 0
    failure_count = 0

    def worker() -> list[bool]:
        results: list[bool] = []
        for _ in range(requests_per_thread):
            results.append(limiter.consume(1))
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            success_count += sum(1 for x in res if x)
            failure_count += sum(1 for x in res if not x)

    # Exatamente total_capacity consumos devem ter tido sucesso
    assert success_count == total_capacity
    assert failure_count == (num_threads * requests_per_thread) - total_capacity
    assert pytest.approx(limiter.tokens, abs=0.01) == 0.0
