"""Aba 📋 TAREFAS da sidebar — fila viva do kanban:

- Onda + código da Story + frase curta
- Atuais (IN_PROGRESS/IN_REVIEW) em cima com ▶; próximas (READY) com ·
- TETO de 5 somando atuais + futuras; quando a atual sai, entra a próxima
"""

import sqlite3
import time
from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tui.widgets.sidebar import Sidebar, _frase_curta


def _db_com_cards(tmp_path: Path, cards: list[tuple[str, str, str]]) -> Path:
    db = ProjectDatabase(str(tmp_path))
    from bombe_code.turing.kanban import KanbanManager

    con = sqlite3.connect(tmp_path / ".bombe-code" / "state.db")
    con.execute(
        "INSERT INTO wave_state (wave_id, state, autonomy_mode, engineering_mode, updated_at) "
        "VALUES ('ONDA-004', 'EXECUTE', 'AUTO', 'tdd-code', ?)",
        (time.time(),),
    )
    con.commit()
    con.close()
    kanban = KanbanManager(str(tmp_path), db=db)
    for sid, titulo, status in cards:
        kanban.add_card(
            story_id=sid, wave_id="ONDA-004", title=titulo, agent="@valim", status=status
        )
    return tmp_path


def test_fila_mostra_atuais_em_cima_e_limita_em_5(tmp_path):
    cards = [
        ("ST-001", "Story 1 — Relatório pré-publicação", "IN_PROGRESS"),
        ("ST-002", "Story 2 — Autenticação de leitores", "READY"),
        ("ST-003", "Story 3 — Fila de processamento", "READY"),
        ("ST-004", "Story 4 — Insights e memória", "READY"),
        ("ST-301", "Story 301 — Editor de livros", "READY"),
        ("ST-302", "Story 302 — Exportação de PDF", "READY"),
        ("ST-303", "Story 303 — Observador de IA", "READY"),
    ]
    proj = _db_com_cards(tmp_path, cards)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    assert len(sidebar.tarefas) == 5, "teto de 5 somando atuais + futuras"
    assert sidebar.tarefas[0]["sid"] == "ST-001" and sidebar.tarefas[0]["atual"] is True
    assert all(t["atual"] is False for t in sidebar.tarefas[1:])
    assert sidebar.tarefas[0]["frase"] == "Relatório pré-publicação"
    assert sidebar.wave_id == "ONDA-004"

    # Render contém marcadores e códigos (padrão do teste de uso real)
    class _ContentFalso:
        ultimo = None

        def update(self, t):
            self.ultimo = t

    sidebar._content_widget = _ContentFalso()
    sidebar.refresh_view()
    rendered = str(sidebar._last_rendered_text or "")
    assert "📋 TAREFAS · ONDA-004 (5)" in rendered
    assert "▶ ST-001" in rendered
    assert "· ST-003" in rendered
    assert "ST-303" not in rendered, "a 7ª story não cabe no teto de 5"


def test_task_concluida_sai_e_fila_anda(tmp_path):
    cards = [
        ("ST-001", "Story 1 — Relatório", "DONE"),
        ("ST-002", "Story 2 — Autenticação", "IN_PROGRESS"),
        ("ST-003", "Story 3 — Fila de processamento", "READY"),
    ]
    proj = _db_com_cards(tmp_path, cards)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    assert [t["sid"] for t in sidebar.tarefas] == ["ST-002", "ST-003"]
    assert sidebar.tarefas[0]["atual"] is True
    assert sidebar.tarefas[1]["atual"] is False


def test_sem_banco_nao_quebra(tmp_path):
    sidebar = Sidebar(project_dir=str(tmp_path / "vazio"))
    sidebar._poll_tarefas()
    assert sidebar.tarefas == []


def test_frase_curta_remove_prefixo_story():
    assert _frase_curta("Story 1 — Relatório pré-publicação") == "Relatório pré-publicação"
    assert _frase_curta("Editor de livros") == "Editor de livros"
