"""Escada v2 — rota por EVIDÊNCIA:

Dev devolveu PLANO sem gravar arquivo = recusa velada. A escada sobe a
agressividade da ordem: 2 plano aprovado pelo Tech Lead → 3 ordem incisiva →
4 o próprio Tech Lead assume e codifica → só então escala humano com a causa
verdadeira (agent_refusal), nunca "falta de informação".

Com evidência de escrita (dev executou), a trilha clássica se mantém:
dirigido ×2 → @caroli refina a story ×2.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.runner import AgentExecutionResult
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


def _runner_lead(output: str) -> MagicMock:
    runner = MagicMock()

    def run(prompt, *a, **k):
        return AgentExecutionResult(agent_handle="@unclebob", success=True, output=output)

    runner.run.side_effect = run
    return runner


def test_dev_sem_escrita_ativa_plano_aprovado_no_degrau_2(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    chamadas: list[str] = []
    lead = _runner_lead("PLANO APROVADO — implemente agora")
    handles_chamados: list[str] = []

    def fake_get_runner(handle):
        handles_chamados.append(handle)
        if handle == "@unclebob":
            return lead
        return MagicMock()

    orch._get_runner = fake_get_runner

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas.append(rework_feedback or "inicial")
        if len(chamadas) <= 2:  # ciclo inicial + degrau 1 (dirigido) vetam
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
                "dev_output": "PLANO: corrigirei publish/service.py e PublishReport.vue",
                "arquivos_escritos": [],
            }
        return {"success": True, "message": "ok", "arquivos_escritos": ["src/fix.py"]}

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    assert len(chamadas) == 3
    assert "PLANO APROVADO PELO TECH LEAD" in chamadas[2]
    assert "PLANO APROVADO — implemente agora" in chamadas[2]
    assert "@unclebob" in handles_chamados  # validação do plano aconteceu


def test_zero_escrita_em_4_degraus_termina_em_agent_refusal(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    chamadas: list[str] = []

    def fake_get_runner(handle):
        return _runner_lead("PLANO APROVADO — implemente agora")

    orch._get_runner = fake_get_runner

    def fake_cycle_sempre_plano(story_id=None, rework_feedback=None):
        chamadas.append(rework_feedback or "inicial")
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
            "dev_output": "PLANO: farei depois",
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle_sempre_plano

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is False
    esc = res["escalation"]
    assert esc["type"] == "agent_refusal"
    assert "NENHUM arquivo foi gravado" in esc["message"]
    assert "não é falta de informação" in esc["message"]
    # 1 ciclo inicial + 4 degraus (dirigido, plano_aprovado, incisivo, lead_assume)
    assert len(chamadas) == 5
    assert "ORDEM DIRETA" in chamadas[3]
    assert "PLANO APROVADO PELO TECH LEAD" in chamadas[2]


def test_com_escrita_mantem_trilha_classica_caroli(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    chamadas: list[str] = []
    refinamentos: list[str] = []

    def fake_get_runner(handle):
        if handle == "@caroli":
            runner = MagicMock()

            def run(prompt, *a, **k):
                refinamentos.append(prompt)
                return AgentExecutionResult(
                    agent_handle="@caroli", success=True, output="story refinada"
                )

            runner.run.side_effect = run
            return runner
        return MagicMock()

    orch._get_runner = fake_get_runner

    def fake_cycle_executa_mas_reprova(story_id=None, rework_feedback=None):
        chamadas.append(rework_feedback or "inicial")
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

    orch._run_cycle_inner = fake_cycle_executa_mas_reprova

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is False
    assert res["escalation"]["type"] == "human_escalation"
    assert len(refinamentos) == 2, "com execução real, degraus 3-4 são da @caroli"
    assert "PLANO APROVADO" not in "".join(chamadas), "trilha de plano não deveria ter ativado"


def test_resultado_com_evidencia_de_escrita():
    vazio = AgentExecutionResult(agent_handle="@valim", success=True, output="plano")
    assert vazio.escreveu_algum_arquivo is False
    com_escrita = AgentExecutionResult(
        agent_handle="@valim",
        success=True,
        output="feito",
        arquivos_escritos=["src/x.py"],
    )
    assert com_escrita.escreveu_algum_arquivo is True


def test_guardiao_lista_arquivos_gravados():
    from bombe_code.permissions.acao_guard import GuardaDeAcoes

    guarda = GuardaDeAcoes(agente="@valim")
    assert guarda.arquivos_escritos() == []
    guarda.validar_escrita("src/B.py", "conteudo b")
    guarda.validar_escrita("src/A.py", "conteudo a")
    assert guarda.arquivos_escritos() == ["src/a.py", "src/b.py"]
    # rascunho não conta como evidência
    guarda.validar_escrita("rascunho.snippet.py", "plano")
    assert "rascunho.snippet.py" not in guarda.arquivos_escritos()
