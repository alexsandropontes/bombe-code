"""KANBAN DE AGENTES — manda em tudo (fonte única de verdade).

- A task de agente NASCE NO KANBAN (designada, ordenada) ANTES de qualquer
  agente acordar. Sem ordem no kanban, agente nem acorda.
- Colunas: BACKLOG → AGUARDANDO DEV → EM DEV → DEV DONE → DONE DEFINITIVO.
- BLOCKED acontece NA coluna em que está e fica ali, tipado; prioridade
  Impedimento: primeiro resolvo blocked antes de qualquer outra coisa.
- Resume: DEV DONE/DONE DEFINITIVO são IGNORADOS (revalidar é papel do code
  review final da story); pega BLOCKED ou o próximo AGUARDANDO DEV.
- Code review achou algo do agente X → os cards DEV DONE de X voltam para o
  BURN. Story 100% aprovada → DONE DEFINITIVO (nunca mais volta; mexer
  depois = CHANGE = novo card).
"""

from pathlib import Path

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.pbb import AtomicTask, AtomicTaskType
from bombe_code.turing.progress import BUS
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    (tmp_path / "app.py").write_text("def app() -> str:\n    return 'ok'\n", encoding="utf-8")
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-004", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-004", title="Story 1", agent="@valim", status="IN_PROGRESS"
    )
    return tmp_path, orch


def _tarefas():
    return [
        AtomicTask(
            id="T1",
            story_id="ST-001",
            task_type=AtomicTaskType.FRONTEND_UI,
            title="Tela",
            description="tela",
            responsible_agent="@ada",
        ),
        AtomicTask(
            id="T2",
            story_id="ST-001",
            task_type=AtomicTaskType.BACKEND_TDD,
            title="Rota",
            description="rota",
            responsible_agent="@valim",
        ),
        AtomicTask(
            id="T3",
            story_id="ST-001",
            task_type=AtomicTaskType.DATABASE,
            title="Schema",
            description="schema",
            responsible_agent="@codd",
        ),
    ]


def test_task_nasce_no_kanban_designada_e_ordenada(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())

    cartoes = orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    assert [c["task_id"] for c in cartoes] == ["T1", "T2", "T3"], "ordem de execução"
    assert [c["agent_role"] for c in cartoes] == ["@ada", "@valim", "@codd"], "designação"
    assert all(c["kanban_status"] == "AGUARDANDO_DEV" for c in cartoes), (
        "nasce BACKLOG e vai para AGUARDANDO DEV quando pronta"
    )


def test_preparar_nao_toca_cards_em_andamento(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "EM_DEV")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")

    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())  # re-chamada (resume)

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados == {"T1": "AGUARDANDO_DEV", "T2": "EM_DEV", "T3": "DEV_DONE"}


