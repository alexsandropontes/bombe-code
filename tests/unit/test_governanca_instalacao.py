"""GOVERNANÇA DE INSTALAÇÃO — falta de ferramenta/dependência NUNCA escala
humano (o usuário pode ser um PM que não instala nada):

- Gate DETERMINÍSTICO no `executar_comando`: instalação local do projeto é
  CAPACIDADE DA PLATAFORMA (forma auditada: pacote único, sem -g, sem sudo,
  sem encadeamento); forma proibida é negada; resto segue a whitelist.
- Bloqueio por falta de ferramenta → Turing classifica e abre task
  PRIORITÁRIA (ordem 0 = PRIMEIRA da fila) roteada pelo PAPEL:
    * ferramenta de infra/ambiente (PostgreSQL, Docker, pandoc…) → @guto
    * biblioteca de aplicação (pacote npm/pip do código) → @unclebob
- A origem ganha `dep:` na DOR: só re-queima quando a instalação está
  DEV DONE (precedência real, fila indiana preservada).
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.runner import AgentExecutionResult
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
    ]


def test_gate_aceita_instalacao_local_auditada(project_env):
    _tmp_path, orch = project_env
    tools = orch._get_project_fs_tools()
    executar = tools[-1]
    # Formas legítimas (execução real: npm falha sem rede? NÃO executamos —
    # validamos só a AUDITORIA; para isso interceptamos o subprocess.
    import bombe_code.turing.orchestrator as orc

    chamadas = {}

    def fake_run(cmd, **kwargs):
        chamadas["cmd"] = cmd
        r = MagicMock()
        r.returncode = 0
        r.stdout = "added 1 package"
        r.stderr = ""
        return r

    original = orc.subprocess.run
    orc.subprocess.run = fake_run
    try:
        resp = executar("npm install -D jsdom")
        assert "exit=0" in resp, resp
        assert chamadas["cmd"] == "npm install -D jsdom"
    finally:
        orc.subprocess.run = original


def test_gate_nega_instalacao_em_forma_proibida(project_env):
    _tmp_path, orch = project_env
    tools = orch._get_project_fs_tools()
    executar = tools[-1]
    # global
    resp = executar("npm install -g jsdom")
    assert "GLOBAL proibida" in resp, resp
    # encadeamento destrutivo
    resp2 = executar("npm install -D jsdom ; rm -rf /")
    assert "Erro" in resp2 and ("encadeamento" in resp2.lower() or "proibida" in resp2.lower())
    # nome de pacote malformado (injeção) — negado por qualquer regra do gate
    resp3 = executar("npm install 'x$(whoami)'")
    assert resp3.startswith("Erro"), resp3


def test_gate_nao_mexe_na_whitelist_normal(project_env):
    _tmp_path, orch = project_env
    tools = orch._get_project_fs_tools()
    executar = tools[-1]
    # fora da whitelist continua negado
    assert "proibida" in executar("curl https://mal.example").lower()
    resp2 = executar("python -c 'ok'")
    assert not resp2.startswith("Erro: programa")


def test_bloqueio_de_dependencia_abre_task_prioritaria_para_o_tech_lead(project_env):
    """@ada bloqueia por jsdom (biblioteca da aplicação) → Turing abre
    INSTALACAO-1 com ordem 0 (primeira da fila) para @unclebob, e a T1
    ganha dep:INSTALACAO-1 na DOR. Zero escalação humana."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())

    res_falho = AgentExecutionResult(
        agent_handle="@ada",
        success=False,
        is_blocked=True,
        block_reason=(
            "MISSING DEPENDENCY — Cannot find dependency 'jsdom' "
            "(npx vitest run: Test Files: no tests). Instalação exige rede."
        ),
    )
    orch._executar_com_card(
        "ONDA-004",
        "ST-001",
        "T1",
        "Tela",
        "@ada",
        1,
        lambda: res_falho,
    )

    cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert "INSTALACAO-1" in cartoes, "task de instalação nasceu no kanban"
    inst = cartoes["INSTALACAO-1"]
    assert inst["ordem"] == 0, "PRIMEIRA da fila"
    assert inst["agent_role"] == "@unclebob", "biblioteca da aplicação → Tech Lead"
    assert inst["kanban_status"] == "AGUARDANDO_DEV"
    # Precedência real: a T1 só re-queima após a instalação DEV DONE
    t1 = cartoes["T1"]
    assert "dep:INSTALACAO-1" in (t1["dor"] or [])
    # A T1 bloqueou pela situação (fica NA coluna EM_DEV)
    assert t1["kanban_status"] == "EM_DEV" and t1["block_tipo"] == "INTERNAL_SCALE"


