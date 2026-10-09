"""Aba 📋 TAREFAS da sidebar — fila viva do kanban:

- Onda + código da Story + frase curta
- Status: 🚩 vermelho = bloqueada · 🟠 laranja = revisão/correção ·
  ▶ verde = nova em execução · · cinza = fila · ✓ riscada cinza escuro =
  encerrada (visível 60s, depois dá lugar à fila)
- TETO de 7 somando atuais + encerradas recentes + fila
"""

import sqlite3
import time
from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tui.widgets.sidebar import Sidebar, _frase_curta


def _db_com_cards(tmp_path: Path, cards: list[tuple[str, str, str, int]]) -> Path:
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
    for sid, titulo, status, bloqueada in cards:
        kanban.add_card(
            story_id=sid,
            wave_id="ONDA-004",
            title=titulo,
            agent="@valim",
            status=status,
            is_blocked=bool(bloqueada),
        )
    return tmp_path


def test_teto_de_7_com_atuais_em_cima(tmp_path):
    cards = [
        ("ST-001", "Story 1 — Relatório pré-publicação", "IN_PROGRESS", 0),
        ("ST-002", "Story 2 — Autenticação de leitores", "READY", 0),
        ("ST-003", "Story 3 — Fila de processamento", "READY", 0),
        ("ST-004", "Story 4 — Insights e memória", "READY", 0),
        ("ST-301", "Story 301 — Editor de livros", "READY", 0),
        ("ST-302", "Story 302 — Exportação de PDF", "READY", 0),
        ("ST-303", "Story 303 — Observador de IA", "READY", 0),
        ("ST-304", "Story 304 — Worker de jobs", "READY", 0),
    ]
    proj = _db_com_cards(tmp_path, cards)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    assert len(sidebar.tarefas) == 7, "teto de 7"
    assert sidebar.tarefas[0]["sid"] == "ST-001"
    assert sidebar.tarefas[0]["estado"] == "run"
    assert all(t["estado"] == "fila" for t in sidebar.tarefas[1:])
    assert sidebar.tarefas[0]["frase"] == "Relatório pré-publicação"
    assert sidebar.wave_id == "ONDA-004"

    class _ContentFalso:
        ultimo = None

        def update(self, t):
            self.ultimo = t

    sidebar._content_widget = _ContentFalso()
    sidebar.refresh_view()
    rendered = str(sidebar._last_rendered_text or "")
    assert "📋 TAREFAS · ONDA-004 (7)" in rendered
    assert "▶ ST-001" in rendered
    assert "· ST-303" in rendered
    assert "ST-304" not in rendered, "a 8ª story não cabe no teto de 7"


def test_status_bloqueada_revisao_e_encerrada_riscada(tmp_path):
    cards = [
        ("ST-001", "Story 1 — Relatório", "IN_PROGRESS", 1),  # 🚩 bloqueada
        ("ST-002", "Story 2 — Autenticação", "IN_REVIEW", 0),  # 🟠 revisão
        ("ST-003", "Story 3 — Fila", "READY", 0),  # ⚪ fila
        ("ST-004", "Story 4 — Worker", "DONE", 0),  # ✓ encerrada recente
    ]
    proj = _db_com_cards(tmp_path, cards)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    estados = {t["sid"]: t["estado"] for t in sidebar.tarefas}
    assert estados["ST-001"] == "blocked"
    assert estados["ST-002"] == "review"
    assert estados["ST-003"] == "fila"
    assert estados["ST-004"] == "done"

    class _ContentFalso:
        ultimo = None

        def update(self, t):
            self.ultimo = t

    sidebar._content_widget = _ContentFalso()
    sidebar.refresh_view()
    rendered = str(sidebar._last_rendered_text or "")
    assert "🚩 ST-001" in rendered
    assert "🟠 ST-002" in rendered
    assert "· ST-003" in rendered
    assert "✓ ST-004" in rendered


def test_encerrada_antiga_sai_e_fila_entra(tmp_path):
    """DONE com mais de 60s some — a vaga vai para a próxima da fila."""
    cards = [
        ("ST-001", "Story 1 — Antiga", "DONE", 0),
        ("ST-002", "Story 2 — Fila A", "READY", 0),
        ("ST-003", "Story 3 — Fila B", "READY", 0),
    ]
    proj = _db_com_cards(tmp_path, cards)
    # Envelhece a DONE manualmente (updated_at = 2h atrás)
    con = sqlite3.connect(proj / ".bombe-code" / "state.db")
    con.execute(
        "UPDATE kanban_cards SET updated_at = ? WHERE story_id = 'ST-001'",
        (time.time() - 7200,),
    )
    con.commit()
    con.close()

    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    sids = [t["sid"] for t in sidebar.tarefas]
    assert "ST-001" not in sids, "encerrada antiga deveria ter sumido"
    assert sids == ["ST-002", "ST-003"]


def test_encerrada_recente_ocupa_vaga_por_60s(tmp_path):
    """DONE recente fica riscada visível — mesmo que desloque a fila."""
    cards = [
        ("ST-001", "Story 1 — Recém-concluída", "DONE", 0),
        ("ST-002", "Story 2 — Fila A", "READY", 0),
        ("ST-003", "Story 3 — Fila B", "READY", 0),
    ]
    proj = _db_com_cards(tmp_path, cards)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    assert sidebar.tarefas[0]["sid"] == "ST-001"
    assert sidebar.tarefas[0]["estado"] == "done"
    assert sidebar.tarefas[0]["marcador"] == "✓"


def test_sem_banco_nao_quebra(tmp_path):
    sidebar = Sidebar(project_dir=str(tmp_path / "vazio"))
    sidebar._poll_tarefas()
    assert sidebar.tarefas == []


def test_frase_curta_remove_prefixo_story():
    assert _frase_curta("Story 1 — Relatório pré-publicação") == "Relatório pré-publicação"
    assert _frase_curta("Editor de livros") == "Editor de livros"
