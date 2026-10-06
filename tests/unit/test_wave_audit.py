"""Testes da Contra-Auditoria Forense (@hoare) — 'Pedido vs. Entregue' com o
CÓDIGO como fonte da verdade. Metodologia DIFERENTE do validate original."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.runner import AgentExecutionResult
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.audit import (
    coletar_evidencias,
    executar_suite_testes,
    extrair_aleacoes_relatorio,
    extrair_furos,
    veredito_auditoria,
)
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage, WaveState


# ------------------------------------------------------------ determinístico
def test_coleta_fraudes_em_producao(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "def pagar():\n    raise NotImplementedError  # depois eu faço\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_pagar():\n    assert True\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")

    ev = coletar_evidencias(tmp_path, "ONDA-001", report_anterior="")
    assert "src/app.py" in ev.arquivos_producao
    assert any("tests/test_app.py" in t for t in ev.testes_encontrados)
    assert any("NotImplementedError" in f for f in ev.fraudes_potenciais)
    assert any("src/app.py" in f for f in ev.fraudes_potenciais)


def test_extrai_aleacoes_do_relatorio_anterior():
    report = (
        "| ST-003 | ✅ | CA-02 coberto com testes reais |\n"
        "- Suíte passando com PostgreSQL real, sem mocks.\n"
        "# Cabeçalho sem alegação\n"
    )
    aleacoes = extrair_aleacoes_relatorio(report)
    assert any("CA-02" in a for a in aleacoes)
    assert any("sem mocks" in a for a in aleacoes)


def test_extrai_furos_e_veredito_do_laudo():
    laudo_com_furos = (
        "Auditoria concluída.\n"
        "FURO: ST-003 — editor read-only — evidência: src/editor/SectionEditor.vue\n"
        "FURO: ST-004 — CA-03 sem teste — evidência: tests/\n"
    )
    furos = extrair_furos(laudo_com_furos)
    assert len(furos) == 2
    limpo, motivo = veredito_auditoria(laudo_com_furos, furos)
    assert limpo is False
    assert "2 furo(s)" in motivo

    laudo_limpo = "Nada a apontar. AUDITORIA: LIMPA"
    furos2 = extrair_furos(laudo_limpo)
    limpo2, _ = veredito_auditoria(laudo_limpo, furos2)
    assert limpo2 is True


def test_suite_ausente_e_inconclusiva_sem_crash(tmp_path: Path):
    resultado, detalhes = executar_suite_testes(tmp_path)
    assert resultado == "AUSENTE"
    assert detalhes


# ------------------------------------------------------------ integração
def _prepara(tmp_path: Path, db: ProjectDatabase) -> WaveOrchestrator:
    (tmp_path / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    orch.end_wave()
    return orch


def _runner_fake(saidas: list[str]) -> MagicMock:
    runner = MagicMock()

    def run_side_effect(prompt: str, *args, **kwargs):
        saida = saidas.pop(0) if len(saidas) > 1 else saidas[0]
        return AgentExecutionResult(agent_handle="@hoare", success=True, output=saida)

    runner.run.side_effect = run_side_effect
    return runner


def test_auditoria_com_furos_bloqueia_e_abre_ciclo_autonomo(
    tmp_path: Path,
):
    db = ProjectDatabase(str(tmp_path))
    orch = _prepara(tmp_path, db)
    for sid in ("ST-001", "ST-002"):
        orch.kanban.add_card(
            story_id=sid, wave_id="ONDA-001", title=f"Story {sid}", agent="@valim", status="DONE"
        )

    hoare = _runner_fake(
        ["Laudo adversarial.\nFURO: ST-002 — CA-03 sem implementação — evidência: src/\n"]
    )
    runners = {"@hoare": hoare}
    orch._get_runner = lambda handle: runners.get(handle)

    burn_calls: list[str] = []

    def fake_cycle(story_id=None):
        burn_calls.append(story_id or "?")
        if orch.state_machine.current_state == WaveState.EXECUTE:
            orch.state_machine.transition_to(WaveState.VALIDATE)
        return {"success": True, "message": "re-queimada"}

    orch._run_cycle_inner = fake_cycle

    res = orch.run_audit("ONDA-001")

    assert res["success"] is True
    assert res["limpa"] is False
    assert len(res["furos"]) == 1
    # Card da story com furo foi bloqueado com a assinatura do @hoare
    card = orch.kanban.get_card("ST-002")
    assert card["is_blocked"] == 1
    assert "@hoare" in card["blocked_by"]
    # A onda auditada assumiu o comando e foi reaberta; re-burn executado
    assert orch.state_machine.wave_id == "ONDA-001"
    assert burn_calls == ["ST-002"]
    # Laudo persistido no workspace
    assert Path(res["laudo_path"]).exists()


def test_auditoria_limpa_nao_muda_estado(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    orch = _prepara(tmp_path, db)
    orch.start_wave("ONDA-002")  # outra onda ativa

    hoare = _runner_fake(["Verifiquei tudo. AUDITORIA: LIMPA"])
    runners = {"@hoare": hoare}
    orch._get_runner = lambda handle: runners.get(handle)

    res = orch.run_audit("ONDA-001")

    assert res["success"] is True
    assert res["limpa"] is True
    assert res["furos"] == []
    # A onda ativa NÃO foi sequestrada por uma auditoria limpa
    assert orch.state_machine.wave_id == "ONDA-002"


def test_suite_falhando_e_tratada_como_furo_obvio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Alegação anterior de 'testes verdes' + suíte real falhando agora = furo na lata."""
    db = ProjectDatabase(str(tmp_path))
    orch = _prepara(tmp_path, db)

    import bombe_code.turing.audit as audit_mod

    monkeypatch.setattr(
        audit_mod, "executar_suite_testes", lambda *a, **k: ("FALHOU (exit 1)", "3 failed")
    )

    hoare = _runner_fake(
        [
            (
                "FURO: ST-001 — suíte real falha apesar do relatório alegar testes passando — evidência: pytest\n"
                "AUDITORIA: LIMPA"  # tentativa de fraude do laudo não engana o veredito estrutural
            ),
        ]
    )
    runners = {"@hoare": hoare}
    orch._get_runner = lambda handle: runners.get(handle)

    res = orch.run_audit("ONDA-001")

    assert res["success"] is True
    assert res["limpa"] is False, "veredito estrutural deve vetar LIMPA com FURO listado"
    assert any("suíte" in f.lower() for f in res["furos"])