def test_bloqueio_de_ferramenta_infra_vai_para_o_guto(project_env):
    """Ferramenta de ambiente (PostgreSQL/pandoc/Docker) → @guto (DevOps)."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())

    res_falho = AgentExecutionResult(
        agent_handle="@valim",
        success=False,
        is_blocked=True,
        output="Erro ao executar: command not found: psql — PostgreSQL ausente no ambiente",
    )
    orch._executar_com_card(
        "ONDA-004",
        "ST-001",
        "T1",
        "Tela",
        "@valim",
        1,
        lambda: res_falho,
    )

    cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert "INSTALACAO-1" in cartoes
    assert cartoes["INSTALACAO-1"]["agent_role"] == "@guto", "infra → DevOps (@guto)"


def test_fila_coloca_instalacao_na_frente_e_origem_fora_ate_dev_done(project_env):
    """A fila determinística põe a instalação PRIMEIRA (ordem 0); a origem
    bloqueada NÃO é elegível (dep: pendente) — volta após DEV DONE."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    res_falho = AgentExecutionResult(
        agent_handle="@ada",
        success=False,
        is_blocked=True,
        block_reason="MISSING DEPENDENCY — Cannot find dependency 'jsdom'",
    )
    orch._executar_com_card(
        "ONDA-004", "ST-001", "T1", "Tela", "@ada", 1, lambda: res_falho
    )

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        # fila de burn: instalação é a bola da vez; T1 está fora (dep pendente)
        res = orch._executar_com_card(
            "ONDA-004",
            "ST-001",
            "INSTALACAO-1",
            "Instalar dependência/ambiente",
            "@unclebob",
            0,
            lambda: AgentExecutionResult(
                agent_handle="@unclebob",
                success=True,
                output="npm install -D jsdom → exit=0; npx vitest run → jsdom presente",
            ),
        )
        assert getattr(res, "success", False) is True
        cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
        assert cartoes["INSTALACAO-1"]["kanban_status"] == "DEV_DONE", (
            "instalação DEV DONE por execução/verificação (sem arquivo exigido)"
        )
        # Com a instalação pronta, a DOR da T1 fica satisfeita
        ok, _ = orch._dor_satisfeita(
            cartoes["T1"], orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
        )
        assert ok, "T1 volta a ser elegível após a instalação DEV DONE"
    finally:
        BUS.publish = publicar_original


