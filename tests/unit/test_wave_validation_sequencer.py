"""Testes unitários e de integração para a validação incremental com WaveSequencer no Bombe Code."""

from pathlib import Path
from unittest.mock import MagicMock

from bombe_code.domain.wave.models import WaveState
from bombe_code.turing.orchestrator import WaveOrchestrator

SAMPLE_PRD_WITH_SEQUENCER = """
# PRD - Drops MVP
## Visão Geral
App de wellness.

## Sequenciador de Ondas do MVP (Lean Inception)
| Onda | Nome da Onda | Hipótese de Negócio | Fatias Verticais / Features | Risco | Final |
| ONDA-001 | Core Loop | Usuário lê sua dose diária | Auth JWT, Leitor de Cards | VERMELHO | Não |
| ONDA-002 | Retenção & Sinais | Usuário salva e curte | Favoritos, Feedback | AMARELO | Não |
| ONDA-003 | Operacional | Rotina diária autônoma | Web Push, Job Cron | VERDE | Sim |
"""


def test_orchestrator_validate_intermediate_wave_prompt(tmp_path: Path):
    # Cria o diretório de testes simulado
    docs_dir = tmp_path / "docs" / "briefings"
    docs_dir.mkdir(parents=True)
    (docs_dir / "PRD.md").write_text(SAMPLE_PRD_WITH_SEQUENCER, encoding="utf-8")

    # Arquivo de código simulado
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")

    orch = WaveOrchestrator(project_dir=tmp_path)
    orch.state_machine.wave_id = "ONDA-001"
    orch.state_machine._current_state = WaveState.VALIDATE

    # Mock do runner da Edith
    runner_edith = MagicMock()
    runner_edith.run.return_value = MagicMock(
        success=True,
        is_blocked=False,
        output="Homologação: APROVADO",
        block_reason=None,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_ms=200,
    )
    runner_nina = MagicMock()
    runner_nina.run.return_value = MagicMock(
        success=True,
        is_blocked=False,
        output="Governança: APROVADO",
        block_reason=None,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_ms=200,
    )

    def mock_get_runner(handle: str):
        if handle == "@edith":
            return runner_edith
        if handle == "@nina":
            return runner_nina
        return None

    orch._get_runner = mock_get_runner

    res = orch.run_validate()
    print("\nDEBUG RES:", res)
    assert res["success"] is True
    # Inspeciona o prompt passado para Edith
    call_args = runner_edith.run.call_args[0][0]
    assert "ONDA INTERMEDIÁRIA 'ONDA-001'" in call_args
    assert (
        "NÃO reprove nem bloqueie esta onda por falta de módulos ou funcionalidades que estão formalmente agendadas para as ondas futuras"
        in call_args
    )


def test_orchestrator_validate_final_wave_prompt(tmp_path: Path):
    docs_dir = tmp_path / "docs" / "briefings"
    docs_dir.mkdir(parents=True)
    (docs_dir / "PRD.md").write_text(SAMPLE_PRD_WITH_SEQUENCER, encoding="utf-8")
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")

    orch = WaveOrchestrator(project_dir=tmp_path)
    orch.state_machine.wave_id = "ONDA-003"  # Onda final
    orch.state_machine._current_state = WaveState.VALIDATE

    runner_edith = MagicMock()
    runner_edith.run.return_value = MagicMock(
        success=True,
        is_blocked=False,
        output="Homologação: APROVADO",
        block_reason=None,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_ms=200,
    )
    runner_nina = MagicMock()
    runner_nina.run.return_value = MagicMock(
        success=True,
        is_blocked=False,
        output="Governança: APROVADO",
        block_reason=None,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_ms=200,
    )

    def mock_get_runner(handle: str):
        if handle == "@edith":
            return runner_edith
        if handle == "@nina":
            return runner_nina
        return None

    orch._get_runner = mock_get_runner

    res = orch.run_validate()

    assert res["success"] is True
    call_args = runner_edith.run.call_args[0][0]
    assert "ONDA FINAL DE RELEASE ('ONDA-003')" in call_args
    assert "audite o entregável integrado completo contra TODOS os requisitos" in call_args
