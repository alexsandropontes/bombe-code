"""Testes da Política de Encadeamento por Modo de Autonomia.

AUTO: nunca para. SEMI-AUTO: pausa só na fronteira de fase (fim do Upstream,
fim do Downstream). MANUAL: pausa ao final de cada etapa (após todos os
agentes e gates da etapa — nunca por agente).
"""

from bombe_code.turing.autonomia import deve_encadear, fase_de, normalizar_autonomia


def test_auto_encadeia_tudo():
    for atual, proxima in [
        ("DISCUSS", "PLAN"),
        ("PLAN", "EXECUTE"),
        ("EXECUTE", "VALIDATE"),
        ("VALIDATE", "COMPLETED"),
        ("DISCOVERY", "INCEPTION"),
    ]:
        assert deve_encadear("AUTO", atual, proxima) is True


def test_manual_nao_encadea_nada():
    for atual, proxima in [
        ("DISCUSS", "PLAN"),
        ("PLAN", "EXECUTE"),
        ("EXECUTE", "VALIDATE"),
        ("VALIDATE", "COMPLETED"),
    ]:
        assert deve_encadear("MANUAL", atual, proxima) is False


def test_semi_auto_encadeia_dentro_da_fase():
    # Upstream: DISCUSS → PLAN (mesma fase)
    assert deve_encadear("SEMI-AUTO", "DISCUSS", "PLAN") is True
    # Downstream: EXECUTE → VALIDATE (mesma fase)
    assert deve_encadear("SEMI-AUTO", "EXECUTE", "VALIDATE") is True
    assert deve_encadear("semi-auto", "REFINEMENT", "EXECUTE") is False  # fronteira


def test_semi_auto_pausa_na_fronteira_de_fase():
    # Fim do Upstream: PLAN (planejamento) → EXECUTE (construção) PAUSA
    assert deve_encadear("SEMI-AUTO", "PLAN", "EXECUTE") is False
    # Fim do Downstream: VALIDATE → arquivamento PAUSA
    assert deve_encadear("SEMI-AUTO", "VALIDATE", "COMPLETED") is False


def test_fases_canonicas():
    assert fase_de("DISCOVERY") == "UPSTREAM"
    assert fase_de("INCEPTION") == "UPSTREAM"
    assert fase_de("PLAN") == "UPSTREAM"
    assert fase_de("REFINEMENT") == "UPSTREAM"
    assert fase_de("EXECUTE") == "DOWNSTREAM"
    assert fase_de("VALIDATE") == "DOWNSTREAM"


def test_normalizacao_de_variacoes():
    assert normalizar_autonomia("semi-auto") == "SEMI_AUTO"
    assert normalizar_autonomia("Semi Auto") == "SEMI_AUTO"
    assert normalizar_autonomia("manual") == "MANUAL"
    assert deve_encadear("semi_auto", "EXECUTE", "VALIDATE") is True
