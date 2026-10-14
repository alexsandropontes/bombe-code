"""Fila de achados — solução atômica (o princípio das tasks, aplicado ao review):

7 achados? O Turing GUARDA os 7, roteia cada um para o agente da especialidade
(front→@ada, banco→@codd, contratos→@ieru, testes→@aniche, arquitetura→@unclebob,
backend→@valim) e corrige UM A UM — tarefinha pequena, dado suficiente do Tech
Lead, zero cegueira. No fim, validação INTEGRAL da story (o review julga o todo).

Anti-invenção: ordem de "corrijam os N achados" SEM a lista = parecer defeituoso
→ o reviewer re-emite. O dev nunca recebe ordem no escuro.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.runner import AgentExecutionResult
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    (tmp_path / "app.py").write_text("def app() -> str:\n    return 'ok'\n", encoding="utf-8")
    return tmp_path, db


def _orch(tmp_path: Path, db: ProjectDatabase) -> WaveOrchestrator:
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-001", title="Story 1", agent="@valim", status="IN_PROGRESS"
    )
    return orch


PARECER_COM_LISTA = (
    "## Veredito\nREJEITADO — corrijam os 3 achados:\n\n"
    "**Bloqueios:**\n"
    "1. ACHADO: coluna origem_id sem foreign key na tabela leituras\n"
    "SOLUÇÃO: crie a FK com ON DELETE CASCADE na migration 0020\n"
    "2. ACHADO: botão salvar sem aria-label no MemoryPanel.vue\n"
    "SOLUÇÃO: adicione aria-label='Salvar memória' ao componente\n"
    "3. ACHADO: dependência domínio→api em publish/service.py\n"
    "SOLUÇÃO: inverta a dependência via porta de publicação\n"
)


def _prompts_por_agente(orch: WaveOrchestrator, saidas: dict[str, str] | None = None):
    capturados: dict[str, list[str]] = {}

    def fake_get_runner(handle):
        capturados.setdefault(handle, [])
        runner = MagicMock()

        def run(prompt, *a, **k):
            capturados[handle].append(prompt)
            saida = (saidas or {}).get(handle, "ok")
            return AgentExecutionResult(agent_handle=handle, success=True, output=saida)

        runner.run.side_effect = run
        return runner

    orch._get_runner = fake_get_runner
    return capturados


def test_fila_roteia_cada_achado_para_o_especialista_e_valida_o_todo(project_env):
    """FILA ÚNICA: os achados NASCEM COMO CARDS no kanban e o ciclo é mandado
    QUEIMAR A FILA na ordem (DOR respeitada). run_execute NÃO queima nada por
    fora — o único processo de queima é a fila do kanban."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    capturados = _prompts_por_agente(orch)
    chamadas_ciclo: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas_ciclo.append(rework_feedback or "inicial")
        if "queime a fila" in (rework_feedback or ""):
            return {"success": True, "message": "conjunto aprovado", "arquivos_escritos": ["a.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": PARECER_COM_LISTA,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    # Os 3 achados nascem COMO CARDS no kanban (única fonte da fila)
    cartoes = orch.db.carregar_tasks_kanban("ONDA-001", "ST-001")
    achado_cards = [c for c in cartoes if c["task_id"].startswith("ACHADO-")]
    assert len(achado_cards) == 3
    assert all(c["task_tipo"] == "ACHADO" for c in achado_cards)
    assert all(c["descricao"] for c in achado_cards), "o texto do achado mora no kanban"
    # Roteamento por especialidade mora NO KANBAN (agent_role da row)
    roteamento = {c["agent_role"] for c in achado_cards}
    assert {"@codd", "@ada", "@unclebob"} <= roteamento
    # run_execute NÃO queima achado por fora: zero prompt de queima fora do ciclo
    assert capturados == {}, "nenhum agente queima fora da fila do kanban"
    # O ciclo foi mandado QUEIMAR A FILA na ordem
    assert any("queime a fila" in c for c in chamadas_ciclo)


def test_ordem_de_achados_sem_lista_obriga_reemissao(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    parecer_sem_lista = "REJEITADO para retrabalho — corrijam os 7 achados e re-submetam."
    capturados = _prompts_por_agente(
        orch,
        saidas={
            "@unclebob": (
                "ACHADO: fetch cru em PublishReport.vue\n"
                "SOLUÇÃO: use o cliente canônico de api\n"
                "ACHADO: testes que abençoam o desvio em tests/api\n"
                "SOLUÇÃO: reescreva a asserção do contrato"
            )
        },
    )
    chamadas_ciclo: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas_ciclo.append(rework_feedback or "inicial")
        if "valide a story INTEIRA" in (rework_feedback or ""):
            return {"success": True, "message": "ok", "arquivos_escritos": ["x.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": parecer_sem_lista,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    # O reviewer foi obrigado a RE-EMITIR com a lista (ACHADO/SOLUÇÃO)
    reemissao = [p for p in capturados["@unclebob"] if "Re-emita" in p or "RE-EMITA" in p]
    assert reemissao, "parecer sem lista passou sem re-emissão — o dev ia inventar"
    # A fila nasceu da lista re-emitida (cards ACHADO no kanban)
    cartoes = orch.db.carregar_tasks_kanban("ONDA-001", "ST-001")
    assert (
        len([c for c in cartoes if c["task_id"].startswith("ACHADO-")]) == 2
    )


def test_sem_lista_e_sem_reemissao_o_feedback_proibe_inventar(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    parecer_sem_lista = "REJEITADO — corrijam os achados."
    _prompts_por_agente(orch, saidas={"@unclebob": ""})
    chamadas_ciclo: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas_ciclo.append(rework_feedback or "inicial")
        if len(chamadas_ciclo) == 2:
            return {"success": True, "message": "ok", "arquivos_escritos": ["fix.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": parecer_sem_lista,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    feedback_reburn = chamadas_ciclo[1]
    assert "NÃO invente correções" in feedback_reburn
    assert "NÃO enumera os achados" in feedback_reburn


def test_roteador_de_achados_por_especialidade(project_env):
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    casos = [
        ("ACHADO: coluna sem FK na tabela leituras", "@codd"),
        ("ACHADO: modal sem foco preso (a11y) no MemoryPanel.vue", "@ada"),
        ("ACHADO: contrato de status patch duplicado entre contratos", "@ieru"),
        ("ACHADO: suíte e2e com mock de rede", "@aniche"),
        ("ACHADO: código morto e duplicação em service.py (DRY)", "@unclebob"),
        ("ACHADO: endpoint PUT ignora validação de payload", "@valim"),
    ]
    for achado, esperado in casos:
        assert orch._agente_para_achado(achado) == esperado, achado


def test_escada_nao_tem_processo_proprio_de_achado(project_env):
    """UMA FILA, UM PROCESSO: a escada de retrabalho NÃO possui caminho próprio
    de achados — nenhum agente é queimado fora da fila do kanban, em degrau
    nenhum. Re-trabalho = nascer cards + o ciclo queimar a fila."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    capturados = _prompts_por_agente(orch)
    chamadas_ciclo: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas_ciclo.append(rework_feedback or "inicial")
        if len(chamadas_ciclo) >= 3:
            return {"success": True, "message": "ok", "arquivos_escritos": ["a.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": PARECER_COM_LISTA,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    # ZERO queima fora da fila — em degrau nenhum (fila única, sem exceção)
    total_fora = sum(len(v) for v in capturados.values())
    assert total_fora == 0, (
        f"queima fora da fila do kanban ({total_fora} chamadas) — segundo processo existente"
    )
    # Os degraus re-invocam O CICLO (que queima a fila), nunca agentes soltos
    assert len(chamadas_ciclo) >= 2


def test_extrator_reconhece_achados_com_solucao():
    from bombe_code.turing.rework import VetoReworkEngine

    motor = VetoReworkEngine()
    achados = motor.extract_blockers(PARECER_COM_LISTA)
    assert len(achados) == 3
    assert achados[0].startswith("ACHADO: coluna origem_id")
    assert achados[2].startswith("ACHADO: dependência")


def test_extrator_reconhece_formato_real_do_tech_lead():
    """Formato REAL dos pareceres (make-books): '**ACHADO 1 (BLOQUEANTE —
    tema):** texto' com número e parêntese antes do dois-pontos. Este teste
    existe porque o extrator antigo só casava 'ACHADO:' — a fila nunca nascia
    e a story repetia em loop."""
    from bombe_code.turing.rework import VetoReworkEngine

    motor = VetoReworkEngine()
    parecer_real = (
        "## Parecer\n"
        "rejeitado para retrabalho — corrijam os achados e re-submetam.\n"
        "### Achados\n"
        "**ACHADO 1 (BLOQUEANTE — Clean Architecture):** domínio `publish/service.py` "
        "importa `REPORT_ITEM_KINDS` de `..api.contracts` (dependência apontando para fora).\n"
        "**ACHADO 2 (DRY):** `PublishReport.vue` usa `fetch()` cru, ignorando o cliente canônico.\n"
        "**ACHADO 3 (não-bloqueante):** `api/contracts.py` monolítico (7+ stories).\n"
        "\n"
        "Escopo da correção: ACHADOS 1 e 2 (~30 linhas em 3 arquivos).\n"
    )
    achados = motor.extract_blockers(parecer_real)
    assert len(achados) == 3, f"extrator perdeu achados: {achados}"
    assert "domínio" in achados[0] and "api.contracts" in achados[0]
    assert "fetch()" in achados[1]
    assert "monolítico" in achados[2]
    # A linha de resumo ("Escopo da correção: ACHADOS 1 e 2...") não vira achado
    assert not any("Escopo" in a for a in achados)


def test_extrator_entende_cabecalho_secao_sem_dois_pontos():
    """Formato REAL dos pareceres por arquivo: '## ACHADO 1 (BLOQUEANTE — tema)'
    sem dois-pontos, descrição no título. O parser antigo exigia ':' e a fila
    nunca nascia — loop da ST-001 parte 2."""
    from bombe_code.turing.rework import VetoReworkEngine

    motor = VetoReworkEngine()
    parecer = (
        "## Parecer\n"
        "**REJEITADO PARA RETRABALHO** — bloqueantes: ACHADOS 1 e 2. Corrigir os 4 achados.\n"
        "## ACHADO 1 (BLOQUEANTE — dado fabricado / contrato front↔back quebrado)\n"
        "o handler fabrica payload que o front nunca envia\n"
        "## ACHADO 2 (BLOQUEANTE — mock fora da estratégia contratada CA-04)\n"
        "vi.mock do vue-router no lugar do router real\n"
        "## ACHADO 3 (texto contratual)\n"
        "wording do CA-02 diverge do PRD\n"
        "## ACHADO 4 (não-bloqueante — cobertura)\n"
        "sem teste para o ramo de erro 422\n"
    )
    achados = motor.extract_blockers(parecer)
    assert len(achados) == 4, f"extrator perdeu achados do formato ##: {achados}"
    assert "BLOQUEANTE — dado fabricado" in achados[0]
    assert "mock fora da estratégia" in achados[1]
    assert "cobertura" in achados[3]


def test_parecer_integral_vem_do_arquivo_apontado_pelo_review(project_env):
    """O reviewer grava o parecer em docs/qa/...md e devolve só o resumo + o
    caminho. A fila precisa do ARQUIVO (achados enumerados), não do resumo."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    parecer_file = tmp_path / "docs" / "qa" / "ST-001_tech_lead_review.md"
    parecer_file.parent.mkdir(parents=True, exist_ok=True)
    parecer_file.write_text(
        "## ACHADO 1 (BLOQUEANTE — front)\nfetch cru no PublishReport.vue\n"
        "## ACHADO 2 (BLOQUEANTE — testes)\ntestes que abençoam o desvio\n",
        encoding="utf-8",
    )
    resumo = (
        "Parecer registrado em `docs/qa/ST-001_tech_lead_review.md`.\n"
        "**Resumo executivo:** Review: REJEITADO PARA RETRABALHO — 2 bloqueantes."
    )
    assert "ACHADO 1" in orch._parecer_da_review(resumo)
    assert "fetch cru" in orch._parecer_da_review(resumo)
    # Sem caminho no output → devolve o próprio output
    assert orch._parecer_da_review("só um resumo") == "só um resumo"


def test_nada_truncado_parecer_longo_chega_inteiro(project_env):
    """LEI: NUNCA, JAMAIS nada enviado a um agente é truncado. Parecer de
    8.000 caracteres deve chegar INTEGRAL no feedback do re-burn (o texto
    antigo era cortado em 6.000/4.000/2.000 — informação truncada = fraude)."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    _prompts_por_agente(orch)
    chamadas_ciclo: list[str] = []
    rechegio = "DETALHE-IMPORTANTE-" + ("x" * 60)

    parecer_longo = (
        "REJEITADO — corrijam os achados:\n\n"
        "**Bloqueios:**\n"
        "1. ACHADO: coluna sem FK em leituras\nSOLUÇÃO: crie a FK\n"
        f"Contexto estendido: {rechegio} {'contexto ' * 900}\n"
    )
    assert len(parecer_longo) > 6000

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas_ciclo.append(rework_feedback or "inicial")
        if len(chamadas_ciclo) == 2:
            # degrau 1 (dirigido, feedback integral) já resolve
            return {"success": True, "message": "ok", "arquivos_escritos": ["a.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": parecer_longo,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle

    res = orch.run_execute(stories=["ST-001"])

    assert res["success"] is True, res.get("error")
    feedback = chamadas_ciclo[1]
    assert rechegio in feedback, "o fim do parecer foi truncado — lei violada"
    assert feedback.count("contexto") >= 900, "trecho do meio sumiu no caminho"


def test_resumo_canonico_da_story_e_o_que_o_agente_recebe(project_env):
    """Regra da @caroli: a story tem a seção '## RESUMO PARA EXECUÇÃO'
    (completo por definição, curto por design). O ciclo envia A SEÇÃO — não
    o texto integral (token) e não um truncamento (lei)."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    story = tmp_path / "docs" / "backlog" / "stories" / "ST-001.md"
    story.parent.mkdir(parents=True, exist_ok=True)
    story.write_text(
        "# ST-001 — Relatório\n\n"
        "## RESUMO PARA EXECUÇÃO\n"
        "Objetivo: relatório pré-publicação com filtro por autor.\n"
        "CAs: 1) botão exporta CSV; 2) 422 sem dados.\n"
        "Armadilha: NÃO usar fetch cru — cliente canônico src/api/client.js.\n"
        "\n"
        "## Contexto estendido\n"
        "prosa longa que NÃO deve ir ao agente " + "palavra " * 300 + "\n",
        encoding="utf-8",
    )
    # força o ciclo a usar a story do arquivo
    prompt_red: list[str] = []

    original_get_runner = orch._get_runner

    def fake_get_runner(handle):
        if handle == "@aniche":
            runner = MagicMock()

            def run(prompt, *a, **k):
                prompt_red.append(prompt)
                return AgentExecutionResult(agent_handle=handle, success=True, output="red")

            runner.run.side_effect = run
            return runner
        return original_get_runner(handle)

    orch._get_runner = fake_get_runner

    def fake_cycle(story_id=None, rework_feedback=None):
        return {"success": True, "message": "ok", "arquivos_escritos": ["a.py"]}

    orch._run_cycle_inner = fake_cycle

    # chama o extrator direto (unidade) + valida regra
    resumo = orch._extrair_resumo_story(story.read_text(encoding="utf-8"))
    assert "RESUMO" in resumo or "Objetivo" in resumo
    assert "cliente canônico" in resumo
    assert "palavra palavra" not in resumo, "o resumo puxou prosa fora da seção"
    assert len(resumo) < 500, "resumo canônico deve ser curto por design"


def test_cards_devolvidos_ao_burn_recebem_precedencia_dos_achados_na_dor(project_env):
    """PRECEDÊNCIA MANDATÓRIA: quando o review reprova e nascem achados para um
    agente, as cards de desenvolvimento desse agente (ex: T4 da @ada) voltam para
    AGUARDANDO_DEV e RECEBEM CADA ACHADO COMO 'dep:' NA SUA DOR. A card só volta a
    queimar quando todos os achados do seu domínio estiverem em DEV DONE."""
    tmp_path, db = project_env
    orch = _orch(tmp_path, db)
    # Cria uma task de dev para @ada em DEV_DONE
    orch.db.criar_task_kanban(
        "ONDA-001",
        "ST-001",
        "ST-001-T4",
        "Interface",
        "@ada",
        3,
        dor=[],
        dod=["gravou_arquivo"],
        task_tipo="FRONTEND_UI",
    )
    orch.db.mover_task_kanban("ONDA-001", "ST-001", "ST-001-T4", "DEV_DONE")

    # Review reprova com achados do front
    parecer = (
        "## Veredito\n"
        "REJEITADO — corrijam os 2 achados:\n\n"
        "**Bloqueios:**\n"
        "1. ACHADO: botão quebrado no modal de front\n"
        "SOLUÇÃO: adicione o handler de clique no componente de front\n"
        "2. ACHADO: aria-label ausente no componente de front\n"
        "SOLUÇÃO: adicione aria-label no componente de front\n"
    )
    chamadas: list[str] = []

    def fake_cycle(story_id=None, rework_feedback=None):
        chamadas.append(rework_feedback or "inicial")
        if "queime a fila" in (rework_feedback or ""):
            return {"success": True, "message": "ok", "arquivos_escritos": ["a.py"]}
        return {
            "success": False,
            "is_blocked": True,
            "error": "REJEIÇÃO",
            "review_output": parecer,
            "arquivos_escritos": [],
        }

    orch._run_cycle_inner = fake_cycle
    orch.run_execute(stories=["ST-001"])

    cards = {c["task_id"]: c for c in orch.db.carregar_tasks_kanban("ONDA-001", "ST-001")}
    t4 = cards["ST-001-T4"]
    assert t4["kanban_status"] == "AGUARDANDO_DEV", "card voltou para o burn"
    achado_ids = [c["task_id"] for c in cards.values() if c["task_id"].startswith("ACHADO-")]
    assert len(achado_ids) >= 1
    for aid in achado_ids:
        assert f"dep:{aid}" in t4["dor"], f"achado {aid} não está declarado na DOR da card devolvida"

