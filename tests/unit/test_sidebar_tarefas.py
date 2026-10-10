"""Aba 📋 TAREFAS da sidebar — lê o KANBAN DE AGENTES (task a task):

- Prioridade: BLOCKED (Andon, 🚩 vermelho) → EM DEV (▶ verde) → fila (·
  cinza) → DEV DONE/DONE DEFINITIVO (✓ apagado)
- EM ANDAMENTO (EM DEV) = NEGRITO + símbolo ALTERNANDO com 🔨 (em construção)
- Fila = sem negrito, qualquer que seja a cor
- TETO de 7 somando tudo
"""

import sqlite3
import time
from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tui.widgets.sidebar import Sidebar


def _db_com_tasks(tmp_path: Path, tasks: list[dict]) -> tuple[Path, ProjectDatabase]:
    db = ProjectDatabase(str(tmp_path))
    con = sqlite3.connect(tmp_path / ".bombe-code" / "state.db")
    con.execute(
        "INSERT INTO wave_state (wave_id, state, autonomy_mode, engineering_mode, updated_at) "
        "VALUES ('ONDA-004', 'EXECUTE', 'AUTO', 'tdd-code', ?)",
        (time.time(),),
    )
    con.commit()
    con.close()
    for t in tasks:
        db.criar_task_kanban(
            "ONDA-004", t["story"], t["tid"], t.get("titulo", t["tid"]), t["agente"], t["ordem"]
        )
        db.mover_task_kanban("ONDA-004", t["story"], t["tid"], t["status"], t.get("tipo", ""))
    return tmp_path, db


def test_le_tasks_do_kanban_de_agentes_com_prioridade(tmp_path: Path):
    proj, _db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T1",
                "agente": "@codd",
                "ordem": 0,
                "status": "DEV_DONE",
            },
            {
                "story": "ST-001",
                "tid": "ST-001-T2",
                "agente": "@valim",
                "ordem": 1,
                "status": "EM_DEV",
            },
            {
                "story": "ST-001",
                "tid": "ST-001-T3",
                "agente": "@ada",
                "ordem": 2,
                "status": "AGUARDANDO_DEV",
            },
            {
                "story": "ST-001",
                "tid": "ST-001-T4",
                "agente": "@ieru",
                "ordem": 3,
                "status": "BLOCKED",
                "tipo": "INTERNAL_SCALE",
            },
        ],
    )
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    rotulos = [t["rotulo"] for t in sidebar.tarefas]
    # Andon: a BLOCKED vem primeiro; o RESTO na ORDEM DO KANBAN (fluxo real) —
    # status é símbolo/cor/negrito, nunca posição na lista.
    assert [r.split(" ")[1] for r in rotulos] == [
        "ST-001-T4",
        "ST-001-T1",
        "ST-001-T2",
        "ST-001-T3",
    ]
    assert sidebar.tarefas[0]["simbolo"] == "🚩", "T4 bloqueada: bandeira vermelha"
    assert sidebar.tarefas[0]["em_andamento"] is False, "blocked na fila: sem negrito"
    assert sidebar.tarefas[2]["em_andamento"] is True, "T2 em dev: negrito"
    assert sidebar.tarefas[3]["simbolo"] == "⚙️", "T3 na fila: símbolo do tipo, cinza"
    assert sidebar.tarefas[3]["em_andamento"] is False
    assert sidebar.tarefas[0]["simbolo"] == "🚩"
    assert sidebar.tarefas[2]["em_andamento"] is True, "T2 em dev: negrito e 🔨"


def test_em_andamento_alternar_martelo_e_negrito(tmp_path: Path):
    proj, _db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T1",
                "agente": "@valim",
                "ordem": 0,
                "status": "EM_DEV",
            }
        ],
    )
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    tr = sidebar.tarefas[0]
    assert tr["em_andamento"] is True
    # A alternância acontece no RENDER (paridade do segundo): o símbolo é o
    # original OU 🔨 — nunca um terceiro.
    simbolos_possiveis = {tr["simbolo"], "🔨"}
    for _ in range(4):
        time.sleep(0.5)

        class _ContentFalso:
            ultimo = None

            def update(self, t):
                self.ultimo = t

        sidebar._content_widget = _ContentFalso()
        sidebar.refresh_view()
        rendered = str(sidebar._last_rendered_text or "")
        linha = next((l for l in rendered.splitlines() if "ST-001-T1" in l), "")
        marcador = linha.strip().split(" ")[0]
        assert marcador in simbolos_possiveis, f"símbolo inesperado: {marcador}"


def test_blocked_re_trabalhado_mantem_bandeira_e_vira_andamento(tmp_path: Path):
    proj, _db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T1",
                "agente": "@ada",
                "ordem": 0,
                "status": "EM_DEV",
                "tipo": "INTERNAL_SCALE",
            },
        ],
    )
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    tr = sidebar.tarefas[0]
    assert tr["em_andamento"] is True, "blocked em re-trabalho está EM ANDAMENTO (negrito)"
    assert tr["simbolo"] == "🚩", "blocked mantém a bandeira"