def test_cota_nunca_dispara_instalacao(project_env):
    """429/cota é PAUSA (infra de provedor), não instalação — não abre task."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    res_cota = AgentExecutionResult(
        agent_handle="@ada",
        success=False,
        is_blocked=True,
        block_reason="HTTP 429: Rate limit reached for requests (cota esgotada)",
    )
    orch._executar_com_card(
        "ONDA-004", "ST-001", "T1", "Tela", "@ada", 1, lambda: res_cota
    )
    cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert not any(tid.startswith("INSTALACAO-") for tid in cartoes), (
        "cota não é impedimento de ambiente"
    )


def test_guto_existe_no_registry_como_devops(project_env):
    _tmp_path, orch = project_env
    agente = orch.registry.get("@guto")
    assert agente is not None, "@guto (SRE & Release Engineering) no registry"
    assert "DevOps" in (agente.role or "") or "SRE" in (agente.role or "")


def test_linha_para_na_instalacao_e_nada_queima_antes_dela(project_env):
    """REGRESSÃO DO BUG REAL (make-books): task bate no jsdom → INSTALACAO
    nasce → o loop NÃO pode delegar a próxima task com o ambiente quebrado.
    A instalação queima EM SEGUIDA (ordem 0), e nada passa na frente dela."""
    tmp_path, orch = project_env
    story_md = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story_md.parent.mkdir(parents=True, exist_ok=True)
    story_md.write_text(
        "# ST-001\n\n## RESUMO PARA EXECUÇÃO\nObjetivo: relatório.\n",
        encoding="utf-8",
    )

    chamadas: list[str] = []

    def fake_get_runner(handle):
        runner = MagicMock()
        contador = {"n": 0}

        def run(prompt=None, **k):
            contador["n"] += 1
            rotulo = f"{handle}#{contador['n']}"
            chamadas.append(rotulo)
            if handle == "@ada" and contador["n"] == 1:
                # 1ª queima da @ada (GREEN do FRONTEND ST-001-T4) bate no jsdom
                return AgentExecutionResult(
                    agent_handle=handle,
                    success=False,
                    is_blocked=True,
                    block_reason=(
                        "MISSING DEPENDENCY — Cannot find dependency 'jsdom'"
                    ),
                )
            if handle == "@unclebob" and contador["n"] == 1:
                # 1ª chamada do Tech Lead = burn da INSTALACAO-1
                return AgentExecutionResult(
                    agent_handle=handle,
                    success=True,
                    output="validado",
                    comandos_executados=["node -e \"require('jsdom')\""],
                )
            return AgentExecutionResult(
                agent_handle=handle,
                success=True,
                output="APROVADO — sem impedimentos.",
                arquivos_escritos=["src/arte.py"],
            )

        runner.run.side_effect = run
        return runner

    orch._get_runner = fake_get_runner

    res = orch._run_cycle_inner("ST-001")

    # NADA queimou entre a falha da @ada e a instalação do Tech Lead.
    assert "@ada#1" in chamadas and "@unclebob#1" in chamadas, f"ordem: {chamadas}"
    idx_ada = chamadas.index("@ada#1")
    idx_inst = chamadas.index("@unclebob#1")
    assert idx_ada < idx_inst, f"instalação não veio depois da falha: {chamadas}"
    entre = chamadas[idx_ada + 1 : idx_inst]
    assert not entre, f"queimou no ambiente quebrado antes da instalação: {entre}"
    cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cartoes["INSTALACAO-1"]["kanban_status"] == "DEV_DONE"
    assert cartoes["INSTALACAO-1"]["ordem"] == 0
    assert cartoes["INSTALACAO-1"]["agent_role"] == "@unclebob"
    # O ciclo terminou honesto: story bloqueada (task não finalizada no ambiente)
    assert res.get("success") is False and res.get("is_blocked") is True


def test_zero_suposicao_dependente_nao_entra_na_fila_por_simulacao(project_env):
    """ZERO SUPOSIÇÃO: a fila NÃO libera dependente por simulação ('vou
    queimar a instalação aqui'). A T4 só é elegível quando a instalação está
    REALMENTE em DEV DONE no banco — queima no ambiente quebrado, nunca mais."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "INSTALACAO-1",
        "Instalar jsdom",
        "@unclebob",
        0,
        task_tipo="INSTALACAO",
    )
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "ST-001-T9",
        "Tela que usa jsdom",
        "@ada",
        9,
        dor=["dep:INSTALACAO-1"],
    )
    fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    ids = [t["task_id"] for t in fila]
    assert "INSTALACAO-1" in ids, "instalação pendente é a primeira da fila"
    assert "ST-001-T9" not in ids, "dependente NÃO entra por suposição — só com DEV DONE real"


