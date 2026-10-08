"""PORT 1:1 do opencode — Sidebar com USO REAL:
- tokens da sessão (persistidos no modelo Session, não estimativa)
- arquivos escritos pela sessão (projetos sem git também)"""

from typing import Any

from bombe_code.tui.widgets.sidebar import Sidebar


class _ContentFalso:
    def __init__(self) -> None:
        self.ultimo: Any = None

    def update(self, t: Any) -> None:
        self.ultimo = t


def test_registrar_arquivo_mostra_na_view(tmp_path):
    s = Sidebar(project_dir=str(tmp_path))
    s._content_widget = _ContentFalso()
    s.registrar_arquivo("src/lexpontes/db.py")
    s.registrar_arquivo("migrations/0001_core.sql")
    s.registrar_arquivo("src/lexpontes/db.py")  # duplicado não repete

    s.refresh_view()
    texto = str(s._last_rendered_text or "")
    assert "ARQUIVOS MODIFICADOS (2)" in texto
    assert "db.py" in texto
    assert "0001_core.sql" in texto


def test_uso_real_substitui_estimativa(tmp_path):
    s = Sidebar(project_dir=str(tmp_path))
    s._content_widget = _ContentFalso()
    s.update_metrics(tokens=86_280, percent=67, cost=0.0035)

    s.refresh_view()
    texto = str(s._last_rendered_text or "")
    assert "86,280 tokens" in texto
    assert "67% usada" in texto


def test_escrita_rascunho_nao_gera_veto(tmp_path):
    """Regressão make-books: rascunhos (*.snippet) não são bandeira vermelha."""
    from bombe_code.permissions.acao_guard import GuardaDeAcoes

    g = GuardaDeAcoes(agente="@valim")
    assert g.validar_escrita("src/api/client.st004.snippet.js", "") is None
