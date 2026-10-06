"""Testes do RESUME de ONDA — retomada exata do checkpoint persistido pós-veto.

Garantia: um processo interrompido (ex.: veto na VALIDATE em versões antigas
ou dúvida de negócio) deve ser retomado EXATAMENTE onde parou — nunca
reiniciado por heurística.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.runner import AgentExecutionResult
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage, WaveState


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    return tmp_path, db


def test_resume_restaura_etapa_validate_apos_veto(project_env):
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    # Cenário veto: processo parou na VALIDATE (estado persistido).
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-001", title="Setup", agent="@valim", status="DONE"
    )
    orch.kanban.add_card(
        story_id="ST-002", wave_id="ONDA-001", title="Árvore", agent="@valim", status="DEV_DONE"
    )

    # Nova instância (novo processo / reinício da TUI) retoma a onda:
    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-001")

    assert res["success"] is True
    assert res.get("resumed") is True
    assert res["stage"] == WaveState.VALIDATE.value
    assert "retomada" in res["message"].lower()
    # Máquina de estados restaurada no ponto exato
    assert orch2.state_machine.current_state == WaveState.VALIDATE
    # Estado persistido permanece VALIDATE
    assert db.load_wave_state()["state"] == WaveState.VALIDATE.value
    # Diagnóstico pelas filas do Kanban (padrão code-forge retomar())
    diag = res["diagnosis"]
    assert diag["done"] == ["ST-001"]
    assert diag["dev_done"] == ["ST-002"]
    assert "1 story(ies) DONE" in diag["summary"]
    assert "DEV_DONE" in diag["summary"]


def test_resume_a_partir_de_qualquer_etapa_pendente(project_env):
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-002", autonomy_mode="SEMI_AUTO")
    orch.transition_to(TuringStage.PLAN)

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-002")
    assert res.get("resumed") is True
    assert res["stage"] == WaveState.PLAN.value
    # Modo de autonomia persistido prevalece na retomada
    assert res["autonomy_mode"] == "SEMI_AUTO"


def _runner_fake(saidas: list[str]) -> MagicMock:
    runner = MagicMock()

    def run_side_effect(prompt: str, *args, **kwargs):
        saida = saidas.pop(0) if len(saidas) > 1 else saidas[0]
        return AgentExecutionResult(agent_handle="@fake", success=True, output=saida)

    runner.run.side_effect = run_side_effect
    return runner


def test_force_e_obsoleto_mesma_onda_pendente_sempre_retoma(project_env):
    """--force não existe mais: mesma ONDA pendente → RESUME do checkpoint,
    independentemente de qualquer flag (o Turing decide sozinho)."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-001", force=True)  # flag obsoleta: ignorada
    assert res.get("resumed") is True
    assert res["stage"] == WaveState.VALIDATE.value


def test_autocura_reabre_onda_arquivada_com_dev_done(project_env):
    """O humano NUNCA precisa saber que houve erro: ao instanciar o runtime,
    a ONDA arquivada indevidamente (cards DEV_DONE) é reaberta na VALIDATE."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    for sid in ("ST-001", "ST-002"):
        orch.kanban.add_card(
            story_id=sid,
            wave_id="ONDA-001",
            title=f"Story {sid}",
            agent="@valim",
            status="DEV_DONE",
        )
    orch.end_wave()  # arquivada indevidamente
    assert db.load_wave_state()["state"] == WaveState.COMPLETED.value

    # Boot de um novo runtime (TUI/CLI/qualquer comando): autocura roda sozinha.
    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    assert orch2.state_machine.current_state == WaveState.VALIDATE
    assert db.load_wave_state()["state"] == WaveState.VALIDATE.value


def test_autocura_reabre_onda_com_relatorio_de_rejeicao(project_env):
    """Homologação indevida com REJEITADO no relatório → autocura reabre."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    orch.end_wave()
    # Simula o falso positivo do make-books: relatório REJEITADO dentro de onda COMPLETED
    report = orch.workspace.wave_validation_report_path("ONDA-001")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Relatório\n- **Resultado Final:** APROVADO\n\n## Veredito Final: **REJEITADO — Retorno para retrabalho**\n",
        encoding="utf-8",
    )

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    assert orch2.state_machine.current_state == WaveState.VALIDATE


def test_autocura_nao_toca_onda_saudavel(project_env):
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    estado_antes = db.load_wave_state()

    WaveOrchestrator(project_dir=str(tmp_path), db=db)  # boot novo

    assert db.load_wave_state() == estado_antes


def test_onda_completada_nao_retoma(project_env):
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    orch.end_wave()

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-001")
    assert res.get("resumed") is not True
    assert res["stage"] == WaveState.DISCUSS.value


