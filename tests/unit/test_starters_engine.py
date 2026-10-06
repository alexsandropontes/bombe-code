"""Testes unitários para o motor de Starters do Bombe Code (ST-023, ST-024).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

from bombe_code.starters.engine import StarterEngine


def test_list_starters():
    engine = StarterEngine()
    starters = engine.list_starters()
    assert len(starters) >= 4

    ids = [s["id"] for s in starters]
    assert "python-fastapi-clean" in ids
    assert "go-gin-clean" in ids
    assert "node-ts-clean" in ids
    assert "react-tailwind-clean" in ids


def test_apply_starter_success(tmp_path: Path):
    target_dir = tmp_path / "meu_projeto"
    target_dir.mkdir()

    engine = StarterEngine()
    result = engine.apply_starter(
        "python-fastapi-clean", target_dir=str(target_dir), project_name="meu-app"
    )

    assert result["success"] is True
    assert (target_dir / "pyproject.toml").is_file()
    assert (target_dir / "src" / "main.py").is_file()
    assert (target_dir / "tests" / "test_health.py").is_file()
    assert (target_dir / ".bombeconfig").is_file()

    # Confirma conteúdo customizado com o nome do projeto
    pyproject_content = (target_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert "meu-app" in pyproject_content


def test_apply_starter_dirty_directory_veto(tmp_path: Path):
    dirty_dir = tmp_path / "dirty"
    dirty_dir.mkdir()
    (dirty_dir / "arquivo_existente.txt").write_text("conteúdo antigo", encoding="utf-8")

    engine = StarterEngine()
    result = engine.apply_starter("python-fastapi-clean", target_dir=str(dirty_dir), force=False)

    assert result["success"] is False
    assert "Diretório não está vazio" in result["error"]
    assert (dirty_dir / "arquivo_existente.txt").exists()


def test_apply_starter_not_found(tmp_path: Path):
    engine = StarterEngine()
    result = engine.apply_starter("starter-inexistente", target_dir=str(tmp_path))
    assert result["success"] is False
    assert "não encontrado" in result["error"]


def test_list_all_38_catalog_starters():
    """Valida se todos os 38 starters do catálogo oficial são descobertos e carregados."""
    engine = StarterEngine()
    starters = engine.list_starters()
    # 38 do catálogo oficial + 4 builtins
    assert len(starters) >= 38

    ids = {s["id"] for s in starters}
    # Checa amostras representativas de cada categoria
    assert "python-mono" in ids
    assert "python-mono-backend" in ids
    assert "dotnet-multi-logical" in ids
    assert "go-multi-physical" in ids
    assert "spring-mono" in ids
    assert "react-portal" in ids
    assert "chatbot-py-streamlit" in ids
    assert "whatsapp-bff-go" in ids


def test_apply_composed_fullstack_starter(tmp_path: Path):
    """Valida scaffolding de starter fullstack composto (python-mono: backend + react-portal)."""
    target = tmp_path / "fullstack_app"
    engine = StarterEngine()
    res = engine.apply_starter("python-mono", target_dir=str(target), project_name="FullstackApp")

    assert res["success"] is True
    assert (target / ".bombeconfig").is_file()
    assert (target / "src" / "backend" / "main.py").is_file()
    assert (target / "src" / "frontend" / "package.json").is_file()
    assert (target / "src" / "run.sh").is_file() or (target / "run.sh").is_file()


def test_apply_chatbot_starter(tmp_path: Path):
    """Valida scaffolding de chatbot Streamlit (chatbot-py-streamlit)."""
    target = tmp_path / "chatbot_app"
    engine = StarterEngine()
    res = engine.apply_starter("chatbot-py-streamlit", target_dir=str(target), project_name="MyBot")

    assert res["success"] is True
    assert (target / ".bombeconfig").is_file()
    assert (target / "src" / "backend" / "app" / "main.py").is_file() or (
        target / "backend" / "app" / "main.py"
    ).is_file()
    assert (target / "src" / "frontend" / "app.py").is_file() or (
        target / "frontend" / "app.py"
    ).is_file()


def test_apply_backend_blueprint_starter(tmp_path: Path):
    """Valida scaffolding de backend Go (go-mono-backend)."""
    target = tmp_path / "go_backend"
    engine = StarterEngine()
    res = engine.apply_starter("go-mono-backend", target_dir=str(target), project_name="GoServer")

    assert res["success"] is True
    assert (target / ".bombeconfig").is_file()
    assert (target / "src" / "backend" / "main.go").is_file()
