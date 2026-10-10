"""Tool delete_project_file — política de confiança:

- DENTRO da raiz do projeto: apaga tudo em qualquer modo (o git amortece
  bobagem interna; estado da plataforma .git/.bombe-code permanece intocado).
- FORA da raiz: em AUTO é NEGADO (bobagem fora não tem conserto); em
  SEMI-AUTO/MANUAL exige permissão EXPLÍCITA do humano (/permitir apagar).
- Guardião: anti-rampage (máx. 20 remoções por execução) + estado da
  plataforma vetado sempre.
"""

from pathlib import Path

import pytest

from bombe_code.permissions.acao_guard import GuardaDeAcoes
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing import orchestrator as orch_mod
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.progress import BUS


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    (tmp_path / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    return tmp_path, db


@pytest.fixture(autouse=True)
def _limpa_autorizacoes():
    orch_mod._REMOCOES_AUTORIZADAS.clear()
    yield
    orch_mod._REMOCOES_AUTORIZADAS.clear()


def _orch(project_dir: Path, db: ProjectDatabase, modo: str = "AUTO") -> WaveOrchestrator:
    orch = WaveOrchestrator(project_dir=str(project_dir), db=db)
    orch.start_wave("ONDA-001", autonomy_mode=modo)
    return orch


def _tool_delete(orch: WaveOrchestrator, guarda=None):
    tools = orch._get_project_fs_tools(guarda)
    assert len(tools) == 5, "toolset deve ter read/write/list/delete/executar"
    return tools[3]  # delete_project_file (ordem fixa: read, write, list, delete, executar)


def test_delete_dentro_da_raiz_qualquer_modo(project_env):
    project_dir, db = project_env
    lixo = project_dir / "tmp_residuo.py"
    lixo.write_text("x", encoding="utf-8")
    orch = _orch(project_dir, db, modo="AUTO")

    resp = _tool_delete(orch)("tmp_residuo.py")

    assert "removido" in resp
    assert not lixo.exists()


def test_delete_fora_da_raiz_auto_nega(project_env, tmp_path: Path):
    project_dir, db = project_env
    fora = tmp_path.parent / "bombe_test_fora_auto.txt"
    fora.write_text("nunca apagar", encoding="utf-8")
    orch = _orch(project_dir, db, modo="AUTO")
    try:
        resp = _tool_delete(orch)(str(fora))

        assert "NEGADA" in resp
        assert fora.exists()
    finally:
        fora.unlink(missing_ok=True)


def test_delete_fora_da_raiz_manual_exige_permissao_explicita(project_env, tmp_path: Path):
    project_dir, db = project_env
    fora = tmp_path.parent / "bombe_test_fora_manual.txt"
    fora.write_text("x", encoding="utf-8")
    orch = _orch(project_dir, db, modo="MANUAL")
    delete = _tool_delete(orch)

    publicados: list[str] = []
    publicar_original = BUS.publish

    def _capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    try:
        BUS.publish = _capturar
        resp = delete(str(fora))

        # 1ª tentativa: negada + pedido de permissão publicado
        assert "PERMISSÃO NECESSÁRIA" in resp
        assert fora.exists()
        assert any("PERMISSÃO EXPLÍCITA" in t for t in publicados)

        # Humano autoriza → a MESMA sessão passa a permitir
        orch_mod.autorizar_remocao(str(fora))
        resp2 = delete(str(fora))
        assert "removido" in resp2
        assert not fora.exists()
    finally:
        BUS.publish = publicar_original
        fora.unlink(missing_ok=True)


def test_estado_da_plataforma_nunca_se_apaga(project_env):
    project_dir, db = project_env
    estado = project_dir / ".bombe-code" / "outro.db"
    estado.parent.mkdir(exist_ok=True)
    estado.write_text("db", encoding="utf-8")
    orch = _orch(project_dir, db, modo="AUTO")

    resp = _tool_delete(orch)(".bombe-code/state.db")

    assert "negada" in resp.lower()
    assert estado.exists()


def test_guardiao_veta_rampage_de_remocoes(project_env):
    project_dir, db = project_env
    orch = _orch(project_dir, db)
    guarda = GuardaDeAcoes(agente="@valim")
    delete = _tool_delete(orch, guarda)
    for i in range(20):
        (project_dir / f"tmp_{i}.txt").write_text("x", encoding="utf-8")

    respostas = [delete(f"tmp_{i}.txt") for i in range(20)]
    assert all("removido" in r for r in respostas)

    extra = project_dir / "tmp_20.txt"
    extra.write_text("x", encoding="utf-8")
    resp21 = delete("tmp_20.txt")
    assert "VETO" in resp21 or "remoção em massa" in resp21
    assert extra.exists()


def test_guardiao_validar_remocao_veta_git_e_redflag():
    guarda = GuardaDeAcoes(agente="@valim")
    assert "bloqueada" in (guarda.validar_remocao("proj/.git/config") or "")
    assert "bloqueada" in (guarda.validar_remocao(".bombe-code/state.db") or "")
    assert guarda.validar_remocao("docs/nota.md") is None
