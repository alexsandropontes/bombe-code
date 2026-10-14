"""Política de COTA do provedor (SRP — uma responsabilidade: decidir e operar
a pausa por cota).

Premissa: cota esgotada (HTTP 429) é INFRAESTRUTURA de fora — nunca recusa de
dev, nunca "falta de informação". A linha PAUSA, ESPERA o reset e RETOMA
sozinha; park honesto quando a espera é bloqueada por BOMBE_QUOTA_MAX_WAIT_SECONDS
ou repetida demais (BOMBE_QUOTA_MAX_ESPERAS). O kanban é avisado (card blocked
= Impedimento, prioridade máxima no resume).

Tudo aqui é DETERMINÍSTICO: assinatura de texto, janela de reset, teto de
esperas — zero juízo de LLM.
"""

from __future__ import annotations

import os
import time
from typing import Any

from bombe_code.llm.quota_detector import QuotaResetInfo, quota_info_de_texto
from bombe_code.turing.progress import ABORT_EVENT, BUS


class PoliticaDeCota:
    """Estado + decisão de cota do provedor. A orchestrator delega aqui."""

    def __init__(self, kanban: Any) -> None:
        self.kanban = kanban
        self.ativa: QuotaResetInfo | None = None

    # ── anotação de resultados ──
    def anotar_resultado(self, res: Any) -> None:
        """Lê um resultado de agente e guarda a janela de reset quando a
        assinatura de cota esgotada estiver presente (status QUOTA_EXHAUSTED
        do runner ou block_reason/error com 429/cota/rate-limit/usage-limit)."""
        if res is None:
            return
        texto = getattr(res, "block_reason", None) or getattr(res, "error", None)
        if not texto and getattr(res, "status", "") == "QUOTA_EXHAUSTED":
            texto = f"Cota esgotada no provedor ({getattr(res, 'agent_handle', '?')})."
        self.anotar_texto(texto)

    def anotar_texto(self, texto: str | None) -> None:
        if not texto:
            return
        info = quota_info_de_texto(texto)
        if info is None or not info.is_exhausted or info.is_already_reset:
            return
        atual = self.ativa
        if atual is None or (
            info.reset_at_utc
            and (atual.reset_at_utc is None or info.reset_at_utc > atual.reset_at_utc)
        ):
            self.ativa = info

    def ocorreu(self, res: Any) -> bool:
        """Anota o resultado e retorna True se a cota ficou ATIVA — o par
        anotar+verificar num só gesto (DRY do esqueleto da linha)."""
        self.anotar_resultado(res)
        return self.ativa is not None

    # ── espera do reset ──
    @staticmethod
    def fmt_restante(segundos: float) -> str:
        segundos = max(0, int(segundos))
        h, resto = divmod(segundos, 3600)
        m, s = divmod(resto, 60)
        if h:
            return f"{h}h {m:02d}m"
        if m:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    def esperar_reset(self, story: str) -> tuple[str, str | None, QuotaResetInfo | None]:
        """PAUSA a linha e ESPERA a janela de reset da cota do provedor.

        Retorna (decisao, mensagem, info):
          - 'retry': janela resetou (ou não havia cota) — pode retomar agora;
          - 'abort': usuário interrompeu com ESC ESC (checkpoint salvo);
          - 'park':  espera muito longa além de BOMBE_QUOTA_MAX_WAIT_SECONDS —
                     parada honesta (NUNCA 'informação em falta'); o próximo
                     resume retoma quando a janela passar (card bloqueado é
                     Impedimento, prioridade máxima na fila).
        """
        from datetime import UTC, datetime

        info = self.ativa
        self.ativa = None
        if info is None:
            return "retry", None, None

        def _restante() -> float:
            if info.reset_at_utc is None:
                return info.retry_after_seconds or 0.0
            return (info.reset_at_utc - datetime.now(UTC)).total_seconds()

        restante = _restante()
        if restante <= 0:
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"🟢 COTA DO PROVEDOR LIBERADA — {story}: a janela de reset já "
                    "passou; a linha retoma agora mesmo."
                ),
            )
            return "retry", None, info

        hora_reset = info.reset_at_local.strftime("%H:%M:%S") if info.reset_at_local else None
        max_wait = float(os.environ.get("BOMBE_QUOTA_MAX_WAIT_SECONDS", "0") or 0)
        if max_wait > 0 and restante > max_wait:
            msg = (
                f"🟠 COTA ESGOTADA — {story}: a janela de reset do provedor passa em "
                f"{self.fmt_restante(restante)}"
                + (f" (retoma prevista às {hora_reset}). " if hora_reset else ". ")
                + "A linha PAUSA — isto NÃO é falta de informação, é cota da plataforma "
                "de IA — e retoma sozinha assim que a janela resetar. "
                "(BOMBE_QUOTA_MAX_WAIT_SECONDS bloqueou a espera em processo; aumente "
                "o limite se quiser que a linha fique aguardando de verdade.)"
            )
            BUS.publish("announcement", agent="@turing", text=msg)
            return "park", msg, info

        BUS.publish(
            "announcement",
            agent="@turing",
            text=(
                f"⏳ COTA ESGOTADA — {story}: aguardando reset do provedor "
                f"({self.fmt_restante(restante)} restantes"
                + (f", retoma prevista às {hora_reset}" if hora_reset else "")
                + "). A linha fica parada até lá e retoma sozinha; ESC ESC interrompe."
            ),
        )
        ultimo_anuncio = time.monotonic()
        while True:
            if ABORT_EVENT.is_set():
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"⏸ {story}: espera de reset da cota interrompida pelo usuário "
                        "(ESC ESC) — /wave resume retoma."
                    ),
                )
                return "abort", "Espera de reset de cota interrompida pelo usuário.", info
            restante = _restante()
            if restante <= 0:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🟢 COTA DO PROVEDOR LIBERADA — {story}: reset concluído; "
                        "a linha retoma a execução."
                    ),
                )
                return "retry", None, info
            agora = time.monotonic()
            if agora - ultimo_anuncio >= 60.0:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"⏳ {story}: aguardando reset da cota "
                        f"({self.fmt_restante(restante)} restantes"
                        + (f", retoma às {hora_reset}" if hora_reset else "")
                        + ")..."
                    ),
                )
                ultimo_anuncio = agora
            time.sleep(min(20.0, max(0.5, restante)))

    # ── parada honesta (park) ──
    def parada(self, story: str, msg: str, completed_stories: list[str]) -> dict[str, Any]:
        """Retorno de PAUSA honesta: cota esgotada no provedor (infra), nunca
        escalação por "falta de informação". Card fica BLOCKED (Impedimento) — o
        próximo resume, com a janela já resetada, retoma sozinho."""
        BUS.publish(
            "escalation",
            agent="@turing",
            text=msg,
            escalation={"type": "quota_paused", "story": story, "message": msg},
        )
        self.kanban.block_card(story, reason=msg, blocked_by="@turing")
        return {
            "success": False,
            "completed_stories": completed_stories,
            "failed_story": story,
            "blocked": True,
            "quota": True,
            "escalation": {
                "type": "quota_paused",
                "story": story,
                "reason": msg,
                "message": msg,
            },
            "error": msg,
        }

    # ── gate da escada ──
    def gate_escada(
        self, story: str, esperas_cota: int, completed_stories: list[str]
    ) -> tuple[str, int, dict[str, Any] | None]:
        """Gate de cota usado na escada (início do degrau e fim do degrau).

        Retorna (decisao, esperas_cota, retorno):
          - ('continue', n+1, None): janela resetou — re-tenta o MESMO degrau,
            sem gastar tentativa de convergência com infra pausada;
          - ('return', n, dict): parada honesta (abort/park/limite de esperas).
        """
        if not self.ativa:
            return "continue", esperas_cota, None
        decisao, msg_cota, _info = self.esperar_reset(story)
        if decisao in ("abort", "park"):
            return "return", esperas_cota, (
                {
                    "success": False,
                    "completed_stories": completed_stories,
                    "interrompido": True,
                    "error": "Espera de reset de cota interrompida pelo usuário (checkpoint salvo).",
                }
                if decisao == "abort"
                else self.parada(story, msg_cota or "Cota esgotada.", completed_stories)
            )
        esperas_cota += 1
        capacidade = int(os.environ.get("BOMBE_QUOTA_MAX_ESPERAS", "3") or 3)
        if esperas_cota > capacidade:
            return "return", esperas_cota, self.parada(
                story,
                f"🟠 COTA ESGOTADA REPETIDAMENTE — {story}: a cota do provedor esgotou "
                "diversas vezes mesmo após o reset da janela. Parada honesta (infra, "
                "não falta de informação): verifique a cota contratada antes de /wave resume.",
                completed_stories,
            )
        return "continue", esperas_cota, None
