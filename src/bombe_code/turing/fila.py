"""FILA DO KANBAN (SRP — uma responsabilidade: a fila de queima).

O kanban é a ÚNICA fonte da verdade: esta classe lê e escreve SOMENTE nele —
nascimento (preparar), elegibilidade (DOR 100%), ordem de execução, acordar
com bola da vez, devolver-para-burn e a fila de achados (cards ACHADO).
Zero task em memória, zero fallback, zero legado."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from bombe_code.turing.progress import BUS


class KanbanLeitura:
    """LEITURA-RO do kanban para a TELA: `mode=ro`, busy_timeout, sem
    migração, sem escrita — a tela NUNCA escreve no banco do processo e
    NUNCA o trava. Implementa o MESMO contrato que o núcleo consome
    (carregar_tasks_kanban / buscar_task_kanban / stories_da_onda): uma
    coisa só — a tela lê as mesmas rows, pela mesma regra."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _con(self) -> Any:
        import sqlite3

        con = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True, timeout=1.0)
        con.row_factory = sqlite3.Row
        return con

    def carregar_tasks_kanban(self, wave_id: str, story_id: str) -> list[dict]:
        try:
            with self._con() as con:
                rows = con.execute(
                    """
                    SELECT id, story_id, agent_role, title, task_id, ordem,
                           kanban_status, block_tipo, dor_json, dod_json,
                           task_tipo, descricao, updated_at
                    FROM agent_tasks
                    WHERE wave_id = ? AND story_id = ? AND task_id != ''
                    ORDER BY ordem, task_id
                    """,
                    (wave_id, story_id),
                ).fetchall()
                cartoes = []
                for r in rows:
                    c = dict(r)
                    c["dor"] = json.loads(c.pop("dor_json", "[]") or "[]")
                    c["dod"] = json.loads(c.pop("dod_json", "[]") or "[]")
                    cartoes.append(c)
                return cartoes
        except Exception:  # noqa: BLE001 — tela nunca derruba o app por leitura
            return []

    def buscar_task_kanban(self, wave_id: str, task_id: str) -> dict | None:
        try:
            with self._con() as con:
                row = con.execute(
                    "SELECT id, story_id, agent_role, title, task_id, ordem, "
                    "       kanban_status, block_tipo, dor_json, dod_json, "
                    "       task_tipo, descricao, updated_at "
                    "FROM agent_tasks WHERE wave_id = ? AND task_id = ? LIMIT 1",
                    (wave_id, task_id),
                ).fetchone()
                if row is None:
                    return None
                c = dict(row)
                c["dor"] = json.loads(c.pop("dor_json", "[]") or "[]")
                c["dod"] = json.loads(c.pop("dod_json", "[]") or "[]")
                return c
        except Exception:  # noqa: BLE001
            return None

    def stories_da_onda(self, wave_id: str) -> list[str]:
        try:
            with self._con() as con:
                rows = con.execute(
                    "SELECT DISTINCT story_id FROM agent_tasks "
                    "WHERE wave_id = ? AND task_id != '' ORDER BY story_id",
                    (wave_id,),
                ).fetchall()
                return [r["story_id"] for r in rows]
        except Exception:  # noqa: BLE001
            return []


