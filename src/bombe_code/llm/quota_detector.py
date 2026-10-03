"""Detector determinístico de estouro de cota e rate limit para LLMs e planos de coding.

Suporta identificação de janelas de reset de cota com tratamento rigoroso de fusos horários
(ex: Z.ai / Zhipu AI opera em Beijing Time CST UTC+8, OpenAI e Anthropic em UTC ou segundos relativos).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Fuso horário oficial de Beijing / Pequim (China Standard Time: UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8), name="CST")

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
    "1308",  # Z.ai Usage limit reached for X hour code
    "1113",  # Z.ai Concurrency / Quota limit
    "requests per minute",
    "tokens per minute",
    "rpm limit",
    "tpm limit",
    "billing",
    "plan limit",
    "usage limit reached",
]


@dataclass
class QuotaResetInfo:
    """Metadados estruturados sobre o estouro de cota e tempo para recuperação."""

    is_exhausted: bool
    reset_at_utc: datetime | None = None
    reset_at_local: datetime | None = None
    retry_after_seconds: float | None = None
    is_already_reset: bool = False
    origin_timezone_name: str = "UTC"
    provider: str = "generic"
    human_message: str = ""
    raw_message: str = ""


def parse_quota_reset_info(
    exc: Any,
    provider_hint: str | None = None,
    current_time: datetime | None = None,
) -> QuotaResetInfo:
    """Extrai informações detalhadas sobre horário e tempo de reset de cota da exceção.

    Trata adequadamente o fuso horário de origem (ex: Z.ai / Zhipu AI usa UTC+8 Pequim).
    """
    raw_str = str(exc or "")
    now_utc = current_time.astimezone(timezone.utc) if current_time else datetime.now(timezone.utc)

    # Identifica o provider
    provider = (provider_hint or "generic").lower()
    if any(kw in raw_str.lower() for kw in ("z.ai", "zhipu", "glm", "1308", "1301", "1113")):
        provider = "zai"

    reset_utc: datetime | None = None
    retry_after_secs: float | None = None
    origin_tz_name = "UTC"

    # 1. Padrão Z.ai: "Your limit will reset at YYYY-MM-DD HH:MM:SS" (em Pequim CST UTC+8)
    match_zai_date = re.search(
        r"limit will reset at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", raw_str, re.IGNORECASE
    )
    if match_zai_date:
        date_str = match_zai_date.group(1)
        try:
            naive_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            # Servidores Z.ai emitem hora local de Pequim (UTC+8)
            beijing_dt = naive_dt.replace(tzinfo=BEIJING_TZ)
            reset_utc = beijing_dt.astimezone(timezone.utc)
            origin_tz_name = "Asia/Shanghai (CST UTC+8)"
        except ValueError:
            pass

    # 2. Padrão de segundos ou minutos relativos: "try again in X.XXs" ou "in X minutes"
    if reset_utc is None:
        match_rel = re.search(
            r"(?:try again in|retry after|retry in|reset in)\s+([0-9]+(?:\.[0-9]+)?)\s*(s|sec|seconds|m|min|minutes|h|hours|ms)?",
            raw_str,
            re.IGNORECASE,
        )
        if match_rel:
            val = float(match_rel.group(1))
            unit = (match_rel.group(2) or "s").lower()
            if unit.startswith("m") and not unit.startswith("ms"):
                seconds = val * 60.0
            elif unit.startswith("h"):
                seconds = val * 3600.0
            elif unit == "ms":
                seconds = val / 1000.0
            else:
                seconds = val
            retry_after_secs = seconds
            reset_utc = now_utc + timedelta(seconds=seconds)

    # 3. Headers HTTP (caso estejam na exceção ou objeto response)
    if reset_utc is None:
        response = getattr(exc, "response", None)
        if response is not None and hasattr(response, "headers"):
            headers = response.headers
            retry_after_hdr = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after_hdr:
                try:
                    retry_after_secs = float(retry_after_hdr)
                    reset_utc = now_utc + timedelta(seconds=retry_after_secs)
                except ValueError:
                    pass

    # Se calculou reset_utc, calcula o tempo restante e fuso local
    if reset_utc is not None:
        diff_secs = (reset_utc - now_utc).total_seconds()
        retry_after_secs = round(diff_secs, 1)
        is_already_reset = diff_secs <= 0

        # Converte para o fuso local do usuário
        local_dt = reset_utc.astimezone()
        local_str = local_dt.strftime("%H:%M:%S")

        if is_already_reset:
            human_msg = (
                f"A cota do provedor ({provider.upper()}) resetou às {local_str} (horário local, "
                f"baseado em {origin_tz_name}). A API já está liberada para execução imediata!"
            )
        else:
            mins = int(diff_secs // 60)
            secs = int(diff_secs % 60)
            tempo_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            human_msg = (
                f"Cota do provedor ({provider.upper()}) esgotada. Reset previsto em {tempo_str} "
                f"(às {local_str} no seu horário local, correspondente a {origin_tz_name})."
            )

        return QuotaResetInfo(
            is_exhausted=True,
            reset_at_utc=reset_utc,
            reset_at_local=local_dt,
            retry_after_seconds=retry_after_secs,
            is_already_reset=is_already_reset,
            origin_timezone_name=origin_tz_name,
            provider=provider,
            human_message=human_msg,
            raw_message=raw_str,
        )

    # Se não foi possível extrair a hora exata
    return QuotaResetInfo(
        is_exhausted=True,
        is_already_reset=False,
        provider=provider,
        human_message=f"Estouro de cota / rate limit detectado no provedor {provider.upper()}.",
        raw_message=raw_str,
    )


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

    is_quota = False
    base_reason = ""

    if status_code == 429:
        is_quota = True
        base_reason = f"HTTP 429 (Too Many Requests / Rate Limit / Cota esgotada): {exc}"
    elif status_code == 402:
        is_quota = True
        base_reason = f"HTTP 402 (Payment Required / Cota ou créditos esgotados): {exc}"
    elif "ratelimit" in exc_type or "usagelimit" in exc_type:
        is_quota = True
        base_reason = f"Exceção {type(exc).__name__} (Limite de uso ou taxa atingido): {exc}"
    else:
        # Códigos de erro conhecidos
        code = getattr(exc, "code", None)
        if code is not None:
            code_str = str(code).lower()
            if code_str in ("1301", "1308", "1113", "rate_limit_exceeded", "insufficient_quota"):
                is_quota = True
                base_reason = f"Código de erro da API LLM ({code_str}): {exc}"

        if not is_quota:
            for pattern in QUOTA_ERROR_PATTERNS:
                if pattern in err_str:
                    is_quota = True
                    base_reason = f"Estouro de Cota / Rate Limit detectado ('{pattern}'): {exc}"
                    break

    if not is_quota:
        return False, None

    # Enriquece a mensagem com a análise de fuso horário e recuperação
    quota_info = parse_quota_reset_info(exc)
    if quota_info.human_message:
        full_reason = f"{base_reason} | ⏱️ {quota_info.human_message}"
    else:
        full_reason = base_reason

    return True, full_reason
