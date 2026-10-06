"""Política de Encadeamento por Modo de Autonomia (premissa do Bombe Code).

Fases canônicas da ONDA:
- UPSTREAM: entendimento, viabilidade e planejamento
  (Onda Zero: DISCOVERY → INCEPTION | Ondas de Entrega: PLAN → REFINEMENT)
- DOWNSTREAM: construção e homologação (EXECUTE → VALIDATE)

Modos:
- AUTO: nunca para (parada mínima — somente furo de informação real).
- SEMI-AUTO: encadeia dentro da fase; PAUSA na fronteira de fase
  (fim do Upstream, antes de construir; fim do Downstream, antes de arquivar).
- MANUAL: pausa ao final de cada etapa.
"""

from __future__ import annotations

FASES: dict[str, frozenset[str]] = {
    "UPSTREAM": frozenset({"DISCOVERY", "DISCUSS", "INCEPTION", "PLAN", "REFINEMENT"}),
    "DOWNSTREAM": frozenset({"EXECUTE", "VALIDATE"}),
}


def fase_de(etapa: str) -> str:
    """Retorna a fase canônica de uma etapa ('UPSTREAM' por padrão)."""
    etapa_norm = (etapa or "").strip().upper()
    if etapa_norm in FASES["DOWNSTREAM"]:
        return "DOWNSTREAM"
    return "UPSTREAM"


def normalizar_autonomia(autonomia: str) -> str:
    return (autonomia or "AUTO").strip().upper().replace("-", "_").replace(" ", "_")


def deve_encadear(autonomia: str, etapa_atual: str, proxima_etapa: str) -> bool:
    """Decide se o runtime encadea automaticamente a próxima etapa.

    AUTO      → sempre True (exceto nada; o fim do MVP também encadeia).
    MANUAL    → sempre False (humano conduz etapa a etapa).
    SEMI_AUTO → True somente dentro da mesma fase; a fronteira
                Upstream→Downstream (e o arquivamento final) pausa para o humano.
    """
    modo = normalizar_autonomia(autonomia)
    if modo == "AUTO":
        return True
    if modo == "MANUAL":
        return False
    # SEMI_AUTO
    proxima = (proxima_etapa or "").strip().upper()
    if proxima in ("COMPLETED", "END"):
        return False  # fim do Downstream: pausa antes de arquivar
    return fase_de(etapa_atual) == fase_de(proxima_etapa)