def fila_da_story(
    db: Any, wave_id: str, story_id: str, anunciar: bool = True
) -> tuple[list[dict], list[dict]]:
    """O NÚCLEO ÚNICO de leitura do kanban (usado pelo processo E pela tela).

    UMA regra: a esteira hierárquica do kanban — tarefas raízes por ordem canônica
    (ordem, task_id) e suas subtasks/dependências aninhadas recursivamente logo abaixo.
    A fila de execução seleciona estritamente os nós da árvore com a DOR 100% ATENDIDA
    no estado real do banco.

    Retorna (fila_na_ordem_do_kanban, todos_os_cartoes)."""
    cartoes = db.carregar_tasks_kanban(wave_id, story_id)

    # 1. Avaliação de DOR de cada cartão contra o estado real do banco
    def _dor_avaliada(c: dict) -> tuple[bool, str]:
        for item in c.get("dor") or []:
            if item.startswith("dep:"):
                alvo = next((x for x in cartoes if x["task_id"] == item[4:]), None)
                if alvo is None:
                    alvo = db.buscar_task_kanban(wave_id, item[4:])
                if alvo is None or alvo["kanban_status"] not in (
                    "DEV_DONE",
                    "DONE_DEFINITIVO",
                ):
                    return False, item
            elif item == "all_burn_done":
                tasks = [x for x in cartoes if not x["task_id"].startswith("REVIEW")]
                if not tasks or not all(
                    x["kanban_status"] in ("DEV_DONE", "DONE_DEFINITIVO") for x in tasks
                ):
                    return False, item
        return True, ""

    # 2. Grafo de hierarquia universal (se Y declara 'dep:X', X é o pré-requisito pai de Y)
    children_of: dict[str, list[str]] = {}
    parent_of: dict[str, str] = {}
    ids_da_story = {c["task_id"] for c in cartoes}
    for c in cartoes:
        tid = c["task_id"]
        deps = [it[4:] for it in c.get("dor") or [] if it.startswith("dep:")]
        deps_internas = [d for d in deps if d in ids_da_story]
        if deps_internas:
            # As tarefas em deps_internas precedem tid (tid é filho dentro da story)
            primeiro_pai = deps_internas[0]
            children_of.setdefault(primeiro_pai, []).append(tid)
            parent_of[tid] = primeiro_pai

    # 3. Construção da esteira em árvore canônica
    roots = [c for c in cartoes if c["task_id"] not in parent_of]
    roots.sort(key=lambda c: (c["ordem"], c["task_id"]))

    arvore: list[dict] = []

    def _visitar(c: dict, depth: int) -> None:
        c_item = dict(c)
        c_item["depth"] = depth
        dok, faltante = _dor_avaliada(c)
        c_item["_dor_ok"] = dok
        c_item["_faltante"] = faltante
        arvore.append(c_item)
        # Visita filhos diretos ordenados
        ch_ids = children_of.get(c["task_id"], [])
        ch_cards = [x for x in cartoes if x["task_id"] in ch_ids]
        ch_cards.sort(key=lambda x: (x["ordem"], x["task_id"]))
        for ch in ch_cards:
            _visitar(ch, depth + 1)

    for r in roots:
        _visitar(r, 0)

    # 4. Elegíveis para execução neste turno (exclui concluídos, reviews e quem não tem DOR)
    elegiveis: list[dict] = []
    for item in arvore:
        if item["kanban_status"] in ("DEV_DONE", "DONE_DEFINITIVO"):
            if anunciar:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=f"✓ {story_id} {item['task_id']} DEV DONE (ignoro no resume).",
                )
            continue
        if item["task_id"].startswith("REVIEW"):
            if anunciar and not item["_dor_ok"]:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🚪 PRECEDÊNCIA — {story_id} {item['task_id']} "
                        f"AGUARDA {item['_faltante']} (revisão só queima com tarefas concluídas)."
                    ),
                )
            continue
        if item["_dor_ok"]:
            elegiveis.append(item)
        elif anunciar:
            faltante = item["_faltante"]
            if faltante.startswith("dep:"):
                alvo_dep = db.buscar_task_kanban(wave_id, faltante[4:])
                if alvo_dep and alvo_dep["story_id"] != story_id:
                    BUS.publish(
                        "announcement",
                        agent="@turing",
                        text=(
                            f"⚠️ FALHA DE PLANEJAMENTO — {story_id} {item['task_id']} "
                            f"depende de {faltante[4:]} (story {alvo_dep['story_id']}) "
                            "ainda não concluída."
                        ),
                    )
            BUS.publish(
                "announcement",
                agent="@turing",
                text=f"🚪 DOR — {story_id} {item['task_id']} aguarda: {faltante}.",
            )

    # ANDON: Tarefas bloqueadas com DOR satisfeita e ACHADOS têm precedência imediata de tratamento
    # (achados de review corrigem a base antes do burn continuar; a linha não queima tarefas dependentes às cegas)
    achados_fila = [x for x in elegiveis if x.get("task_tipo") == "ACHADO" or x.get("task_id", "").startswith("ACHADO-")]
    blockeds = [x for x in elegiveis if x.get("block_tipo") and x not in achados_fila]
    livres = [x for x in elegiveis if not x.get("block_tipo") and x not in achados_fila]
    elegiveis = achados_fila + blockeds + livres

    return elegiveis, arvore


