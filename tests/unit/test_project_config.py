"""Testes para o gerenciador de configuração do projeto (.bombeconfig) (ST-019).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

from bombe_code.config.project_config import ProjectConfig, ProjectConfigManager


def test_project_config_defaults(tmp_path: Path):
    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = mgr.load()

    assert cfg.name == tmp_path.name or cfg.name == "bombe-project"
    assert cfg.mode in ("tdd-code", "vibe-code")
    assert cfg.autonomy in ("auto", "semi-auto", "manual")


def test_project_config_save_and_load(tmp_path: Path):
    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = ProjectConfig(
        name="finance-core",
        type="api",
        backend_language="python",
        frontend_stack="none",
        root_src="src/",
        backend_path="src/api/",
        frontend_path="src/ui/",
        docs_root="docs/",
        branch="dev-ia",
        mode="tdd-code",
        autonomy="manual",
    )
    mgr.save(cfg)

    # Confirma que o arquivo .bombeconfig foi criado fisicamente
    assert (tmp_path / ".bombeconfig").is_file()

    loaded = mgr.load()
    assert loaded.name == "finance-core"
    assert loaded.backend_language == "python"
    assert loaded.autonomy == "manual"
    assert loaded.branch == "dev-ia"


def test_project_config_autodetect_python(tmp_path: Path):
    # Cria arquivo pyproject.toml para simular stack python
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test-py'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()

    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    detected = mgr.autodetect()

    assert detected.backend_language == "python"
    assert detected.root_src == "src/"
    assert detected.docs_root == "docs/"
