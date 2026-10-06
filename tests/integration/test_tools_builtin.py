"""Integration F4 tools-system — tools em filesystem/subprocess/HTTP REAL (sem mocks)."""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from bombe_code.tools.base import ToolContext
from bombe_code.tools.registry import builtin_registry, load_custom_tools

pytestmark = pytest.mark.integration


def _ctx(project_dir: Path, ask_result: str = "allow") -> ToolContext:
    return ToolContext(
        session_id="ses_teste",
        project_dir=str(project_dir),
        ask=lambda permission, details="": ask_result,
        run_subtask=lambda prompt: f"subtask:{prompt}",
    )


def test_read_de_arquivo_real(tmp_path: Path):
    alvo = tmp_path / "app.py"
    alvo.write_text("conteudo alvo\nlinha 2\n", encoding="utf-8")
    out = builtin_registry().execute("read", {"path": str(alvo)}, _ctx(tmp_path))
    assert "conteudo alvo" in out


def test_write_e_read_roundtrip(tmp_path: Path):
    registry = builtin_registry()
    alvo = tmp_path / "novo" / "arquivo.txt"
    registry.execute("write", {"path": str(alvo), "content": "escrito"}, _ctx(tmp_path))
    out = registry.execute("read", {"path": str(alvo)}, _ctx(tmp_path))
    assert "escrito" in out


def test_edit_substitui_string_exata(tmp_path: Path):
    alvo = tmp_path / "m.py"
    alvo.write_text("a = 1\nb = 2\n", encoding="utf-8")
    registry = builtin_registry()
    registry.execute(
        "edit",
        {"path": str(alvo), "old_string": "b = 2", "new_string": "b = 3"},
        _ctx(tmp_path),
    )
    assert alvo.read_text(encoding="utf-8") == "a = 1\nb = 3\n"


def test_edit_string_ausente_retorna_erro(tmp_path: Path):
    alvo = tmp_path / "m.py"
    alvo.write_text("a = 1\n", encoding="utf-8")
    out = builtin_registry().execute(
        "edit",
        {"path": str(alvo), "old_string": "nao_existe", "new_string": "x"},
        _ctx(tmp_path),
    )
    assert "nao_existe" in out


def test_glob_encontra_arquivos(tmp_path: Path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    out = builtin_registry().execute(
        "glob", {"pattern": "*.py", "path": str(tmp_path)}, _ctx(tmp_path)
    )
    assert "a.py" in out
    assert "b.txt" not in out


def test_grep_retorna_caminho_e_linha(tmp_path: Path):
    (tmp_path / "codigo.py").write_text(
        "linha um\npadrao_secreto aqui\nlinha tres\n", encoding="utf-8"
    )
    out = builtin_registry().execute(
        "grep", {"pattern": "padrao_secreto", "path": str(tmp_path)}, _ctx(tmp_path)
    )
    assert "codigo.py:2:" in out


def test_shell_executa_comando_real(tmp_path: Path):
    out = builtin_registry().execute("shell", {"command": "echo oi-do-shell"}, _ctx(tmp_path))
    assert "oi-do-shell" in out


def test_todowrite_confirma_atualizacao(tmp_path: Path):
    registry = builtin_registry()
    ctx = _ctx(tmp_path)
    out = registry.execute(
        "todowrite",
        {
            "todos": [
                {"content": "etapa 1", "status": "completed"},
                {"content": "etapa 2", "status": "pending"},
            ]
        },
        ctx,
    )
    assert "atualizados" in out.lower() or "updated" in out.lower()


def test_question_devolve_resposta_humana(tmp_path: Path):
    ctx = _ctx(tmp_path, ask_result="sim, usar postgres")
    out = builtin_registry().execute("question", {"question": "qual banco?"}, ctx)
    assert out == "sim, usar postgres"


def test_task_delega_para_subtask(tmp_path: Path):
    out = builtin_registry().execute("task", {"prompt": "cria a UI"}, _ctx(tmp_path))
    assert out == "subtask:cria a UI"


def test_skill_carrega_markdown_do_projeto(tmp_path: Path):
    skills = tmp_path / ".bombe" / "skills" / "deploy"
    skills.mkdir(parents=True)
    (skills / "deploy.md").write_text("# Deploy passo a passo\n", encoding="utf-8")
    out = builtin_registry().execute("skill", {"name": "deploy"}, _ctx(tmp_path))
    assert "Deploy passo a passo" in out


def test_webfetch_http_real_local(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html>ola web</html>", encoding="utf-8")

    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        out = builtin_registry().execute(
            "webfetch", {"url": f"http://127.0.0.1:{port}/index.html"}, _ctx(tmp_path)
        )
    finally:
        server.shutdown()
    assert "ola web" in out


def test_apply_patch_aplica_diff_unificado(tmp_path: Path):
    alvo = tmp_path / "arq.txt"
    alvo.write_text("linha1\nlinha3\n", encoding="utf-8")
    diff = "--- a/arq.txt\n+++ b/arq.txt\n@@ -1,2 +1,3 @@\n linha1\n+linha2\n linha3\n"
    registry = builtin_registry()
    registry.execute("apply_patch", {"path": str(alvo), "diff": diff}, _ctx(tmp_path))
    assert alvo.read_text(encoding="utf-8") == "linha1\nlinha2\nlinha3\n"


def test_shell_negado_recusa_executar(tmp_path: Path):
    ctx = ToolContext(
        session_id="ses_teste",
        project_dir=str(tmp_path),
        ask=lambda permission, details="": "deny",
    )
    out = builtin_registry().execute("shell", {"command": "echo ola-nunca"}, ctx)
    assert "negada" in out.lower()
    assert "ola-nunca" not in out


def test_read_fora_do_worktree_dispara_external_directory(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    fora = tmp_path / "fora.txt"
    fora.write_text("segredo", encoding="utf-8")
    asks: list[str] = []
    ctx = ToolContext(
        session_id="ses_teste",
        project_dir=str(proj),
        ask=lambda permission, details="": asks.append(permission) or "allow",
    )
    out = builtin_registry().execute("read", {"path": str(fora)}, ctx)
    assert "external_directory" in asks
    assert "segredo" in out


def test_custom_tool_py_e_md_sao_carregados(tmp_path: Path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "hello.py").write_text(
        "from pydantic import BaseModel\n"
        "from bombe_code.tools.base import ToolDef\n"
        "class Empty(BaseModel):\n"
        "    pass\n"
        "TOOL = ToolDef(id='hello', description='diz oi', parameters=Empty,\n"
        "    execute=lambda args, ctx: 'ola do custom')\n",
        encoding="utf-8",
    )
    (tools_dir / "guia.md").write_text("conteudo do guia em markdown", encoding="utf-8")

    registry = builtin_registry()
    load_custom_tools(registry, tmp_path)

    assert "hello" in {t.id for t in registry.list()}
    assert registry.execute("hello", {}, _ctx(tmp_path)) == "ola do custom"
    assert "guia" in {t.id for t in registry.list()}
    assert "markdown" in registry.execute("guia", {}, _ctx(tmp_path))