def quadro_da_onda(db: Any, wave_id: str) -> list[dict]:
    """A LEITURA QUE A TELA CONSOME — A MESMA do processo (fila_da_story),
    onda inteira, na ordem hierárquica do kanban. Zero segundo caminho:
    o que a tela mostra É o que o Turing queima. Cada row: story_id, task_id,
    title, kanban_status, block_tipo, task_tipo, na_fila, proxima,
    em_queima, depth, updated_at."""
    import time
    agora = time.time()
    rows: list[dict] = []
    story_ids = db.stories_da_onda(wave_id)

_PAR_FRONTE = "FRONTEND_UI"
_PAR_TRAS = ("BACKEND_TDD", "DATABASE")


def resolver_camada(c: dict) -> str:
    """Classifica a camada da task para fins de paralelismo ortogonal."""
    tipo = c.get("task_tipo") or ""
    if tipo in (_PAR_FRONTE, *_PAR_TRAS):
        return tipo
    if tipo in ("ACHADO", "INSTALACAO", "REVIEW") or c.get("task_id", "").startswith(
        ("ACHADO-", "INSTALACAO-", "REVIEW-")
    ):
        return tipo
    ag = c.get("agent_role") or ""
    if ag in ("@ada", "@norman"):
        return _PAR_FRONTE
    if ag in ("@valim", "@barbara", "@james", "@scott", "@ryan", "@codd", "@eliot"):
        return "BACKEND_TDD"
    t = (c.get("title") or "").lower()
    if any(k in t for k in ("modal", "front", "interface", "ui", "view", "component", "acessibilidade")):
        return _PAR_FRONTE
    if any(k in t for k in ("rota", "api", "schema", "banco", "contrato", "backend", "migrations")):
        return "BACKEND_TDD"
    return tipo


def montar_lote_turno(candidatos: list[dict]) -> list[dict]:
    """Regra de ouro única de lote do turno:
    - Se a 1ª for INSTALACAO / ACHADO / REVIEW / solo: lote de 1 (fila indiana).
    - Se for de camada FRONTEND vs BACKEND/DB: até 1 par ortogonal em paralelo."""
    if not candidatos:
        return []
    primeira = candidatos[0]
    lote = [primeira]
    if not (
        primeira.get("task_tipo") == "INSTALACAO"
        or primeira["task_id"].startswith("INSTALACAO-")
        or primeira.get("task_tipo") == "ACHADO"
        or primeira["task_id"].startswith("ACHADO-")
        or primeira.get("task_tipo") == "REVIEW"
        or primeira["task_id"].startswith("REVIEW-")
    ):
        lado_p = resolver_camada(primeira)
        if lado_p == _PAR_FRONTE:
            opostos = _PAR_TRAS
        elif lado_p in _PAR_TRAS:
            opostos = (_PAR_FRONTE,)
        else:
            opostos = ()
        if opostos:
            for cand in candidatos[1:]:
                if resolver_camada(cand) in opostos:
                    lote.append(cand)
                    break
    return lote


