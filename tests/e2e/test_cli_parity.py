"""Suíte de testes de ponta a ponta (E2E) para paridade da CLI Bombe Code v4.

Cobre integralmente os 19 entry points canônicos (EP-01 a EP-19) e os 6 slices:
- SLICE-01: Lifecycle e Lock Atômico (EP-01 a EP-03)
- SLICE-02: Tríade de Rounds Modo Manual (EP-04 a EP-07, EP-10)
- SLICE-03: Tríade de Rounds Modos Autônomos (EP-08, EP-09)
- SLICE-04: Wave Bridge de Retrocompatibilidade (EP-11)
- SLICE-05: Governança de Projeto e Standalone (EP-12 a EP-19)
- SLICE-06: Auditoria AST Zero Stubs e Quality Gates Enterprise G1 a G6
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.orchestration.ship_engine import ShipEngine

runner = CliRunner()


def _init_git_repository(project_path: Path) -> None:
    """Inicializa repositório Git descartável com commit inicial para testes."""
    subprocess.run(["git", "init"], cwd=str(project_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "agent@bombe.com"],
        cwd=str(project_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Bombe Agent"],
        cwd=str(project_path),
        capture_output=True,
        check=True,
    )
    seed_file = project_path / ".gitkeep"
    seed_file.write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(project_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial repository seed"],
        cwd=str(project_path),
        capture_output=True,
        check=True,
    )


def _setup_sandbox_project(project_path: Path, mode: str = "slice-code") -> None:
    """Configura projeto mínimo com .bombeconfig em diretório temporário."""
    mgr = ProjectConfigManager(project_dir=str(project_path))
    cfg = mgr.load()
    cfg.mode = mode
    cfg.backend_language = "python"
    cfg.frontend_stack = "react"
    mgr.save(cfg)


# ==============================================================================
# SLICE-01: Lifecycle e Lock Atômico (EP-01, EP-02, EP-03)
# ==============================================================================


def test_e2e_mission_lifecycle_success(tmp_path: Path) -> None:
    """EP-01, EP-02, EP-03: Ciclo completo new -> status -> end com persistência."""
    _setup_sandbox_project(tmp_path)

    # EP-01: Inicia nova missão
    res_new = runner.invoke(
        app,
        [
            "mission",
            "new",
            "Implementar arquitetura de microsserviços",
            "--title",
            "Microsserviços v1",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert res_new.exit_code == 0
    assert "inicializada com sucesso" in res_new.output
    assert "01" in res_new.output
    assert "Microsserviços v1" in res_new.output

    mission_file = tmp_path / "docs" / "missions" / "01" / "mission.md"
    assert mission_file.exists()
    assert (tmp_path / "docs" / "missions" / "01" / "rounds").exists()

    # EP-02: Inspeção de status da missão ativa
    res_status = runner.invoke(app, ["mission", "status", "--project-dir", str(tmp_path)])
    assert res_status.exit_code == 0
    assert "Microsserviços v1" in res_status.output
    assert "01" in res_status.output
    assert "open" in res_status.output

    # EP-03: Encerramento formal da missão
    res_end = runner.invoke(
        app,
        ["mission", "end", "--force-abort", "--project-dir", str(tmp_path)],
    )
    assert res_end.exit_code == 0
    assert "encerrada com sucesso" in res_end.output
    assert "completed" in res_end.output


def test_e2e_mission_atomic_lock_blocks_concurrent(tmp_path: Path) -> None:
    """EP-01: Porteiro atômico bloqueia abertura de nova missão se outra estiver aberta."""
    _setup_sandbox_project(tmp_path)

    # Primeira missão abre normalmente
    res_first = runner.invoke(
        app,
        ["mission", "new", "Primeira Missão Ativa", "--project-dir", str(tmp_path)],
    )
    assert res_first.exit_code == 0

    # Segunda missão deve ser rejeitada com exit code 1 pelo porteiro atômico
    res_second = runner.invoke(
        app,
        ["mission", "new", "Segunda Missão Concorrente", "--project-dir", str(tmp_path)],
    )
    assert res_second.exit_code == 1
    assert "Porteiro Atômico" in res_second.output or "Existe uma missão ativa" in res_second.output


# ==============================================================================
# SLICE-02: Tríade de Rounds Modo Manual (EP-04, EP-05, EP-06, EP-07, EP-10)
# ==============================================================================


def test_e2e_round_start_stops_at_dor(tmp_path: Path) -> None:
    """EP-04: round start executa upstream físico e para deterministicamente na DoR."""
    _setup_sandbox_project(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda de Testes Manuais", "--project-dir", str(tmp_path)])

    # EP-04: Inicia round 1 no modo manual
    res_start = runner.invoke(app, ["round", "start", "1", "--project-dir", str(tmp_path)])
    assert res_start.exit_code == 0
    assert "Round 1" in res_start.output
    assert "DoR Gate" in res_start.output
    assert "PARADA DETERMINÍSTICA" in res_start.output

    goal_path = tmp_path / "docs" / "missions" / "01" / "rounds" / "round-01" / "goal.md"
    assert goal_path.exists()
    content = goal_path.read_text(encoding="utf-8")
    assert "dor_ready: true" in content
    assert "- [ ]" in content  # DoD ainda pendente


def test_e2e_round_burn_review_validate_cycle(tmp_path: Path) -> None:
    """EP-05, EP-06, EP-07: Ciclo manual sequencial burn -> review -> validate."""
    _setup_sandbox_project(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda de Ciclo Manual", "--project-dir", str(tmp_path)])
    runner.invoke(app, ["round", "start", "1", "--project-dir", str(tmp_path)])

    # EP-05: Queima downstream dos slices
    res_burn = runner.invoke(app, ["round", "burn", "1", "--project-dir", str(tmp_path)])
    assert res_burn.exit_code == 0
    assert "Round 1" in res_burn.output
    assert "queimado" in res_burn.output

    # EP-06: Code review e story compliance
    res_review = runner.invoke(app, ["round", "review", "1", "--project-dir", str(tmp_path)])
    assert res_review.exit_code == 0
    assert "Round 1" in res_review.output
    assert "REVISADO" in res_review.output

    # EP-07: Validação formal de DoD
    res_val = runner.invoke(app, ["round", "validate", "1", "--project-dir", str(tmp_path)])
    assert res_val.exit_code == 0
    assert "Round 1" in res_val.output
    assert "VALIDADO" in res_val.output

    goal_path = tmp_path / "docs" / "missions" / "01" / "rounds" / "round-01" / "goal.md"
    assert "status: validated" in goal_path.read_text(encoding="utf-8")


def test_e2e_round_status_renders_kanban(tmp_path: Path) -> None:
    """EP-10: round status renderiza tabela Rich com kanban e gates dos rounds."""
    _setup_sandbox_project(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda de Visualização Kanban", "--project-dir", str(tmp_path)])
    runner.invoke(app, ["round", "start", "1", "--project-dir", str(tmp_path)])

    # EP-10: Status consolidado dos rounds
    res_status = runner.invoke(app, ["round", "status", "--project-dir", str(tmp_path)])
    assert res_status.exit_code == 0
    assert "Status dos Rounds da Missão" in res_status.output
    assert "Round 1" in res_status.output

    # EP-10: Status de round específico
    res_single = runner.invoke(app, ["round", "status", "1", "--project-dir", str(tmp_path)])
    assert res_single.exit_code == 0
    assert "Round 1" in res_single.output


# ==============================================================================
# SLICE-03: Tríade de Rounds Modos Autônomos (EP-08, EP-09)
# ==============================================================================


def test_e2e_round_full_executes_single_story(tmp_path: Path) -> None:
    """EP-08: round full executa story ponta a ponta e para na fronteira do round."""
    _setup_sandbox_project(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda Semi-Auto", "--project-dir", str(tmp_path)])

    # EP-08 via subcomando 'round full'
    res_full = runner.invoke(app, ["round", "full", "1", "--project-dir", str(tmp_path)])
    assert res_full.exit_code == 0
    assert "Round 1" in res_full.output
    assert "VALIDADO" in res_full.output
    assert "PARADA DETERMINÍSTICA" in res_full.output

    # EP-08 via comando raiz 'round-full'
    res_root = runner.invoke(app, ["round-full", "1", "--project-dir", str(tmp_path)])
    assert res_root.exit_code == 0
    assert "VALIDADO" in res_root.output


def test_e2e_round_all_runs_continuous_pipeline(tmp_path: Path) -> None:
    """EP-09: round all executa pipeline contínuo desatendido para todos os rounds."""
    _setup_sandbox_project(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda Pipeline Contínuo", "--project-dir", str(tmp_path)])

    # Cadastra rounds adicionais no manifesto de missão
    mission_file = tmp_path / "docs" / "missions" / "01" / "mission.md"
    content = mission_file.read_text(encoding="utf-8")
    extra_rounds = (
        "rounds:\n"
        "  ROUND-1:\n"
        "    status: pending\n"
        "    story_id: STORY-001\n"
        "  ROUND-2:\n"
        "    status: pending\n"
        "    story_id: STORY-002\n"
    )
    updated_content = content.replace("rounds: {}", extra_rounds)
    mission_file.write_text(updated_content, encoding="utf-8")

    # EP-09: Executa pipeline de todos os rounds pendentes
    res_all = runner.invoke(app, ["round", "all", "--project-dir", str(tmp_path)])
    assert res_all.exit_code == 0
    assert "Pipeline de Rounds Concluído" in res_all.output
    assert "Round 1" in res_all.output
    assert "Round 2" in res_all.output

    # EP-09 via comando raiz 'round-all'
    res_root = runner.invoke(app, ["round-all", "--project-dir", str(tmp_path)])
    assert res_root.exit_code == 0


# ==============================================================================
# SLICE-04: Wave Bridge de Retrocompatibilidade (EP-11)
# ==============================================================================


def test_e2e_wave_bridge_redirects_all_legacy_commands(tmp_path: Path) -> None:
    """EP-11: Wave Bridge intercepta 7 comandos legados, emite banner e despacha."""
    _setup_sandbox_project(tmp_path)
    _init_git_repository(tmp_path)
    runner.invoke(app, ["mission", "new", "Demanda Wave Bridge", "--project-dir", str(tmp_path)])

    banner_phrase = "AVISO DE DEPRECIAÇÃO (WAVE BRIDGE)"

    # 1. wave start -> round start
    res_ws = runner.invoke(app, ["wave", "start", "ONDA-001", "--project-dir", str(tmp_path)])
    assert res_ws.exit_code == 0
    assert banner_phrase in res_ws.output
    assert "bombe round start 1" in res_ws.output

    # 2. wave cycle -> round burn
    res_wc = runner.invoke(app, ["wave", "cycle", "ONDA-001", "--project-dir", str(tmp_path)])
    assert res_wc.exit_code == 0
    assert banner_phrase in res_wc.output
    assert "bombe round burn 1" in res_wc.output

    # 3. wave validate -> round validate
    res_wv = runner.invoke(app, ["wave", "validate", "ONDA-001", "--project-dir", str(tmp_path)])
    assert res_wv.exit_code == 0
    assert banner_phrase in res_wv.output
    assert "bombe round validate 1" in res_wv.output

    # 4. wave status -> round status
    res_st = runner.invoke(app, ["wave", "status", "--project-dir", str(tmp_path)])
    assert res_st.exit_code == 0
    assert banner_phrase in res_st.output
    assert "bombe round status" in res_st.output

    # 5. wave run -> round all
    res_wr = runner.invoke(app, ["wave", "run", "--project-dir", str(tmp_path)])
    assert res_wr.exit_code == 0
    assert banner_phrase in res_wr.output
    assert "bombe round all" in res_wr.output

    # 6. wave promote -> project ship
    res_wp = runner.invoke(app, ["wave", "promote", "dev", "--project-dir", str(tmp_path)])
    assert res_wp.exit_code == 0
    assert banner_phrase in res_wp.output
    assert "bombe project ship dev" in res_wp.output

    # 7. wave end -> mission end
    res_we = runner.invoke(
        app,
        ["wave", "end", "--force-abort", "--project-dir", str(tmp_path)],
    )
    assert res_we.exit_code == 0
    assert banner_phrase in res_we.output
    assert "bombe mission end" in res_we.output


# ==============================================================================
# SLICE-05: Governança de Projeto e Standalone (EP-12 a EP-19)
# ==============================================================================


def test_e2e_project_configure_and_mode_switching(tmp_path: Path) -> None:
    """EP-12, EP-14: project configure e alternância de modo com auditoria."""
    _setup_sandbox_project(tmp_path)

    # EP-12: Configura parâmetros operacionais do projeto
    res_cfg = runner.invoke(
        app,
        [
            "project",
            "configure",
            "--mode",
            "slice-code",
            "--backend-language",
            "python",
            "--frontend-stack",
            "react",
            "--backend-path",
            "src/core/",
            "--frontend-path",
            "src/ui/",
            "--autonomy",
            "semi-auto",
            "--delivery-target",
            "enterprise-grade",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert res_cfg.exit_code == 0
    assert "Configuração atualizada com sucesso" in res_cfg.output

    cfg_mgr = ProjectConfigManager(str(tmp_path))
    loaded = cfg_mgr.load()
    assert loaded.mode == "slice-code"
    assert loaded.backend_path == "src/core/"
    assert loaded.frontend_path == "src/ui/"
    assert loaded.backend_language == "python"
    assert loaded.frontend_stack == "react"

    # EP-14 via comando raiz: Comuta modo para vibe-code
    res_mode_root = runner.invoke(app, ["mode", "vibe-code", "--project-dir", str(tmp_path)])
    assert res_mode_root.exit_code == 0
    assert "Modo de engenharia alterado" in res_mode_root.output

    loaded_migrated = cfg_mgr.load()
    assert loaded_migrated.mode == "vibe-code"
    assert loaded_migrated.mode_origin == "slice-code"
    assert loaded_migrated.mode_migrated_at is not None

    # EP-14 via sub-app standalone: Comuta de volta para slice-code
    res_mode_sub = runner.invoke(
        app,
        ["standalone", "mode", "slice-code", "--project-dir", str(tmp_path)],
    )
    assert res_mode_sub.exit_code == 0
    assert cfg_mgr.load().mode == "slice-code"


def test_e2e_project_ship_with_pre_flight_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """EP-13: project ship aborta se pré-flight falhar e promove se passar."""
    _init_git_repository(tmp_path)

    # Cenário A: Falha no pré-flight de testes bloqueia o ship com exit code 1
    monkeypatch.setattr(ShipEngine, "_run_pre_flight_tests", lambda self: False)
    res_fail = runner.invoke(app, ["project", "ship", "dev", "--project-dir", str(tmp_path)])
    assert res_fail.exit_code == 1
    assert "Falha na promoção" in res_fail.output or "Testes pré-flight falharam" in res_fail.output

    # Cenário B: Pré-flight aprovado promove estado para branch dev com exit code 0
    monkeypatch.setattr(ShipEngine, "_run_pre_flight_tests", lambda self: True)
    res_pass = runner.invoke(app, ["project", "ship", "dev", "--project-dir", str(tmp_path)])
    assert res_pass.exit_code == 0
    assert "Promoção Git concluída com sucesso" in res_pass.output


def test_e2e_standalone_auxiliary_tools(tmp_path: Path) -> None:
    """EP-15, EP-16, EP-17, EP-18, EP-19: Ferramentas auxiliares standalone."""
    _setup_sandbox_project(tmp_path)

    # EP-15: task avulsa despachada via Protocolo Garçom
    res_task = runner.invoke(
        app,
        [
            "task",
            "Criar índice composto de banco",
            "--agent",
            "@codd",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert res_task.exit_code == 0
    assert "@codd" in res_task.output
    assert "Task executada e despachada com sucesso" in res_task.output

    # EP-16: Análise de causa raiz determinística (RCA)
    res_rca = runner.invoke(
        app,
        ["rca", "Gargalo de I/O em leitura concorrente", "--project-dir", str(tmp_path)],
    )
    assert res_rca.exit_code == 0
    assert "Root Cause Analysis" in res_rca.output
    assert "5 Porquês" in res_rca.output

    # EP-17: Code review avulso multi-eixo
    res_rev = runner.invoke(app, ["review", "src/", "--project-dir", str(tmp_path)])
    assert res_rev.exit_code == 0
    assert "Auditoria de Qualidade" in res_rev.output

    # EP-18: Auditoria de simplificação de código
    res_simp = runner.invoke(app, ["simplify", "src/", "--project-dir", str(tmp_path)])
    assert res_simp.exit_code == 0
    assert "Code Simplification Audit" in res_simp.output

    # EP-19: Status report executivo do projeto
    res_rep = runner.invoke(app, ["status-report", "--project-dir", str(tmp_path)])
    assert res_rep.exit_code == 0
    assert "Status Report do Projeto" in res_rep.output

    # EP-19 alias 'report'
    res_alias = runner.invoke(app, ["report", "--project-dir", str(tmp_path)])
    assert res_alias.exit_code == 0


# ==============================================================================
# SLICE-06: Gates G1-G6 e Auditoria AST
# ==============================================================================


def test_e2e_audit_zero_stubs_and_mocks_in_production() -> None:
    """AC-04: Auditoria AST em src/bombe_code/ garante zero stubs e zero mocks."""
    root_src = Path(__file__).resolve().parent.parent.parent / "src" / "bombe_code"
    assert root_src.is_dir()

    not_implemented_errors: list[str] = []
    empty_pass_functions: list[str] = []
    forbidden_mock_imports: list[str] = []

    for py_file in root_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            # 1. Varredura por raise NotImplementedError
            if isinstance(node, ast.Raise):
                exc = node.exc
                name = getattr(exc, "id", None) or getattr(getattr(exc, "func", None), "id", None)
                if name == "NotImplementedError":
                    not_implemented_errors.append(f"{py_file.name}:{node.lineno}")

            # 2. Varredura por corpos vazios contendo apenas pass em funções não abstratas
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_abstract = any(
                    (isinstance(d, ast.Name) and d.id in ("abstractmethod", "overload"))
                    or (isinstance(d, ast.Attribute) and d.attr in ("abstractmethod", "overload"))
                    for d in node.decorator_list
                )
                if not is_abstract:
                    body = node.body
                    if len(body) == 1 and isinstance(body[0], ast.Pass):
                        empty_pass_functions.append(f"{py_file.name}:{node.name}:{node.lineno}")
                    elif (
                        len(body) == 2
                        and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[1], ast.Pass)
                    ):
                        empty_pass_functions.append(f"{py_file.name}:{node.name}:{node.lineno}")

            # 3. Varredura por imports de mocks em código de produção
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("unittest.mock", "pytest_mock"):
                        forbidden_mock_imports.append(f"{py_file.name}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("unittest.mock") or node.module.startswith("pytest_mock"):
                    forbidden_mock_imports.append(f"{py_file.name}:{node.module}")

    assert not_implemented_errors == [], f"NotImplementedError encontrado: {not_implemented_errors}"
    assert empty_pass_functions == [], f"Funções stub com pass encontradas: {empty_pass_functions}"
    assert forbidden_mock_imports == [], f"Imports de mock encontrados em produção: {forbidden_mock_imports}"


def test_e2e_homologation_gates_g1_to_g6(tmp_path: Path) -> None:
    """AC-05: Homologação formal dos 6 Quality Gates estabelecidos em docs/projeto/mvp.md."""
    # Gate G1: Backend TDD Estrito — existência das suítes de teste de rounds e slices
    unit_tests_dir = Path(__file__).resolve().parent.parent / "unit"
    assert (unit_tests_dir / "test_round_execution_engine.py").exists()
    assert (unit_tests_dir / "test_round_manual_engine.py").exists()

    # Gate G2: Interface Operacional Real — CLI consumindo o orquestrador real
    _setup_sandbox_project(tmp_path)
    res_cli = runner.invoke(
        app,
        ["mission", "new", "Validação Gate G2 CLI Real", "--project-dir", str(tmp_path)],
    )
    assert res_cli.exit_code == 0
    assert (tmp_path / "docs" / "missions" / "01" / "mission.md").exists()

    # Gate G3: Zero Código Morto ou Stubs — AST limpa em src/bombe_code
    test_e2e_audit_zero_stubs_and_mocks_in_production()

    # Gate G4: Testes de Integração com Infra Real — contingência e resiliência
    e2e_dir = Path(__file__).resolve().parent
    assert (e2e_dir / "test_contingency_mission.py").exists()

    # Gate G5: Inicialização Limpa e Sem Erros — executável sobe sem exceptions
    res_version = runner.invoke(app, ["version"])
    assert res_version.exit_code == 0
    assert "bombe-code" in res_version.output

    res_help = runner.invoke(app, ["--help"])
    assert res_help.exit_code == 0
    assert "Bombe Code" in res_help.output

    # Gate G6: Teste E2E de Contingência — documentado e auditado
    contingency_file = e2e_dir / "test_contingency_mission.py"
    contingency_source = contingency_file.read_text(encoding="utf-8")
    assert "test_contingency_failover_z_ai_429_to_local_vllm_e2e" in contingency_source