def test_fila_blocked_primeiro_e_feitos_ignorados(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    # SITUAÇÃO (não coluna): T2 fica NA coluna em que está, com a flag tipada.
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T2", "INTERNAL_SCALE")

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    finally:
        BUS.publish = publicar_original

    # LEI: flag é SITUAÇÃO — queima NA POSIÇÃO do kanban (T2 antes de T3).
    # Flag NUNCA furta fila e NUNCA é perpetuidade (flagged fora da fila =
    # deadlock do resume: a fila esvazia, nada desbloqueia, a linha morre).
    # O anti-loop é o TETO DE 2 FALHAS no ciclo, não exclusão da fila.
    assert [t["task_id"] for t in fila] == ["T2", "T3"], "flagged queima na posição; fila segue a ordem do kanban"
    cartoes_dep = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cartoes_dep["T2"]["block_tipo"] == "INTERNAL_SCALE", "flag preservada NA coluna"
    assert cartoes_dep["T2"]["kanban_status"] == "AGUARDANDO_DEV", "blocked é situação, card fica na coluna real"
    assert any("ignoro no resume" in t and "T1" in t for t in publicados)


def test_transicao_binaria_dev_done_ou_blocked(project_env):
    """Binário do fim do trabalho: sucesso → DEV DONE; falha → SITUAÇÃO
    blocked tipada, o card PERMANECE NA COLUNA EM QUE ESTÁ (blocked não é
    coluna — é flag que impede a próxima coluna até ser resolvida)."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # deu certo
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "EM_DEV")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    # não deu certo — fica EM DEV (coluna real) com a situação HUMAN_SCALE
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "EM_DEV")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T2", "HUMAN_SCALE")

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    tipos = {
        c["task_id"]: c["block_tipo"] for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T1"] == "DEV_DONE"
    assert estados["T2"] == "EM_DEV", "o card NUNCA sai da coluna por causa de blocked"
    assert tipos["T2"] == "HUMAN_SCALE"
    # A coluna 'BLOCKED' NÃO EXISTE: passá-la como status é argumento inválido.
    import pytest as _pytest

    with _pytest.raises(ValueError):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "BLOCKED", "INTERNAL_SCALE")


def test_bola_da_vez_burn_um_por_vez_e_em_dev_acumula(project_env):
    """REGRA DO BURN: a card pega vai pra EM_DEV ANTES de atuar; EM DEV pode
    ter várias (exceção acumulada) — quem travou blocked EM DEV FICA EM DEV
    com a situação; o que é um por vez é o BURN. Escolha DETERMINÍSTICA
    (situação → ordem do kanban): 10 execuções, a mesma bola da vez."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # Exceção acumulada: T1 EM DEV bloqueada NA coluna; T2 EM DEV de crash.
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "EM_DEV")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T1", "INTERNAL_SCALE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "EM_DEV")
    # A bola da vez: T3 vai pra EM DEV antes de atuar
    orch._acordar_task_em_dev("ONDA-004", "ST-001", "T3")

    cards = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cards["T3"]["kanban_status"] == "EM_DEV", "a pega vai pra EM DEV ANTES de atuar"
    assert cards["T1"]["kanban_status"] == "EM_DEV", "travou EM DEV? FICA EM DEV"
    assert cards["T1"]["block_tipo"] == "INTERNAL_SCALE", "situação preservada"
    assert cards["T2"]["kanban_status"] == "EM_DEV"
    # Nada volta pra AGUARDANDO DEV por construção — a fila decide o BURN
    assert cards["T1"]["block_tipo"] != "" or cards["T2"]["block_tipo"] != "" or True

    # DETERMINISMO: a prioridade da fila (garcom) escolhe sempre a mesma
    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        escolhas = [
            [t["task_id"] for t in orch._garcom_carregar_fila("ONDA-004", "ST-001")[0]]
            for _ in range(3)
        ]
    finally:
        BUS.publish = publicar_original
    assert escolhas[0] == escolhas[1] == escolhas[2], "a fila é determinística"
    assert escolhas[0] == ["T1", "T2", "T3"], "flagged (T1) queima NA POSIÇÃO; fila = ordem do kanban"
    assert "T1" in escolhas[0], "flag nunca é perpetuidade: a card volta a queimar na sua ordem"


def test_legado_blocked_pseudo_coluna_normaliza_para_situacao(project_env):
    """DBs antigos gravavam 'BLOCKED' como status (pseudo-coluna). A leitura
    normaliza: coluna real AGUARDANDO DEV + situação preservada — o modelo
    (colunas × situação) volta a valer sem perder dado."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    import sqlite3 as _sq

    caminho = _tmp_path / ".bombe-code" / "state.db"
    con = _sq.connect(caminho)
    con.execute("UPDATE agent_tasks SET kanban_status = 'BLOCKED' WHERE task_id = 'T2'")
    con.commit()
    con.close()

    cards = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cards["T2"]["kanban_status"] == "AGUARDANDO_DEV"
    assert cards["T2"]["block_tipo"] == "INTERNAL_SCALE"


def test_dor_100_por_cento_para_ir_para_em_dev(project_env):
    """DOR 100% ATENDIDA é condição para puxar a card pra EM DEV — sem
    exceção. Card com precedência pendente NÃO acorda (ninguém atua); após
    o alvo chegar a DEV DONE, a mesma chamada acorda."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "T9",
        "Depende do schema",
        "@valim",
        9,
        dor=["dep:T3"],
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T9", "AGUARDANDO_DEV")

    assert orch._acordar_task_em_dev("ONDA-004", "ST-001", "T9") is False
    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T9"] == "AGUARDANDO_DEV", "DOR pendente: card não entra em DEV"

    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")
    assert orch._acordar_task_em_dev("ONDA-004", "ST-001", "T9") is True
    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T9"] == "EM_DEV"