def quadro_da_onda(db: Any, wave_id: str) -> list[dict]:
    """A LEITURA QUE A TELA CONSOME — A MESMA do processo (fila_da_story),
    onda inteira, na ordem hierárquica do kanban. Zero segundo caminho:
    o que a tela mostra É o que o Turing queima. Cada row: story_id, task_id,
    title, kanban_status, block_tipo, task_tipo, na_fila, proxima,
    em_queima, depth, updated_at."""
    import time
    agora = time.time()
    rows: list[dict] = []
    story_ids = db.stories_da_onda(wave_id)

    for story_id in story_ids:
        fila, arvore = fila_da_story(db, wave_id, story_id, anunciar=False)
        ids_fila = [c["task_id"] for c in fila]

        # Lote de queima ativa: espelha EXATAMENTE o lote do turno do orchestrator!
        # Se existem tarefas que já foram acordadas para EM_DEV (sem block), elas são o lote em burn ativo.
        # Caso contrário, o lote em burn ativo é a próxima elegível da fila (com eventual par paralelo).
        em_dev_ativos = [
            c for c in arvore
            if c["kanban_status"] == "EM_DEV" and not c.get("block_tipo")
        ]
        candidatos_queima = em_dev_ativos if em_dev_ativos else fila
        lote_ativo = montar_lote_turno(candidatos_queima)
        ids_em_queima = {c["task_id"] for c in lote_ativo}

        ha_espera = any(
            r["kanban_status"] not in ("DEV_DONE", "DONE_DEFINITIVO") for r in arvore
        )

        for c in arvore:
            st = c["kanban_status"]
            if st == "DONE_DEFINITIVO":
                continue
            if st == "DEV_DONE" and ha_espera and agora - float(c.get("updated_at") or 0) > 60:
                continue

            rows.append(
                {
                    "story_id": c["story_id"],
                    "task_id": c["task_id"],
                    "title": c["title"],
                    "kanban_status": c["kanban_status"],
                    "block_tipo": c["block_tipo"],
                    "task_tipo": c["task_tipo"],
                    "na_fila": c["task_id"] in ids_fila,
                    "proxima": bool(ids_fila) and c["task_id"] == ids_fila[0],
                    "em_queima": c["task_id"] in ids_em_queima,
                    "depth": c.get("depth", 0),
                    "updated_at": c.get("updated_at") or 0,
                }
            )

    return rows


