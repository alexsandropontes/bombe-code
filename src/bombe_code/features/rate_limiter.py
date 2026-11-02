"""Implementação thread-safe do algoritmo Token Bucket Rate Limiter."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucketRateLimiter:
    """Rate limiter baseado no algoritmo Token Bucket com precisão temporal contínua."""

    def __init__(
        self,
        refill_rate: float,
        capacity: float,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if refill_rate <= 0:
            raise ValueError("refill_rate must be greater than zero")
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self._refill_rate = float(refill_rate)
        self._capacity = float(capacity)
        self._time_fn = time_fn
        self._tokens = float(capacity)
        self._last_refill = self._time_fn()
        self._lock = threading.Lock()

    @property
    def capacity(self) -> float:
        """Capacidade máxima de tokens acumuláveis no bucket."""
        return self._capacity

    @property
    def refill_rate(self) -> float:
        """Taxa contínua de recarga de tokens por segundo."""
        return self._refill_rate

    @property
    def tokens(self) -> float:
        """Quantidade de tokens atualmente disponíveis no bucket."""
        with self._lock:
            self._refill(self._time_fn())
            return self._tokens

    def _refill(self, now: float) -> None:
        """Calcula e acumula tokens decorrentes do delta temporal."""
        delta = now - self._last_refill
        if delta > 0:
            accumulated = delta * self._refill_rate
            self._tokens = min(self._capacity, self._tokens + accumulated)
            self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Tenta consumir a quantidade especificada de tokens de forma thread-safe."""
        if tokens <= 0:
            raise ValueError("tokens to consume must be greater than zero")

        with self._lock:
            now = self._time_fn()
            self._refill(now)
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