def test_dod_da_instalacao_exige_validacao_rodando(project_env):
    """DOD REAL (doutrina da VALIDAÇÃO): a prova da instalação é o TESTE
    (import/require da biblioteca) executado pela ferramenta com exit 0 —
    não o `npm install` em si (instalou ≠ roda). Cobre os três casos:
    instalou agora · já estava instalado (só o teste roda) · reinstalou."""
    from bombe_code.agents.runner import AgentExecutionResult
    from bombe_code.turing.ambiente import verificar_instalacao

    # Prosa de mentira + registro vazio = FALHA (a plataforma não executou nada)
    mentira = AgentExecutionResult(
        agent_handle="@unclebob",
        success=True,
        output="Rodei npm install -D jsdom e passou. Deve funcionar.",
        comandos_executados=[],
    )
    assert verificar_instalacao(getattr(mentira, "comandos_executados", [])) is False
    # JÁ ESTAVA INSTALADO: nenhuma instalação rodou — só o TESTE de validação
    # executado pela ferramenta com exit 0 → evidência suficiente
    ja_estava = AgentExecutionResult(
        agent_handle="@unclebob",
        success=True,
        output="jsdom já presente — validação verde",
        comandos_executados=["node -e \"require('jsdom')\""],
    )
    assert verificar_instalacao(getattr(ja_estava, "comandos_executados", [])) is True
    # Guarda: só exit 0 é registrado (tool layer)
    from bombe_code.permissions.acao_guard import GuardaDeAcoes

    g = GuardaDeAcoes()
    g.registrar_comando_executado("node -e \"require('jsdom')\"", 1)
    assert g.comandos_executados() == [], "exit != 0 não é evidência"
    g.registrar_comando_executado("node -e \"require('jsdom')\"", 0)
    assert g.comandos_executados() == ["node -e \"require('jsdom')\""]


def test_guarda_só_registra_instalacao_com_exit_zero():
    """CONTRATO DA EVIDÊNCIA (platform-side): o registro de instalação só
    aceita exit code 0 — comando auditado que falhou NÃO é evidência. É este
    registro que alimenta `comandos_executados` do AgentExecutionResult e o
    DOD da card de INSTALACAO; a LLM não tem como forjá-lo."""
    from bombe_code.permissions.acao_guard import GuardaDeAcoes

    g = GuardaDeAcoes()
    g.registrar_comando_executado("node -e \"require('jsdom')\"", 0)
    g.registrar_comando_executado("uv add httpx", 0)
    g.registrar_comando_executado("npm ls jsdom", 3)
    g.registrar_comando_executado("   ", 0)
    assert g.comandos_executados() == [
        "node -e \"require('jsdom')\"",
        "uv add httpx",
    ]