class FilaDoKanban:
    def __init__(
        self,
        db: Any,
        wave_provider: Callable[[], str],
        mapa_camada: dict[str, str],
        roteador_achado: Callable[[str], str],
    ) -> None:
        self.db = db
        self.wave_provider = wave_provider
        self.mapa_camada = mapa_camada
        self.roteador_achado = roteador_achado

    @property
    def wave_id(self) -> str:
        return self.wave_provider()

    # ── NASCIMENTO ──
    def preparar(self, onda_id: str, story_id: str, tarefas: list[Any]) -> None:
        """Braço ESCRITOR: a task nasce NO KANBAN, designada e ordenada, ANTES
        de qualquer agente acordar — com REGRAS DE DOR (entrada, incluindo a
        PRECEDÊNCIA via depends_on como item 'dep:') e DOD (saída). Cards
        EM DEV/DEV DONE/DONE DEFINITIVO/BLOCKED não são tocados."""
        for ordem, t in enumerate(tarefas):
            agente = self.mapa_camada.get(t.task_type.value, "@valim")
            existentes = {c["task_id"]: c for c in self.db.carregar_tasks_kanban(onda_id, story_id)}
            cartao = existentes.get(t.id)
            if cartao is None:
                dor = [
                    "especificação e regras de negócio disponíveis",
                    "BDD/RED-GREEN definido para a task",
                ] + [f"dep:{dep}" for dep in (t.depends_on or [])]
                dod = ["gravou_arquivo", "implementação atende os testes da task"]
                self.db.criar_task_kanban(
                    onda_id,
                    story_id,
                    t.id,
                    t.title,
                    agente,
                    ordem,
                    dor=dor,
                    dod=dod,
                    task_tipo=t.task_type.value,
                    descricao=(t.problema_unico or t.description or ""),
                )
                self.db.mover_task_kanban(onda_id, story_id, t.id, "AGUARDANDO_DEV")
            elif cartao["kanban_status"] == "BACKLOG":
                self.db.mover_task_kanban(onda_id, story_id, t.id, "AGUARDANDO_DEV")

    # ── DOR (entrada) ──
    def dor_satisfeita(self, cartao: dict, cartoes: list[dict]) -> tuple[bool, str]:
        """Avalia a DOR de um card ITEM A ITEM (determinístico). REGRAS:
        DOR 100% ATENDIDA para a card ser pega pra EM DEV — sem exceção; e
        para sair do blocked e voltar a atuar, de novo: 100%.

        Itens: 'dep:{task_id}' — precedência: card alvo em DEV DONE/DONE
        DEFINITIVO (procurada PRIMEIRO na story, DEPOIS em toda a ONDA:
        dependência entre stories vale precedência — se S2T1 depende de
        S1T3, a story 1 é entregue antes da story 2 começar); 'all_burn_done'
        — todas as tasks de burn prontas; demais = estáticos (satisfeitos no
        breakdown; faltando em execução viram blocked HUMAN_SCALE pelo
        próprio agente — a informação que causou o blocked é item de DOR
        para voltar a atuar)."""
        onda = self.wave_id
        for item in cartao.get("dor") or []:
            if item.startswith("dep:"):
                alvo = next((c for c in cartoes if c["task_id"] == item[4:]), None)
                if alvo is None:
                    alvo = self.db.buscar_task_kanban(onda, item[4:])
                if alvo is None or alvo["kanban_status"] not in (
                    "DEV_DONE",
                    "DONE_DEFINITIVO",
                ):
                    return False, item
            elif item == "all_burn_done":
                tasks = [c for c in cartoes if not c["task_id"].startswith("REVIEW")]
                if not tasks or not all(
                    c["kanban_status"] in ("DEV_DONE", "DONE_DEFINITIVO") for c in tasks
                ):
                    return False, item
        return True, ""

    # ── A FILA ──
    def carregar(self, onda_id: str, story_id: str) -> tuple[list[dict], list[dict]]:
        """A fila DELEGA ao NÚCLEO ÚNICO (fila_da_story): estado REAL do
        banco, zero suposição. O processo RELÊ a fila do kanban após cada
        queima — uma card só libera dependente quando está REALMENTE em
        DEV DONE. Cards com 🚩 estão fora da fila até o desbloqueio."""
        return fila_da_story(self.db, onda_id, story_id)

    def desbloquear_apos_instalacao(
        self, onda_id: str, story_id: str, instalacao_task_id: str
    ) -> int:
        """A INSTALAÇÃO chegou a DEV DONE (evidência REAL): a informação que
        causou os blocks de ambiente EXISTE — as cards flagged cuja DOR é
        `dep:{instalacao}` são DESBLOQUEADAS (a flag morre) e voltam à fila
        na próxima leitura. Determinístico, kanban-only, sem suposição."""
        desbloqueadas = 0
        for c in self.db.carregar_tasks_kanban(onda_id, story_id):
            if not c["block_tipo"]:
                continue
            if f"dep:{instalacao_task_id}" in (c.get("dor") or []):
                self.db.desbloquear_task_kanban(onda_id, story_id, c["task_id"])
                desbloqueadas += 1
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🔓 IMPEDIMENTO RESOLVIDO — {story_id} {c['task_id']} "
                        f"desbloqueada: {instalacao_task_id} em DEV DONE "
                        "(a informação que causou o block chegou)."
                    ),
                )
        return desbloqueadas

    # ── DEVOLVER PARA O BURN ──
    def devolver_cards_para_burn(
        self,
        onda_id: str,
        story_id: str,
        agente: str,
        achados_ids: list[str] | None = None,
    ) -> int:
        """Code review achou algo no projeto → os cards DEV DONE do backend/dev
        VOLTAM PARA O BURN (AGUARDANDO DEV) com PRECEDÊNCIA MANDATÓRIA:
        cada card devolvida recebe `dep:{achado_id}` na sua DOR — a card só pode
        re-queimar quando TODOS os achados de pré-requisito estiverem em DEV DONE."""
        voltaram = 0
        deps_achados = [f"dep:{aid}" for aid in (achados_ids or [])]
        for c in self.db.carregar_tasks_kanban(onda_id, story_id):
            # DEV_DONE PODE SER REABERTO SE NECESSÁRIO (somente DONE_DEFINITIVO pós-validate é irreversível).
            # Devolve cards do próprio agente do achado que precisam de retrabalho
            if c["agent_role"] == agente and c["kanban_status"] in ("DEV_DONE", "EM_DEV"):
                if not c["task_id"].startswith("ACHADO-") and not c["task_id"].startswith("REVIEW-"):
                    self.db.mover_task_kanban(onda_id, story_id, c["task_id"], "AGUARDANDO_DEV")
                    for item in deps_achados:
                        self.db.adicionar_dep_task_kanban(onda_id, story_id, c["task_id"], item[4:])
                    voltaram += 1
        return voltaram

    # ── ACORDAR (bola da vez) ──
    def acordar_em_dev(self, onda_id: str, story_id: str, task_id: str) -> bool:
        """PEGA A BOLA DA VEZ E LEVA PRO BURN — mas SÓ com a DOR 100% ATENDIDA
        (sem exceção; sair do blocked e voltar a atuar exige a mesma coisa: a
        informação que causou o blocked é item de DOR). A card escolhida vai
        pra EM_DEV ANTES de atuar (kanban = momento atual) e a SITUAÇÃO
        blocked MORRE: ao ser pega pra executar, a flag é removida — volta ao
        ícone real; se falhar de novo, o binário re-aplica a situação. EM DEV
        pode ter quantas tasks existirem (o que é um por vez é o BURN).
        Retorna False se a DOR não permitir acordar."""
        cartao = next(
            (
                c
                for c in self.db.carregar_tasks_kanban(onda_id, story_id)
                if c["task_id"] == task_id
            ),
            None,
        )
        if cartao is not None:
            dor_ok, item_faltante = self.dor_satisfeita(
                cartao, self.db.carregar_tasks_kanban(onda_id, story_id)
            )
            if not dor_ok:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🚪 DOR — {story_id} {task_id} NÃO vai pra EM DEV: falta "
                        f"{item_faltante}. DOR 100% atendida é condição para pegar "
                        "a card (e para sair do blocked)."
                    ),
                )
                return False
        if cartao is not None and cartao["block_tipo"]:
            # 🚩→🛠 TRATAMENTO NA HORA: a linha parou no impedimento e agora o
            # resolve — a flag morre NA PEGA (se falhar de novo, re-aplica).
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"🛠 TRATANDO IMPEDIMENTO — {story_id} {task_id} ({cartao['block_tipo']}) "
                    "na frente da fila: a linha só segue depois dele."
                ),
            )
        # A pega leva pro burn e o blocked MORRE (impedimento resolvido pela
        # DOR 100%): a card volta ao estado limpo de EM DEV.
        self.db.mover_task_kanban(onda_id, story_id, task_id, "EM_DEV", "")
        return True

    # ── FILA DE ACHADOS (cards no kanban) ──
    def nascer_fila_achados(self, story_id: str, achados: list[str]) -> None:
        """A fila de achados É O KANBAN (única fonte): cada achado nasce COMO
        CARD (ordem 80+i, roteado pela especialidade) ANTES de qualquer atuação.
        Idempotente — card existente nunca é recriada."""
        onda = self.wave_id
        cartoes = self.db.carregar_tasks_kanban(onda, story_id)
        existentes = {c["task_id"] for c in cartoes}
        import re
        maior_idx = 0
        for tid in existentes:
            m = re.match(rf"^ACHADO-{re.escape(story_id)}-(\d+)$", tid)
            if m:
                maior_idx = max(maior_idx, int(m.group(1)))

        for i, achado in enumerate(achados, 1):
            novo_num = maior_idx + i
            tid = f"ACHADO-{story_id}-{novo_num}"
            if tid in existentes:
                continue
            self.db.criar_task_kanban(
                onda,
                story_id,
                tid,
                f"Achado: {achado[:120]}",
                self.roteador_achado(achado),
                -10 + novo_num,
                dor=[],
                dod=["gravou_arquivo"],
                task_tipo="ACHADO",
                descricao=achado[:400],
            )
            self.db.mover_task_kanban(onda, story_id, tid, "AGUARDANDO_DEV")

    def achados_pendentes(self, story_id: str) -> list[dict]:
        """A fila, LIDA DO KANBAN: cards ACHADO pendentes na ordem de execução."""
        return [
            c
            for c in self.db.carregar_tasks_kanban(self.wave_id, story_id)
            if c["task_id"].startswith("ACHADO-")
            and c["kanban_status"] not in ("DEV_DONE", "DONE_DEFINITIVO")
        ]
