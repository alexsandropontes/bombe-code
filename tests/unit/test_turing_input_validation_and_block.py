"""Testes determinísticos para as duas regras inegociáveis:
1. Turing valida saída de cada agente no Upstream sem exceções.
2. Todo agente valida sua entrada antes de executar; se faltar, bloqueia (BLOCKED) e Turing intervém.
"""

from unittest.mock import MagicMock

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


def test_rule1_turing_rejects_upstream_output_without_negotiation(tmp_path):
    """Regra 1: Turing avalia saída via Gates e não aceita documentação incompleta."""
    db = ProjectDatabase(tmp_path / "test.db")
    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    # Retorna parecer aprovado mas sem seção de riscos
    mock_res.data = "Viabilidade aprovada com sucesso.\n\n## Parecer\nViável tecnicamente."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-RULE-01")

    res = orch.run_discuss(topic="Pagamento Instantâneo")
    assert res["success"] is False
    assert "Gate de Viabilidade reprovado" in res["error"]
    # Garante intervenção e bloqueio
    card = orch.kanban.get_card("ST-001")
    assert card is not None
    assert card["is_blocked"] in (1, True)


def test_rule2_agent_validates_input_and_blocked_triggers_turing(tmp_path):
    """Regra 2: Se faltar entrada essencial para o agente, ele devolve BLOCKED e Turing intervém."""
    db = ProjectDatabase(tmp_path / "test.db")
    mock_factory = MagicMock()
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-RULE-02")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)

    # Tenta rodar a story ST-099 SEM o arquivo físico da story existir
    res = orch.run_cycle("ST-099")
    assert res["success"] is False
    assert res["is_blocked"] is True
    assert res["blocked_by"] == "@aniche"
    assert "Pré-requisito ausente" in res["error"]

    # Intervenção OBRIGATÓRIA do Turing no Kanban
    card = orch.kanban.get_card("ST-099")
    assert card is not None
    assert card["is_blocked"] in (1, True)
    assert card["blocked_by"] == "@aniche"
    assert "ST-099.md" in card["block_reason"]