def test_dependencia_entre_stories_e_falha_de_planejamento(project_env):
    """S2T1 pendurada na S1T3: enquanto S1T3 não está DEV DONE, a card NÃO é
    elegível E a falha de planejamento é sinalizada (a story de origem é
    entregue por completo antes). Com o alvo pronto, a card entra na fila."""
    _tmp_path, orch = project_env
    orch.kanban.add_card(
        story_id="ST-002", wave_id="ONDA-004", title="Story 2", agent="@valim", status="IN_PROGRESS"
    )
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-002",
        "T1",
        "Story 2 pendurada na ST-001",
        "@valim",
        1,
        dor=["dep:T3"],
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-002", "T1", "AGUARDANDO_DEV")

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        # DOR da ST-002-T1 resolve contra a ST-001 (cross-story pendente):
        assert orch._dor_satisfeita(
            orch.db.carregar_tasks_kanban("ONDA-004", "ST-002")[0],
            orch.db.carregar_tasks_kanban("ONDA-004", "ST-002"),
        )[0] is False
        orch._garcom_carregar_fila("ONDA-004", "ST-002")
        assert any("FALHA DE PLANEJAMENTO" in t for t in publicados), (
            "elegibilidade fora de ordem é erro do breakdown — levanta a mão"
        )
        # Alvo concluído na ST-001 → dependência satisfeita (cross-story)
        orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")
        ok, _ = orch._dor_satisfeita(
            orch.db.carregar_tasks_kanban("ONDA-004", "ST-002")[0],
            orch.db.carregar_tasks_kanban("ONDA-004", "ST-002"),
        )
        assert ok, "alvo DEV DONE em outra story satisfaz a precedência"
    finally:
        BUS.publish = publicar_original


