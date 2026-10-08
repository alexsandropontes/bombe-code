"""Higiene de ciclo: a PLATAFORMA remove resíduos físicos (tmp_*, *.tmp,
*.snippet*, scratch, X.script.vue) — o modelo não tem delete (só read/write/
list), então gates de higiene (G1) nunca convergiriam: o modelo "neutraliza"
o conteúdo, o arquivo continua lá, o gate reprova de novo — loop infinito."""

from pathlib import Path

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    return tmp_path, db


def _orch(tmp_path: Path, db: ProjectDatabase) -> WaveOrchestrator:
    (tmp_path / "app.py").write_text("def app() -> str:\n    return 'ok'\n", encoding="utf-8")
    return WaveOrchestrator(project_dir=str(tmp_path), db=db)


def test_remove_residuos_e_preserva_fonte(tmp_path: Path, project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    residuos = [
        "tmp_st305_append.txt",
        ".tmp_jobs_e302.py",
        "z.tmp",
        "src/a.snippet.py",
        "main._import_snippet",
        "src/components/Comp.script.vue",
        "anotacoes scratch.md",
    ]
    for r in residuos:
        p = tmp_path / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    (tmp_path / ".bombe-code").mkdir(exist_ok=True)
    (tmp_path / ".bombe-code" / "banco.db").write_text("db", encoding="utf-8")

    removidos = orch._higienizar_residuos()

    assert set(removidos) == set(residuos)
    assert (tmp_path / "app.py").exists()
    assert (tmp_path / ".bombe-code" / "banco.db").exists()


def test_nao_desce_em_node_modules(tmp_path: Path, project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    lixo = tmp_path / "node_modules" / "tmp_pacote.js"
    lixo.parent.mkdir(parents=True)
    lixo.write_text("x", encoding="utf-8")

    removidos = orch._higienizar_residuos()

    assert removidos == []
    assert lixo.exists()


def test_ciclo_higieniza_a_arvore_antes_do_trabalho(tmp_path: Path, project_env):
    """Cada história começa com a árvore limpa — o review nunca reprova por
    resíduo que o modelo não consegue apagar."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-001", title="S1", agent="@valim", status="IN_PROGRESS"
    )
    lixo = tmp_path / "tmp_residuo.py"
    lixo.write_text("x", encoding="utf-8")

    orch._run_cycle_inner = lambda story_id=None, rework_feedback=None: {
        "success": True,
        "message": "ok",
    }

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True
    assert not lixo.exists()
