"""Aba 📋 TAREFAS da sidebar — lê o KANBAN DE AGENTES (task a task):

- UMA REGRA: a ordem da tela É a ordem de execução do kanban — situação
  blocked (🚩 vermelho) é flag e NUNCA muda a posição do card
- EM ANDAMENTO (bola da vez: a primeira EM DEV na ordem) = NEGRITO +
  símbolo ALTERNANDO com 🔨 (em construção)
- Fila = sem negrito, qualquer que seja a cor
- TETO de 7 somando tudo
"""

import sqlite3
import time
from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tui.tokens import TOKENS
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
        if t["status"] == "BLOCKED":
            # LEGADO: DBs antigos tinham 'BLOCKED' como pseudo-coluna. Grava a
            # linha crua para a sidebar exercitar a normalização na leitura
            # (situação na coluna real).
            db.mover_task_kanban(
                "ONDA-004", t["story"], t["tid"], "AGUARDANDO_DEV", t.get("tipo", "")
            )
            con = sqlite3.connect(tmp_path / ".bombe-code" / "state.db")
            con.execute(
                "UPDATE agent_tasks SET kanban_status = 'BLOCKED' WHERE task_id = ?",
                (t["tid"],),
            )
            con.commit()
            con.close()
        else:
            db.mover_task_kanban("ONDA-004", t["story"], t["tid"], t["status"], t.get("tipo", ""))
    return tmp_path, db


def test_le_tasks_do_kanban_na_mesma_ordem_do_processo(tmp_path: Path):
    """UMA COISA SÓ: a tela renderiza o MESMO quadro que o processo queima
    (quadro_da_onda). Ordem = ordem do kanban; DEV DONE não é fila (não
    aparece); 🚩 fica NA POSIÇÃO, mantendo cor de fila; EM DEV queima verde
    negrito."""
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
    con = sqlite3.connect(proj / ".bombe-code" / "state.db")
    con.execute(
        "UPDATE agent_tasks SET updated_at = ? WHERE task_id = 'ST-001-T1'",
        (time.time() - 7200,),
    )
    con.commit()
    con.close()

    sidebar = Sidebar(project_dir=str(proj))
    sidebar._poll_tarefas()

    rotulos = [t["rotulo"] for t in sidebar.tarefas]
    # ORDEM DO KANBAN — sem balde "executando no topo": T2, T3, T4 na ordem.
    # T1 (DEV DONE) não aparece: não é fila, revalidar é do review.
    assert [r.split(" ")[1] for r in rotulos] == ["ST-001-T2", "ST-001-T3", "ST-001-T4"]
    t4 = sidebar.tarefas[2]
    assert t4["simbolo"] == "🚩", "T4 blocked: bandeira NA POSIÇÃO do kanban"
    assert t4["cor"] == TOKENS["text_muted"], "blocked mantém a cor de fila"
    assert t4["em_andamento"] is False, "🚩 NUNCA parece queimando (mata o pisca)"
    # T2 é a EM DEV do kanban: queimando agora — verde negrito.
    assert sidebar.tarefas[0]["rodando"] is True
    assert sidebar.tarefas[0]["em_andamento"] is True
    # T3 na fila: cinza claro, sem negrito.
    assert sidebar.tarefas[1]["em_andamento"] is False


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
    assert tr["em_andamento"] is False, "🚩 é impedimento: NUNCA aparece como queima"
    assert tr["simbolo"] == "🚩", "blocked mantém a bandeira"
    assert tr["rodando"] is False, "flagged não alterna martelo (lei anti-pisca)"


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

    # Bug (aguardando): 🐛 cinza claro, sem negrito
    assert por_tid["ST-001-T1"]["simbolo"] == "🐛"
    assert por_tid["ST-001-T1"]["em_andamento"] is False
    # EM DEV (exceção acumulada): ambas VERDE NEGRITO — verdade do kanban.
    assert por_tid["ST-001-T2"]["simbolo"] == "⚙️"
    assert por_tid["ST-001-T2"]["em_andamento"] is True
    assert por_tid["ST-001-T2"]["rodando"] is True
    assert por_tid["ST-001-T3"]["simbolo"] == "🐛"
    assert por_tid["ST-001-T3"]["rodando"] is True
    # ORDEM = ORDEM DO KANBAN (sem balde de execução no topo)
    assert [t["rotulo"].split(" ")[1] for t in sidebar.tarefas] == [
        "ST-001-T1",
        "ST-001-T2",
        "ST-001-T3",
    ]


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


def test_encerrada_nao_e_fila_quadro_mostra_so_o_que_queima(tmp_path: Path):
    """UMA COISA SÓ: o quadro é a fila do processo. DEV DONE/DONE DEFINITIVO
    não são fila — nem aparecem (revalidar é papel do review)."""
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
    tr3 = next(t for t in sidebar.tarefas if "ST-001-T3" in t["rotulo"])
    # FIM DE TASK: cinza ESCURO RISCADO (a indicação que faltava no quadro)
    assert tr3["simbolo"] == "✓"
    assert "strike" in tr3["cor"], f"DEV DONE sem riscado: {tr3['cor']}"
    assert tr3["em_andamento"] is False
    assert not any("ST-001-T2" in r for r in rotulos), "DONE DEFINITIVO nem aparece"
    # Sem fila esperando, o riscado PERMANECE (quadro não esvazia)
    assert any("ST-001-T3" in r for r in rotulos)