def test_achado_queima_pela_fila_respeitando_dor_da_instalacao(project_env):
    """REGRESSÃO DO BUG REAL DO RESUME: achado com dep: da instalação NÃO pode
    queimar antes da INSTALACAO (ordem 0). FILA ÚNICA: a fila do kanban segura
    o achado até a instalação estar DEV DONE de verdade."""
    tmp_path, orch = project_env
    story_md = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story_md.parent.mkdir(parents=True, exist_ok=True)
    story_md.write_text(
        "# ST-001\n\n## RESUMO PARA EXECUÇÃO\nObjetivo: relatório.\n",
        encoding="utf-8",
    )
    # ACHADO no kanban com DEP da instalação (ordem 81 — depois da instalação)
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "INSTALACAO-1",
        "Instalar jsdom",
        "@unclebob",
        0,
        task_tipo="INSTALACAO",
    )
    orch.db.criar_task_kanban(
        "ONDA-004",
        "ST-001",
        "ACHADO-ST-001-1",
        "Achado do review",
        "@ada",
        81,
        dor=["dep:INSTALACAO-1"],
        task_tipo="ACHADO",
        descricao="ACHADO: botão sem aria-label\nSOLUÇÃO: adicione aria-label",
    )

    ordem_queima: list[str] = []

    def fake_get_runner(handle):
        runner = MagicMock()
        contador = {"n": 0}

        def run(prompt=None, **k):
            contador["n"] += 1
            ordem_queima.append(handle)
            if handle == "@unclebob":
                return AgentExecutionResult(
                    agent_handle=handle,
                    success=True,
                    output="jsdom presente — validação verde",
                    comandos_executados=["node -e \"require('jsdom')\""],
                )
            return AgentExecutionResult(
                agent_handle=handle,
                success=True,
                output="corrigido",
                arquivos_escritos=["src/fix.py"],
            )

        runner.run.side_effect = run
        return runner

    orch._get_runner = fake_get_runner
    orch._run_cycle_inner("ST-001")

    # FILA ÚNICA: instalação (ordem 0) queima ANTES do achado (ordem 81, com dep)
    assert "@unclebob" in ordem_queima and "@ada" in ordem_queima, (
        f"fila não queimou as duas: {ordem_queima}"
    )
    assert ordem_queima.index("@unclebob") < ordem_queima.index("@ada"), (
        f"achado queimou antes da instalação: {ordem_queima}"
    )
    cartoes = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")}
    assert cartoes["ACHADO-ST-001-1"]["kanban_status"] == "DEV_DONE"


def test_resume_sem_dev_card_nao_acorda_o_aniche(project_env):
    """O RELÓGIO: resume com fila só de INSTALACAO/ACHADO (nada de dev novo) —
    o @aniche NEM ACORDA. Suíte existente é o contrato; reescrever teste em
    resume é reaproveitar linha de montagem parada. Zero chamadas."""
    tmp_path, orch = project_env
    story_md = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story_md.parent.mkdir(parents=True, exist_ok=True)
    story_md.write_text(
        "# ST-001\n\n## RESUMO PARA EXECUÇÃO\nObjetivo: relatório.\n",
        encoding="utf-8",
    )
    # Story JÁ queimada (resume real): o breakdown canônico do decompose
    # (mesmo nascido pelo ciclo) está TODO em DEV DONE + instalação/achado
    from bombe_code.turing.pbb import PBBDecomposer

    orch._garcom_preparar_tasks(
        "ONDA-004",
        "ST-001",
        PBBDecomposer.decompose_story(
            story_id="ST-001",
            story_title="Story 1",
            requires_db=True,
            requires_frontend=True,
        ),
    )
    for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001"):
        if not c["task_id"].startswith(("INSTALACAO", "ACHADO", "REVIEW")):
            orch.db.mover_task_kanban("ONDA-004", "ST-001", c["task_id"], "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "INSTALACAO-1", "Instalar jsdom", "@unclebob", 0,
        task_tipo="INSTALACAO",
    )
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "ACHADO-ST-001-1", "Achado", "@ada", 81,
        dor=["dep:INSTALACAO-1"], task_tipo="ACHADO",
        descricao="ACHADO: botão sem aria-label\nSOLUÇÃO: adicione aria-label",
    )

    chamadas: list[str] = []

    def fake_get_runner(handle):
        runner = MagicMock()
        contador = {"n": 0}

        def run(prompt=None, **k):
            contador["n"] += 1
            chamadas.append(f"{handle}#{contador['n']}")
            if handle == "@unclebob":
                return AgentExecutionResult(
                    agent_handle=handle,
                    success=True,
                    output="validado",
                    comandos_executados=["node -e \"require('jsdom')\""],
                )
            return AgentExecutionResult(
                agent_handle=handle,
                success=True,
                output="corrigido",
                arquivos_escritos=["src/fix.py"],
            )

        runner.run.side_effect = run
        return runner

    orch._get_runner = fake_get_runner
    orch._run_cycle_inner("ST-001")

    # ANICHE ZERA: nada na fila precisa de teste novo (suíte não é reescrita)
    assert not any(c.startswith("@aniche#") for c in chamadas), (
        f"aniche acordou fora da hora: {chamadas}"
    )
    # A fila queimou na ordem: instalação → achado (precedência respeitada)
    assert "@unclebob#1" in chamadas and "@ada#1" in chamadas, f"fila: {chamadas}"
    assert chamadas.index("@unclebob#1") < chamadas.index("@ada#1")