def test_teto_de_7(tmp_path: Path):
    tasks = [
        {
            "story": "ST-001",
            "tid": f"ST-001-T{i}",
            "agente": "@valim",
            "ordem": i,
            "status": "AGUARDANDO_DEV",
        }
        for i in range(1, 9)
    ]
    proj, _db = _db_com_tasks(tmp_path, tasks)
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    assert len(sidebar.tarefas) == 7


def test_sem_kanban_de_agentes_cai_para_stories(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    from bombe_code.turing.kanban import KanbanManager

    con = sqlite3.connect(tmp_path / ".bombe-code" / "state.db")
    con.execute(
        "INSERT INTO wave_state (wave_id, state, autonomy_mode, engineering_mode, updated_at) "
        "VALUES ('ONDA-001', 'EXECUTE', 'AUTO', 'tdd-code', ?)",
        (time.time(),),
    )
    con.commit()
    con.close()
    kanban = KanbanManager(str(tmp_path), db=db)
    kanban.add_card(
        story_id="ST-001",
        wave_id="ONDA-001",
        title="Story 1 — Relatório",
        agent="@valim",
        status="IN_PROGRESS",
    )
    sidebar = Sidebar(project_dir=str(tmp_path))
    sidebar._poll_tarefas()

    assert len(sidebar.tarefas) == 1
    assert sidebar.tarefas[0]["rotulo"].startswith("ST-001")


def test_bug_tem_simbolo_proprio_e_alternar_martelo(tmp_path: Path):
    proj, _db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T1",
                "agente": "@valim",
                "ordem": 0,
                "titulo": "Correção do contrato front↔back",
                "status": "AGUARDANDO_DEV",
            },
            {
                "story": "ST-001",
                "tid": "ST-001-T2",
                "agente": "@valim",
                "ordem": 1,
                "titulo": "Rota de publicação",
                "status": "EM_DEV",
            },
            {
                "story": "ST-001",
                "tid": "ST-001-T3",
                "agente": "@ada",
                "ordem": 2,
                "titulo": "Bug do modal sem foco",
                "status": "EM_DEV",
            },
        ],
    )
    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    por_tid = {}
    for tr in sidebar.tarefas:
        tid = tr["rotulo"].split(" ")[1]
        por_tid[tid] = tr

    # Bug (idle): 🐛 laranja, sem negrito
    assert por_tid["ST-001-T1"]["simbolo"] == "🐛"
    assert por_tid["ST-001-T1"]["em_andamento"] is False
    # Task normal (idle... aqui EM DEV): ⚙️ verde, andamento
    assert por_tid["ST-001-T2"]["simbolo"] == "⚙️"
    assert por_tid["ST-001-T2"]["em_andamento"] is True
    # Bug EM DEV: 🐛 com andamento (alterna com 🔨 no render)
    assert por_tid["ST-001-T3"]["simbolo"] == "🐛"
    assert por_tid["ST-001-T3"]["em_andamento"] is True


def test_task_encerrada_sai_do_quadro_apos_60s(tmp_path: Path):
    proj, db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T1",
                "agente": "@valim",
                "ordem": 0,
                "status": "AGUARDANDO_DEV",
            }
        ],
    )
    # Task concluída há 2 horas — fora da janela de 60s
    db.criar_task_kanban("ONDA-004", "ST-001", "ST-001-T0", "Tarefa antiga", "@codd", 0)
    db.mover_task_kanban("ONDA-004", "ST-001", "ST-001-T0", "DEV_DONE")
    con = sqlite3.connect(proj / ".bombe-code" / "state.db")
    con.execute(
        "UPDATE agent_tasks SET updated_at = ? WHERE task_id = 'ST-001-T0'",
        (time.time() - 7200,),
    )
    con.commit()
    con.close()

    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    rotulos = [t["rotulo"] for t in sidebar.tarefas]
    assert not any("ST-001-T0" in r for r in rotulos), "antiga sai: fila esperando vaga"
    assert any("ST-001-T1" in r for r in rotulos), "fila permanece"


def test_encerrada_antiga_permite_quadro_vazio_nao_sumir(tmp_path: Path):
    """Todas encerradas há horas e NADA na fila? O quadro NÃO esvazia —
    as riscadas permanecem (regra: saem só para dar lugar)."""
    proj, db = _db_com_tasks(
        tmp_path,
        [
            {
                "story": "ST-001",
                "tid": "ST-001-T3",
                "agente": "@ada",
                "ordem": 1,
                "status": "DEV_DONE",
            }
        ],
    )
    db.criar_task_kanban("ONDA-004", "ST-001", "ST-001-T2", "Tarefa done", "@ada", 1)
    db.mover_task_kanban("ONDA-004", "ST-001", "ST-001-T2", "DONE_DEFINITIVO")
    con = sqlite3.connect(proj / ".bombe-code" / "state.db")
    con.execute(
        "UPDATE agent_tasks SET updated_at = ? WHERE task_id = 'ST-001-T2'", (time.time() - 7200,)
    )
    con.commit()
    con.close()

    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    rotulos = [t["rotulo"] for t in sidebar.tarefas]
    assert any("ST-001-T2" in r for r in rotulos), "sem fila, done antiga PERMANECE riscada"
    assert any("ST-001-T3" in r for r in rotulos)
