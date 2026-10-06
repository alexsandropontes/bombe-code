"""Testes unitários para o widget Sidebar vertical da TUI."""

from __future__ import annotations

from pathlib import Path

from bombe_code.tui.widgets.sidebar import Sidebar, _get_git_modified_files


def test_sidebar_initial_metrics(tmp_path: Path):
    sidebar = Sidebar(
        project_dir=str(tmp_path),
        session_id="ses_12345",
        session_title="Test Project",
        model="gpt-4o",
    )
    assert sidebar.session_id == "ses_12345"
    assert sidebar.session_title == "Test Project"
    assert sidebar.model_name == "gpt-4o"
    assert sidebar.can_focus is False
    assert sidebar.tokens_count == 0
    assert sidebar.cost == 0.0


def test_sidebar_update_metrics(tmp_path: Path):
    sidebar = Sidebar(project_dir=str(tmp_path), session_id="ses_abc")
    sidebar.update_metrics(tokens=1500, cost=0.045, percent=12, title="Updated Title")
    assert sidebar.tokens_count == 1500
    assert sidebar.cost == 0.045
    assert sidebar.context_percent == 12
    assert sidebar.session_title == "Updated Title"


def test_git_modified_files_non_repo(tmp_path: Path):
    files = _get_git_modified_files(tmp_path)
    assert isinstance(files, list)


def test_sidebar_renders_untracked_directories_properly(tmp_path: Path, monkeypatch):
    import subprocess

    # Simula git status retornando raízes de diretório e arquivos reais com subpastas
    def fake_run(cmd, *args, **kwargs):
        class FakeRes:
            returncode = 0
            stdout = "?? docs/\n?? src/app.py\n?? tests/unit/test_foo.py\n?? pyproject.toml\n"
            stderr = ""

        return FakeRes()

    monkeypatch.setattr(subprocess, "run", fake_run)
    files = _get_git_modified_files(tmp_path)
    # docs/ é raiz de diretório, deve ser ignorada da contagem de arquivos
    assert len(files) == 3
    file_names = [f["file"] for f in files]
    assert "docs/" not in file_names
    assert "src/app.py" in file_names
    assert "tests/unit/test_foo.py" in file_names
    assert "pyproject.toml" in file_names

    sidebar = Sidebar(project_dir=str(tmp_path), session_id="ses_abc")
    sidebar.refresh_view()
    rendered_text = sidebar._last_rendered_text.plain

    # Arquivos em subpastas mostram pasta pai / arquivo
    assert "• src/app.py" in rendered_text
    assert "• unit/test_foo.py" in rendered_text
    assert "• pyproject.toml" in rendered_text