def test_review_nunca_entra_na_fila_de_queima(project_env):
    """REVIEW NUNCA é task de dev: com all_burn_done satisfeito (todas as
    tasks DEV DONE), a card REVIEW-TECH continua FORA da fila — quem a queima
    é o passo de review (gate próprio). Nunca mais aniche escrevendo teste
    pra code review."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "DEV_DONE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "REVIEW-TECH", "Code Review da story", "@unclebob",
        90, dor=["all_burn_done"], task_tipo="REVIEW",
    )

    fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001")
    assert "REVIEW-TECH" not in [t["task_id"] for t in fila], (
        "REVIEW entrou na fila de queima — absurdo: dev 'implementaria review'"
    )


def test_primeira_queima_aniche_escreve_com_card_ja_em_dev(project_env):
    """A QUEIMA COMEÇA NO RED: na primeira queima da story (suíte inexistente),
    quando o @aniche escreve, a card DEV JÁ ESTÁ EM_DEV no kanban — a queima
    não começa quando o dev bota a mão no código."""
    tmp_path, orch = project_env
    story_md = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story_md.parent.mkdir(parents=True, exist_ok=True)
    story_md.write_text(
        "# ST-001\n\n## RESUMO PARA EXECUÇÃO\nObjetivo: relatório.\n",
        encoding="utf-8",
    )
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    status_no_red: list[str] = []

    def fake_get_runner(handle):
        runner = MagicMock()

        def run(prompt=None, **k):
            if handle == "@aniche":
                # qual task está queimando neste RED (prompt: 'TAREFA ATUAL: ...')
                import re as _re

                if "APENAS os testes" not in (prompt or ""):
                    return AgentExecutionResult(
                        agent_handle=handle, success=True, output="Veredito: APROVADO"
                    )
                tid_red = _re.search(r"TAREFA ATUAL: \[[^\]]+\] ([^\n]+)", prompt or "")
                titulo_red = tid_red.group(1).strip() if tid_red else ""
                cartoes = {
                    c["title"]: c
                    for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
                }
                alvo = cartoes.get(titulo_red)
                status_no_red.append((titulo_red, alvo["kanban_status"] if alvo else "?"))
                return AgentExecutionResult(
                    agent_handle=handle,
                    success=True,
                    output="Testes falhando (RED)",
                )
            return AgentExecutionResult(
                agent_handle=handle,
                success=True,
                output="implementado",
                arquivos_escritos=["src/tela.py"],
            )

        runner.run.side_effect = run
        return runner

    orch._get_runner = fake_get_runner
    orch._run_cycle_inner("ST-001")

    # O RED roda UMA vez (latch do relógio) e a card queimando JÁ ESTÁ EM_DEV
    assert len(status_no_red) == 1, f"aniche acordou mais de uma vez: {status_no_red}"
    titulo_red, status_red = status_no_red[0]
    assert status_red == "EM_DEV", (
        f"card '{titulo_red}' não estava EM_DEV quando o aniche escreveu ({status_red})"
    )


def test_suite_existente_reburn_nao_acorda_o_aniche(project_env):
    """RE-BURN/RESUME COM SUÍTE EXISTENTE: a suíte é o contrato — o aniche não
    re-escreve nada; o dev vai direto pro GREEN contra a suíte. A revalidação
    é papel do REVIEW-QA."""
    tmp_path, orch = project_env
    story_md = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story_md.parent.mkdir(parents=True, exist_ok=True)
    story_md.write_text(
        "# ST-001\n\n## RESUMO PARA EXECUÇÃO\nObjetivo: relatório.\n",
        encoding="utf-8",
    )
    # Suíte da story JÁ EXISTE (artefato da primeira queima)
    pasta = tmp_path / "tests"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "test_st001_publica_relatorio.aniche.py").write_text(
        "def test_cenario():\n    assert True\n", encoding="utf-8"
    )
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "DEV_DONE")
    # T3 devolvida ao burn (re-burn por achado) — suíte existe

    chamadas: list[str] = []

    def fake_get_runner(handle):
        runner = MagicMock()
        contador = {"n": 0}

        def run(prompt=None, **k):
            contador["n"] += 1
            chamadas.append(f"{handle}#{contador['n']}")
            return AgentExecutionResult(
                agent_handle=handle,
                success=True,
                output="ok",
                arquivos_escritos=["src/fix.py"],
            )

        runner.run.side_effect = run
        return runner

    prompts_aniche: list[str] = []
    base_get = fake_get_runner

    def fake_get_runner_com_prompts(handle):
        runner = base_get(handle)
        run_original = runner.run

        def run_com_prompts(prompt=None, **k):
            if handle == "@aniche":
                prompts_aniche.append(prompt or "")
            return run_original(prompt, **k)

        runner.run = run_com_prompts
        return runner

    orch._get_runner = fake_get_runner_com_prompts
    orch._run_cycle_inner("ST-001")

    reds = [p for p in prompts_aniche if "APENAS os testes" in p]
    assert not reds, f"aniche re-escreveu teste com suíte existente: {len(reds)} RED(s)"


def test_ambiente_ja_validado_nao_nova_instalacao(project_env):
    """ANTI-ARMADILHA (o bug real do resume): card blocked cuja evidência
    MENCIONA jsdom/document, com INSTALACAO-1 já DEV DONE (ambiente provado
    com teste), NÃO nasce INSTALACAO-2 — a DOR já resolvida não renasce. A
    falha é impedimento real da card (flag), a linha para nele."""
    _tmp_path, orch = project_env
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "INSTALACAO-1", "Instalar jsdom", "@unclebob", 0,
        task_tipo="INSTALACAO",
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "INSTALACAO-1", "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "ACHADO-2", "Achado de UI", "@ada", 81,
        task_tipo="ACHADO", descricao="ACHADO: aria-label",
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "ACHADO-2", "EM_DEV")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "ACHADO-2", "INTERNAL_SCALE")

    resultado = orch._abrir_task_instalacao(
        "ONDA-004",
        "ST-001",
        "ACHADO-2",
        "vitest falhou: document is not defined em LibraryView.spec.js",
    )

    assert resultado is None, "ambiente já validado: nenhuma instalação nova"
    ids = [c["task_id"] for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")]
    assert "INSTALACAO-2" not in ids, "a DOR já resolvida renasceu (a armadilha)"


def test_primeira_falta_de_dependencia_ainda_nasce_instalacao(project_env):
    """O caso LEGÍTIMO continua: ambiente sem INSTALACAO DEV DONE prévia +
    evidência de dependência ausente = nasce a card prioritária (ordem 0)."""
    _tmp_path, orch = project_env
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "ST-001-T1", "Tarefa", "@ada", 1,
        task_tipo="FRONTEND_UI",
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "ST-001-T1", "EM_DEV")
    orch.db.bloquear_task_kanban("ONDA-004", "ST-001", "ST-001-T1", "INTERNAL_SCALE")

    resultado = orch._abrir_task_instalacao(
        "ONDA-004", "ST-001", "ST-001-T1",
        "MISSING DEPENDENCY — Cannot find dependency 'jsdom'",
    )

    assert resultado == "INSTALACAO-1"
    ids = [c["task_id"] for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")]
    assert "INSTALACAO-1" in ids