def test_trocar_de_onda_arquiva_checkpoint_sem_decisao_humana(project_env):
    """Autonomia total: pedir outra ONDA com checkpoint ativo arquiva o antigo
    no histórico e prossegue — nenhum '--force', nenhuma pergunta ao humano."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-002")

    assert res["success"] is True
    assert res["wave_id"] == "ONDA-002"
    # O checkpoint da ONDA-001 foi preservado no histórico
    checkpoint = db.load_wave_checkpoint("ONDA-001")
    assert checkpoint is not None
    assert checkpoint["state"] == WaveState.PLAN.value


def test_onda_concluida_com_cards_dev_done_reabre_na_validate(project_env):
    """Cenário make-books: onda arquivada com homologação indevida (cards
    DEV_DONE, nunca DONE) → o Turing reabre direto na VALIDATE, sem '--force'."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    for sid in ("ST-001", "ST-002", "ST-003", "ST-004"):
        orch.kanban.add_card(
            story_id=sid,
            wave_id="ONDA-001",
            title=f"Story {sid}",
            agent="@valim",
            status="DEV_DONE",
        )
    orch.end_wave()  # falso positivo arquivado como COMPLETED

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    res = orch2.start_wave("ONDA-001")

    assert res["success"] is True
    assert res["stage"] == WaveState.VALIDATE.value
    assert orch2.state_machine.current_state == WaveState.VALIDATE


def test_autocura_global_avisa_sem_revalidar_retroativamente(project_env):
    """Economia de tokens: evidência de pendência em onda antiga gera APENAS
    aviso determinístico (custo zero) — a máquina NUNCA revalida 300 ondas por
    conta própria. A ação é do usuário: /wave audit ONDA-xxx."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    orch.end_wave()
    # Falso positivo: relatório consolidado contém veredito de rejeição
    report = orch.workspace.wave_validation_report_path("ONDA-001")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Relatório\n- **Resultado Final:** APROVADO\n\n## Veredito Final: **REJEITADO — Retorno para retrabalho (B-1 e B-2)**\n",
        encoding="utf-8",
    )

    # A máquina segue para a ONDA-002 (vazia, PLAN) como no log do usuário
    orch.start_wave("ONDA-002")
    assert db.load_wave_state()["wave_id"] == "ONDA-002"

    # Boot do runtime: autocura AVISA sobre a ONDA-001 mas NÃO assume o comando
    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    assert orch2.state_machine.wave_id == "ONDA-002"
    assert db.load_wave_state()["wave_id"] == "ONDA-002"
    # Nenhuma revalidação retroativa foi disparada (ONDA-001 permanece no disco)
    assert orch.workspace.wave_validation_report_path("ONDA-001").exists()


def test_autocura_global_nao_hijacked_onda_com_trabalho_em_voo(project_env):
    """Se a onda ativa TEM trabalho em voo (cards), a autocura não a sequestra —
    apenas cura a ativa se ela própria estiver anômala."""
    tmp_path, db = project_env
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-002")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-010", wave_id="ONDA-002", title="Em voo", agent="@valim", status="IN_PROGRESS"
    )

    # ONDA-001 anômala no histórico do workspace
    report = orch.workspace.wave_validation_report_path("ONDA-001")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("## Veredito Final: **REJEITADO**\n", encoding="utf-8")

    orch2 = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    # A onda ativa (com trabalho em voo) mantém o comando
    assert orch2.state_machine.wave_id == "ONDA-002"


def test_orcamento_de_retrabalho_escala_ao_esgotar_sessao(project_env):
    """Teto de sessão: rodadas persistentes ≥ MAX → escala com evidência em vez
    de queimar tokens infinitamente (o limbo de 1h24 do make-books)."""
    tmp_path, db = project_env
    (tmp_path / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)

    # Simula sessão já exaurida anteriormente (crash/loop histórico)
    db.set_meta("rework_rounds:ONDA-001", "3")

    edith = _runner_fake(["Parecer vago sem aprovação."])
    nina = _runner_fake(["Governança: APROVADO."])
    runners = {"@edith": edith, "@nina": nina}
    orch._get_runner = lambda handle: runners.get(handle)

    res = orch.run_validate()
    assert res["success"] is False
    escalation = res["rework"]["escalation"]
    assert "ORÇAMENTO DE RETRABALHO ESGOTADO" in escalation["message"]
    assert edith.run.call_count == 1  # nenhuma rodada nova queimada


def test_sucesso_zera_orcamento_de_retrabalho(project_env):
    tmp_path, db = project_env
    (tmp_path / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)
    db.set_meta("rework_rounds:ONDA-001", "2")

    edith = _runner_fake(["Homologação: APROVADO. Entrega íntegra."])
    nina = _runner_fake(["Governança: APROVADO."])
    runners = {"@edith": edith, "@nina": nina}
    orch._get_runner = lambda handle: runners.get(handle)

    res = orch.run_validate()
    assert res["success"] is True
    assert db.get_meta("rework_rounds:ONDA-001") == "0"
