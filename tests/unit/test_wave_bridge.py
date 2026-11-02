"""Tests for Wave Bridge and Deprecation Interceptor."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from bombe_code.cli.commands.wave_bridge import (
    parse_wave_id_to_round_num,
    render_wave_deprecation_banner,
    wave_app,
)
from bombe_code.domain.contracts.wave_bridge import (
    LegacyWaveCommand,
    WaveBridgeRedirect,
)


def _scaffold_mock_mission(base_dir: Path) -> Path:
    """Helper to create a realistic mock mission structure in base_dir."""
    mission_dir = base_dir / "docs" / "missions" / "01"
    rounds_dir = mission_dir / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)

    mission_content = (
        "---\n"
        "id: MISSION-01\n"
        "rounds:\n"
        "  ROUND-1:\n"
        "    status: validated\n"
        "    story_id: STORY-001\n"
        "  ROUND-2:\n"
        "    status: pending\n"
        "    story_id: STORY-002\n"
        "---\n\n"
        "# MISSION-01\n"
    )
    (mission_dir / "mission.md").write_text(mission_content, encoding="utf-8")

    r1_dir = rounds_dir / "round-01"
    r1_dir.mkdir(parents=True, exist_ok=True)
    r1_goal = (
        "---\nround: 1\nstatus: done\n---\n"
        "## Checklist de Definition of Done (DoD)\n"
        "- [x] Task 1 completed\n"
    )
    (r1_dir / "goal.md").write_text(r1_goal, encoding="utf-8")
    return mission_dir


def test_legacy_wave_command_enum_values() -> None:
    """Verifica todos os comandos legados suportados no enum."""
    assert LegacyWaveCommand.START == "start"
    assert LegacyWaveCommand.RUN == "run"
    assert LegacyWaveCommand.CYCLE == "cycle"
    assert LegacyWaveCommand.VALIDATE == "validate"
    assert LegacyWaveCommand.STATUS == "status"
    assert LegacyWaveCommand.PROMOTE == "promote"
    assert LegacyWaveCommand.END == "end"


def test_wave_bridge_redirect_pydantic_v2_strict() -> None:
    """Valida imutabilidade, proibição de campos extras e tipos estritos."""
    redirect = WaveBridgeRedirect(
        legacy_command=LegacyWaveCommand.START,
        canonical_command="bombe round start",
        target_subapp="round",
        explanation="O conceito de ONDA foi substituído por ROUNDS no Bombe Core v4.",
    )
    assert redirect.legacy_command == LegacyWaveCommand.START
    assert redirect.canonical_command == "bombe round start"
    assert redirect.target_subapp == "round"
    assert redirect.deprecated is True
    assert "ROUNDS" in redirect.explanation

    # Imutabilidade (frozen)
    with pytest.raises(ValidationError):
        redirect.canonical_command = "other"  # type: ignore[misc]

    # Forbid extra fields
    with pytest.raises(ValidationError):
        WaveBridgeRedirect(
            legacy_command=LegacyWaveCommand.RUN,
            canonical_command="bombe round all",
            target_subapp="round",
            explanation="Test",
            extra_field="invalido",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("raw_input", "expected_round"),
    [
        ("ONDA-001", 1),
        ("ONDA-002", 2),
        ("onda-10", 10),
        ("WAVE-003", 3),
        ("1", 1),
        ("5", 5),
        (2, 2),
        (None, 1),
        ("", 1),
        ("invalido_sem_numero", 1),
    ],
)
def test_parse_wave_id_to_round_num(raw_input: str | int | None, expected_round: int) -> None:
    """Verifica extração correta de número inteiro de round a partir de wave_id."""
    assert parse_wave_id_to_round_num(raw_input) == expected_round


def test_render_wave_deprecation_banner(capsys: pytest.CaptureFixture[str]) -> None:
    """Verifica que o banner educativo de depreciação é renderizado com rich."""
    render_wave_deprecation_banner(
        legacy_cmd="bombe wave start",
        canonical_cmd="bombe round start",
    )
    captured = capsys.readouterr()
    # Verifica menções essenciais no banner Rich impresso no terminal
    combined = captured.out + captured.err
    assert "ONDA" in combined
    assert "ROUND" in combined
    assert "bombe round start" in combined


def test_cli_wave_start_intercepts_and_runs_round_start(tmp_path: Path) -> None:
    """Verifica se bombe wave start exibe banner e executa round-start com sucesso."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()
    result = runner.invoke(wave_app, ["start", "ONDA-002", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe round start 2" in result.stdout
    assert "Round 2" in result.stdout


def test_cli_wave_cycle_intercepts_and_runs_round_burn(tmp_path: Path) -> None:
    """Verifica se bombe wave cycle exibe banner e despacha para round-burn."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()
    # Primeiro inicia o round 2 para que haja DoR
    runner.invoke(wave_app, ["start", "2", "--project-dir", str(tmp_path)])

    result = runner.invoke(wave_app, ["cycle", "2", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe round burn 2" in result.stdout
    assert "queimado" in result.stdout.lower() or "burn" in result.stdout.lower()


def test_cli_wave_validate_intercepts_and_runs_round_validate(tmp_path: Path) -> None:
    """Verifica se bombe wave validate exibe banner e despacha para round-validate."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()
    runner.invoke(wave_app, ["start", "2", "--project-dir", str(tmp_path)])
    runner.invoke(wave_app, ["cycle", "2", "--project-dir", str(tmp_path)])

    result = runner.invoke(wave_app, ["validate", "2", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe round validate 2" in result.stdout
    assert "validado" in result.stdout.lower() or "dod" in result.stdout.lower()


def test_cli_wave_status_intercepts_and_runs_round_status(tmp_path: Path) -> None:
    """Verifica se bombe wave status exibe banner e tabela de rounds."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()
    runner.invoke(wave_app, ["start", "2", "--project-dir", str(tmp_path)])

    result = runner.invoke(wave_app, ["status", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe round status" in result.stdout
    assert "ROUND" in result.stdout.upper()


def test_cli_wave_run_intercepts_and_runs_round_all(tmp_path: Path) -> None:
    """Verifica se bombe wave run exibe banner e executa pipeline de rounds."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()
    result = runner.invoke(wave_app, ["run", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe round all" in result.stdout


def test_cli_wave_end_intercepts_and_runs_mission_end(tmp_path: Path) -> None:
    """Verifica se bombe wave end exibe banner e despacha para mission end."""
    from bombe_code.cli.commands.mission import mission_app

    runner = CliRunner()
    runner.invoke(
        mission_app,
        ["new", "Missão legada para teste de encerramento", "--project-dir", str(tmp_path)],
    )

    result = runner.invoke(
        wave_app,
        ["end", "--project-dir", str(tmp_path), "--force-abort"],
    )
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe mission end" in result.stdout
    assert "encerrada" in result.stdout.lower() or "concluída" in result.stdout.lower()


def test_cli_wave_promote_intercepts_and_renders_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica se bombe wave promote exibe banner e despacha promoção."""
    from bombe_code.turing.promocao import PromotorDeBranches, ResultadoPromocao

    def mock_promover_para_dev(self: PromotorDeBranches, msg: str) -> ResultadoPromocao:
        return ResultadoPromocao(
            success=True,
            acao="promover_dev",
            mensagem="Promoção para dev simulada com sucesso",
            detalhes=["merge squash ok"],
        )

    monkeypatch.setattr(PromotorDeBranches, "promover_para_dev", mock_promover_para_dev)

    runner = CliRunner()
    result = runner.invoke(wave_app, ["promote", "dev", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "AVISO DE DEPRECIAÇÃO" in result.stdout
    assert "bombe project ship dev" in result.stdout
    assert "Promoção para dev simulada com sucesso" in result.stdout


def test_main_cli_registers_wave_app() -> None:
    """Verifica que o CLI principal (bombe) registra wave_app sob o comando wave."""
    from bombe_code.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["wave", "--help"])
    assert result.exit_code == 0
    assert "Ponte de retrocompatibilidade para comandos legados de ondas" in result.stdout


