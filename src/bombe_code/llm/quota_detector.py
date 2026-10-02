"""Detector determinístico de estouro de cota e rate limit para LLMs e planos de coding (Z.ai, OpenAI, Anthropic, Gemini, etc)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

QUOTA_ERROR_PATTERNS: list[str] = [
    "quota",
    "insufficient balance",
    "balance insufficient",
    "credit balance",
    "resource_exhausted",
    "resource has been exhausted",
    "rate limit",
    "ratelimit",
    "too many requests",
    "tokens limit reached",
    "1301",  # Z.ai Insufficient balance / Quota exceeded code
    "1113",  # Z.ai Concurrency / Quota limit
    "requests per minute",
    "tokens per minute",
    "rpm limit",
    "tpm limit",
    "billing",
    "plan limit",
]


def is_quota_or_rate_limit_error(exc: Any) -> tuple[bool, str | None]:
    """Inspeciona a exceção ou payload para identificar se o plano de coding ou cota da LLM esgotou.
    
    Retorna (is_quota_error, error_summary).
    """
    if exc is None:
        return False, None

    err_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    # 1. Checa status HTTP direto na exceção ou objeto response
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        if response is not None:
            status_code = getattr(response, "status_code", None)

    if status_code == 429:
        return True, f"HTTP 429 (Too Many Requests / Rate Limit / Cota esgotada): {exc}"
    if status_code == 402:
        return True, f"HTTP 402 (Payment Required / Cota ou créditos esgotados): {exc}"

    # 2. Tipos de exceção conhecidos em bibliotecas de LLM (OpenAI, PydanticAI, httpx)
    if "ratelimit" in exc_type or "usagelimit" in exc_type:
        return True, f"Exceção {type(exc).__name__} (Limite de uso ou taxa atingido): {exc}"

    # 3. Z.ai e OpenAI códigos de erro retornados em corpo JSON ou atributos
    code = getattr(exc, "code", None)
    if code is not None:
        code_str = str(code).lower()
        if code_str in ("1301", "1113", "rate_limit_exceeded", "insufficient_quota"):
            return True, f"Código de erro da API LLM ({code_str}): {exc}"

    # 4. Inspeciona padrões textuais no erro
    for pattern in QUOTA_ERROR_PATTERNS:
        if pattern in err_str:
            return True, f"Estouro de Cota / Rate Limit detectado ('{pattern}'): {exc}"

    return False, None