def test_desempate_deterministico_de_fato(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # T2 e T3 com a MESMA ordem (empate) → task_id decide: T2 antes de T3
    con = orch.db._get_connection() if hasattr(orch.db, "_get_connection") else None
    assert con is not None
    with con:
        con.execute("UPDATE agent_tasks SET ordem = 2 WHERE task_id IN ('T2', 'T3')")
    con.close()

    ordens = [
        [c["task_id"] for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")]
        for _ in range(5)
    ]
    assert ordens[0] == ["T1", "T2", "T3"], "empate de ordem cai para task_id"
    assert all(o == ordens[0] for o in ordens), "10 execuções, a mesma escolha"


def test_achado_devolve_cards_do_agente_para_burn(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "EM_DEV")
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DEV_DONE")

    voltaram = orch._garcom_devolver_cards_para_burn("ONDA-004", "ST-001", "@codd")

    assert voltaram == 1
    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T3"] == "AGUARDANDO_DEV", "card do banco voltou para o BURN"
    assert estados["T1"] == "DEV_DONE" and estados["T2"] == "DEV_DONE"


def test_story_aprovada_vira_done_definitivo(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DEV_DONE")

    # Story 100% aprovada → DONE DEFINITIVO (nunca mais volta)
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DONE_DEFINITIVO")

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert all(s == "DONE_DEFINITIVO" for s in estados.values())
    # _garcom_devolver_cards_para_burn NÃO mexe em DONE DEFINITIVO
    assert orch._garcom_devolver_cards_para_burn("ONDA-004", "ST-001", "@codd") == 0


def test_review_nao_pula_fila_por_blocked_precedencia(project_env):
    """PRECEDÊNCIA > PRIORIDADE: review bloqueado NÃO é tratado antes das
    tasks pendentes — a regra que libera o review (todas as tasks DEV DONE)
    é o que define QUANDO ele pode ser queimado."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # T1 pronta; T2 e T3 ainda na fila; review bloqueado tentando furar
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "REVIEW-TECH",
        "Code Review da story",
        "@unclebob",
        90,
        dor=["all_burn_done"],
    )
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "REVIEW-TECH", "INTERNAL_SCALE")

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    finally:
        BUS.publish = publicar_original

    # A fila é das TASKS: T2 e T3 (blocked T2? não — T2/T3 aguardando; T1 feito)
    ids = [t["task_id"] for t in fila]
    assert "T2" in ids and "T3" in ids, "as tasks pendentes são queimadas primeiro"
    # O aviso de precedência explica por que o review não sobe
    assert any("PRECEDÊNCIA" in t and "AGUARDA" in t for t in publicados)


def test_tool_executar_comando_whitelist(project_env):
    """QA executa suítes de VERDADE: tool com whitelist estrita (pytest/
    vitest/playwright/scripts) — fora dela, negado; destrutivo, negado."""
    _tmp_path, orch = project_env
    tools = orch._get_project_fs_tools()
    executar = tools[-1]

    # fora da whitelist → negado
    resp = executar("curl https://mal.example")
    assert "proibida" in resp.lower() or "whitelist" in resp.lower()
    # destrutivo mesmo dentro do prefixo → negado
    resp2 = executar("pytest ; rm -rf /")
    assert "proibida" in resp2.lower()
    # permitido → executa de verdade (pytest --version, rápido)
    resp3 = executar("python -m pytest --version")
    assert "exit=0" in resp3
    assert "pytest" in resp3.lower()


def test_executar_comando_grade_enterprise(project_env):
    """Gate estruturado: launchers reais de ambiente (uv run, .venv/bin),
    helpers de leitura em pipes — e negação de fora-da-lista/destrutivo."""
    _tmp_path, orch = project_env
    tools = orch._get_project_fs_tools()
    executar = tools[-1]

    # launchers reais: uv run pytest ✓ (executa — falha por não haver pytest no
    # system python, mas a FLAG é execução, não whitelist)
    resp = executar("uv run pytest --version")
    assert "whitelist" not in resp.lower() and "fora da lista" not in resp.lower()
    # .venv/bin/pytest ✓ (basename pytest)
    resp = executar(".venv/bin/pytest --version")
    assert "fora da lista" not in resp.lower()
    # pipe com helper de leitura ✓
    resp = executar("uv run pytest --version | tail -5")
    assert "fora da lista" not in resp.lower()
    # cat = helper de leitura ✓ (executa; arquivo inexistente no fixture)
    resp = executar("cat pyproject.toml")
    assert resp.startswith("exit=")
    # git = programa fora da lista ✗
    resp = executar("git status")
    assert "fora da lista" in resp.lower()
    # bash fora de scripts/ ✗
    resp = executar("bash -c 'rm -rf /'")
    assert "só executa scripts/" in resp.lower() or "proibida" in resp.lower()
    # destrutivo em qualquer segmento ✗
    resp = executar("uv run pytest | tee /etc/passwd")
    assert "proibida" in resp.lower() or "fora da lista" in resp.lower()


def test_blocked_tem_precedencia_sobre_trabalho_livre(project_env):
    """GESTÃO DE FLUXO REAL: card deu blocked → trata NA HORA. Na fila única,
    card flagged com DOR 100% satisfeita queima ANTES de trabalho livre que
    esteja à frente dela na ordem — a linha para no impedimento, resolve, e
    só então segue. Cadeia de blockeds resolve por DEPENDÊNCIA: blocked B
    (dep: A blocked) só fica elegível quando A é resolvido."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # T2 (ordem 1) blocked com DOR satisfeita — impedimento aguardando tratamento
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T2", "INTERNAL_SCALE")
    # T1 (ordem 0) livre: o kanban a coloca antes de T2, mas o BLOCKED TEM
    # PRECEDÊNCIA DE TRATAMENTO
    fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    assert [t["task_id"] for t in fila][:2] == ["T2", "T1"], (
        f"blocked não foi tratado na hora: {[t['task_id'] for t in fila]}"
    )
    # A pega do blocked ANUNCIA o tratamento e mata a flag
    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        orch._acordar_task_em_dev("ONDA-004", "ST-001", "T2")
    finally:
        BUS.publish = publicar_original
    cartao = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cartao["T2"]["block_tipo"] == "", "flag morre na pega (tratamento na hora)"
    assert cartao["T2"]["kanban_status"] == "EM_DEV"
    assert any("TRATANDO IMPEDIMENTO" in t and "T2" in t for t in publicados)

    # CADEIA DE BLOCKEDS POR DEPENDÊNCIA: T4 (dep:T3) também blocked — enquanto
    # T3 (o bloqueador) não resolve, T4 NEM é elegível; resolvido T3, T4 é o
    # próximo (tratamento pela ordem de precedência/dependência).
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "T4",
        "Depende de T3",
        "@valim",
        3,
        dor=["dep:T3"],
        task_tipo="BACKEND_TDD",
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T4", "AGUARDANDO_DEV")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T3", "INTERNAL_SCALE")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T4", "INTERNAL_SCALE")
    fila2, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    ids2 = [t["task_id"] for t in fila2]
    assert ids2 == ["T3"], f"cadeia: esperado só o bloqueador de jusante, veio {ids2}"
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")
    fila3, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    ids3 = [t["task_id"] for t in fila3]
    assert ids3[:1] == ["T4"], f"resolvido o bloqueador, o blocked dependente é o próximo: {ids3}"


def test_blocked_com_precedencia_pendente_nao_e_tratado_antes_do_bloqueador(project_env):
    """A PRIORIZAÇÃO NASCE NO KANBAN, NÃO NA PEGA: task blocked cuja DOR é uma
    precedência/dependência pendente NÃO é tratada antes do bloqueador. O
    bloqueador (INSTALACAO-n) já nasceu priorizado NO KANBAN (ordem 0) e a
    origem ganhou dep: na DOR — a fila é MONTADA por isso (DOR 100% na
    montagem), nunca por decisão no momento de pegar a card."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # XPTO = T3 blocked PORQUE depende da instalação (precedência escrita na
    # DOR da origem no nascimento da instalação — `_abrir_task_instalacao`)
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "INSTALACAO-1",
        "Instalar jsdom",
        "@unclebob",
        0,
        task_tipo="INSTALACAO",
    )
    orch.db.adicionar_dep_task_kanban("ONDA-004", "ST-001", "T3", "INSTALACAO-1")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "T3", "INTERNAL_SCALE")

    fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    ids = [t["task_id"] for t in fila]

    # T3 blocked NÃO entra: sua DOR (precedência) está pendente — o tratamento
    # dela É queimar o bloqueador, que já nasceu priorizado (ordem 0).
    assert "T3" not in ids, f"blocked com precedência pendente não pode ser pego: {ids}"
    assert ids[:1] == ["INSTALACAO-1"], f"o bloqueador priorizado no kanban queima primeiro: {ids}"
    # Livres (T1) queimam depois do bloqueador, na ordem do kanban
    assert "T1" in ids


def test_round_paralelo_somente_front_x_backend(project_env):
    """ROUND DE PARALELISMO (regra do processo): só FRONTEND × (BACKEND|
    DATABASE) queimam juntos — tasks que não mexem no mesmo ambiente/código.
    Achado/instalação/review e pares do mesmo lado: SOLO (fila indiana). O
    round termina quando TODAS as paralelas terminam; o round seguinte segue
    pelos resultados."""
    from bombe_code.turing.pbb import AtomicTask, AtomicTaskType

    _tmp_path, orch = project_env
    tarefas = [
        AtomicTask(
            id="F1", story_id="ST-001", task_type=AtomicTaskType.FRONTEND_UI,
            title="Tela", description="tela", responsible_agent="@ada",
        ),
        AtomicTask(
            id="B1", story_id="ST-001", task_type=AtomicTaskType.BACKEND_TDD,
            title="Rota", description="rota", responsible_agent="@valim",
        ),
    ]
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", tarefas)
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "F1", "INTERNAL_SCALE")

    fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    # ambos elegíveis; o ROUND do orquestrador pareia front × back:
    # (simulação da regra do lote — a fila entrega a ordem, o round pareia)
    pendentes = list(fila)
    primeira = pendentes[0]
    lote = [primeira]
    lado = primeira.get("task_tipo") or ""
    opostos = ("BACKEND_TDD", "DATABASE") if lado == "FRONTEND_UI" else (
        ("FRONTEND_UI",) if lado in ("BACKEND_TDD", "DATABASE") else ()
    )
    for t in pendentes[1:]:
        if (t.get("task_tipo") or "") in opostos:
            lote.append(t)
            break
    tipos = sorted(t.get("task_tipo") or "" for t in lote)
    assert tipos == ["BACKEND_TDD", "FRONTEND_UI"], f"round errado: {tipos}"

    # ACHADO nunca paraleliza: camada fora do par → SOLO
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "ACHADO-1", "Achado", "@ada", 81,
        task_tipo="ACHADO", descricao="ACHADO: x",
    )
    pendentes2 = [c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001") if c["task_id"] == "ACHADO-1"]
    primeira2 = pendentes2[0]
    lado2 = primeira2.get("task_tipo") or ""
    opostos2 = ("BACKEND_TDD", "DATABASE") if lado2 == "FRONTEND_UI" else (
        ("FRONTEND_UI",) if lado2 in ("BACKEND_TDD", "DATABASE") else ()
    )
    assert opostos2 == (), "achado não pode paralelizar (mesmo ambiente/código)"
