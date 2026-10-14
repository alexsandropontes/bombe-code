"""Cota do provedor esgotada (HTTP 429 / usage limit) = impedimento de
INFRAESTRUTURA, nunca "falta de informação" nem motivo para queimar a escada.

A escada PAUSA quando a cota estoura e ESPERA o reset da janela SEM consumir
o degrau corrente (corrigir com o provedor de fora é chamada que garante 429).
Só além do teto de espera (BOMBE_QUOTA_MAX_WAIT_SECONDS / MAX_ESPERAS) a linha
faz parada honesta — park com 'quota_paused', card BLOCKED para o próximo
resume retomar sozinho.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.llm.quota_detector import QuotaResetInfo
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    (tmp_path / "app.py").write_text("def app() -> str:\n    return 'ok'\n", encoding="utf-8")
    return tmp_path, db


def _orch(tmp_path: Path, db: ProjectDatabase) -> WaveOrchestrator:
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-001", title="Story 1", agent="@valim", status="IN_PROGRESS"
    )
    return orch


def _seta_quota(orch: WaveOrchestrator, segundos_ate_reset: float) -> None:
    agora = datetime.now(UTC)
    orch._cota_ativa = QuotaResetInfo(
        is_exhausted=True,
        reset_at_utc=agora + timedelta(seconds=segundos_ate_reset),
        reset_at_local=agora + timedelta(seconds=segundos_ate_reset),
        provider="zai",
        human_message="Usage limit reached for 5 hour",
    )


def _fake_get_runner(*_a, **_k) -> MagicMock:
    return MagicMock()


def test_pausa_na_cota_e_retoma_o_mesmo_degrau_sem_gastar_tentativa(project_env, monkeypatch):
    """Cota estoura no ciclo inicial → a escada PAUSA no degrau 1 (gate de
    início), espera o reset (janela já passada → retry imediato) e re-tenta o
    MESMO degrau — não pula para o degrau seguinte nem escala o humano."""
    import bombe_code.turing.quota as quota_mod

    monkeypatch.setattr(quota_mod.time, "sleep", lambda *_: None)
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    orch._get_runner = _fake_get_runner
    ciclos: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        ciclos.append(rework_feedback or "inicial")
        if len(ciclos) == 1:
            _seta_quota(orch, -60)  # reset já passou → retry imediato
            return {
                "success": False,
                "is_blocked": True,
                "error": "Cota esgotada no provedor (429).",
                "review_output": "",
                "arquivos_escritos": [],
            }
        if len(ciclos) == 2:
            orch.kanban.block_card(
                story_id,
                reason="Tech Lead: veredito de REJEIÇÃO — 'bloqueante'",
                blocked_by="@unclebob",
            )
            return {
                "success": False,
                "is_blocked": True,
                "error": "Tech Lead: REJEIÇÃO",
                "review_output": "parecer",
                "arquivos_escritos": ["src/fix.py"],
            }
        return {"success": True, "message": "ok", "arquivos_escritos": ["src/fix.py"]}

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    assert len(ciclos) == 3
    assert "Cota esgotada no provedor" in ciclos[1], (
        "cota consumida no gate de início do degrau 1: o degrau 1 (dirigido "
        "clássico, feedback com o motivo=veta por cota) é re-tentado SEM avançar"
    )
    assert "PLANO APROVADO PELO TECH LEAD" not in "".join(ciclos), (
        "se a escada tivesse avançado (queimar degrau por cota), o degrau 2 seria "
        "trilha de plano aprovado — não pode aparecer"
    )
    assert orch._cota_ativa is None, "a janela de reset foi consumida pela espera"
    assert orch._cota_ativa is None, "a janela de reset foi consumida pela espera"
    assert "escalation" not in res


def test_espera_em_processo_ate_o_reset_e_retoma_mesmo_degrau(project_env, monkeypatch):
    """Janela de reset no futuro próximo: a linha fica em espera no processo e,
    quando a janela passa, retoma do MESMO degrau (nenhuma tentativa queimada)."""
    import bombe_code.turing.quota as quota_mod

    monkeypatch.setattr(quota_mod.time, "sleep", lambda *_: None)
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    orch._get_runner = _fake_get_runner
    ciclos: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        ciclos.append(rework_feedback or "inicial")
        if len(ciclos) == 1:
            _seta_quota(orch, 0.4)  # futura por pouco tempo — espera de verdade
            return {
                "success": False,
                "is_blocked": True,
                "error": "Cota esgotada no provedor (429).",
                "review_output": "",
                "arquivos_escritos": [],
            }
        return {"success": True, "message": "ok", "arquivos_escritos": ["src/fix.py"]}

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    assert len(ciclos) == 2
    assert orch._cota_ativa is None
    assert "escalation" not in res


def test_repeticao_de_cota_apos_reset_curto_park_por_max_esperas(project_env, monkeypatch):
    """Cota re-esgota a cada degrau (janela curta demais): o teto de esperas
    consecutivas (BOMBE_QUOTA_MAX_ESPERAS) converte a linha para parada honesta
    — quota_paused, NUNCA "informação em falta"."""
    import bombe_code.turing.quota as quota_mod

    monkeypatch.setattr(quota_mod.time, "sleep", lambda *_: None)
    monkeypatch.setenv("BOMBE_QUOTA_MAX_ESPERAS", "1")
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    orch._get_runner = _fake_get_runner
    ciclos: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        ciclos.append(rework_feedback or "inicial")
        _seta_quota(orch, -60)  # reset sempre já passou → 'retry' — mas re-esgota
        orch.kanban.block_card(
            story_id,
            reason="Tech Lead: veredito de REJEIÇÃO — 'bloqueante'",
            blocked_by="@unclebob",
        )
        return {
            "success": False,
            "is_blocked": True,
            "error": "Tech Lead: REJEIÇÃO",
            "review_output": "parecer",
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is False
    assert res.get("quota") is True
    assert res["escalation"]["type"] == "quota_paused"
    assert "informação em falta" not in res["error"].lower()
    assert "cota" in res["error"].lower()
    card = orch.kanban.get_card("ST-001")
    assert card and card.get("is_blocked")
    assert "cota" in (card.get("block_reason") or "").lower()


def test_espera_longa_alem_do_limite_park_honesto(project_env, monkeypatch):
    """Reset daqui a 2h com BOMBE_QUOTA_MAX_WAIT_SECONDS=1: a linha não segura
    o processo à toa — parada honesta (quota_paused) para o resume retomar
    quando a janela passar."""
    monkeypatch.setenv("BOMBE_QUOTA_MAX_WAIT_SECONDS", "1")
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    orch._get_runner = _fake_get_runner

    def fake_cycle(story_id=None, rework_feedback=None):
        _seta_quota(orch, 7200)
        return {
            "success": False,
            "is_blocked": True,
            "error": "Cota esgotada no provedor (429).",
            "review_output": "",
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is False
    assert res.get("quota") is True
    assert res["escalation"]["type"] == "quota_paused"
    assert "informação em falta" not in res["error"].lower()
    assert "cota" in res["error"].lower()