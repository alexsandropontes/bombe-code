"""Widget de Sidebar vertical para a TUI do Bombe Code (paridade com OpenCode)."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from ...turing.fila import KanbanLeitura, quadro_da_onda
from ..tokens import TOKENS


def _get_git_modified_files(repo_dir: str | Path = ".") -> list[dict[str, Any]]:
    """Lê arquivos modificados no repositório com contadores de adição/remoção."""
    try:
        res = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
            timeout=1.5,
        )
        items = []
        if res.stdout:
            for line in res.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 3:
                    add = int(parts[0]) if parts[0].isdigit() else 0
                    dels = int(parts[1]) if parts[1].isdigit() else 0
                    filepath = parts[2]
                    items.append(
                        {
                            "file": filepath,
                            "additions": add,
                            "deletions": dels,
                        }
                    )
        # Arquivos não rastreados (usa -uall para inspecionar arquivos reais e ignorar raízes de diretórios)
        st = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
            timeout=1.5,
        )
        if st.stdout:
            existing = {it["file"].rstrip("/") for it in items}
            for line in st.stdout.strip().splitlines():
                if line.startswith("??"):
                    f = line[3:].strip()
                    if f.endswith("/"):
                        continue
                    if f not in existing:
                        items.append({"file": f, "additions": 1, "deletions": 0})
        return items
    except (subprocess.SubprocessError, OSError):
        return []


def _frase_curta(titulo: str) -> str:
    """Frase curta da story/task para a fila do painel (sem prefixo 'Story N')."""
    import re as _re

    base = (titulo or "").strip()
    for sep in (" — ", " – ", ": "):
        if sep in base:
            base = base.split(sep, 1)[1].strip()
            break
    base = _re.sub(r"^Story\s+\S+\s*", "", base, flags=_re.IGNORECASE)
    return base[:36]


def _simbolo_tarefa(titulo: str) -> tuple[str, str]:
    """Símbolo/cor por TIPO de task (fora de blocked):
    🐛 laranja = bug/débito/correção · ⚙️ verde = task normal."""
    titulo_lower = (titulo or "").lower()
    eh_bug = any(
        k in titulo_lower
        for k in (
            "bug",
            "fix",
            "correção",
            "correcao",
            "débito",
            "debito",
            "defeito",
            "hotfix",
            "achado",
        )
    )
    if eh_bug:
        return "🐛", TOKENS["laranja"]
    return "⚙️", TOKENS["success"]


# ── REGRA VISUAL ÚNICA (DRY) — vale para o board de TASKS e o de STORIES ──
# EM DEV/execução: VERDE NEGRITO (🔨 alterna na queima) · AGUARDANDO/fila:
# cinza claro · DEV DONE: riscado apagado · blocked: mantém a cor do STATUS,
# só o ícone vira 🚩 · BACKLOG e DONE DEFINITIVO: nem aparecem.
_COR_EXECUCAO = TOKENS["success"]
_COR_FILA = TOKENS["text_muted"]
_ESTILO_DONE = f"{TOKENS['text_dim']} strike"
ICONE_BLOCKED = "🚩"
ICONE_FEITA = "✓"


def _entrada_fila(
    rotulo: str,
    simbolo: str,
    cor: str,
    rodando: bool = False,
    negrito: bool = False,
    depth: int = 0,
) -> dict:
    """Monta a entrada-padrão do quadro.
    `negrito` = EM DEV (verde negrito); `rodando` = a queima da vez (🔨);
    `depth` = nível hierárquico na árvore kanban (recuo proporcional)."""
    return {
        "rotulo": rotulo,
        "simbolo": simbolo,
        "cor": cor,
        "rodando": rodando,
        "em_andamento": negrito or rodando,
        "depth": depth,
    }


class Sidebar(VerticalScroll):
    """Painel lateral vertical com informações do projeto, métricas e contexto."""

    DEFAULT_CSS = f"""
    Sidebar {{
        width: 40;
        height: 100%;
        background: {TOKENS["surface"]};
        border-left: solid {TOKENS["border"]};
        padding: 1 1;
        scrollbar-gutter: stable;
    }}

    Sidebar.hidden {{
        display: none;
    }}

    .sidebar-section {{
        margin-bottom: 1;
        padding-bottom: 1;
        border-bottom: solid {TOKENS["surface_alt"]};
    }}

    .sidebar-title {{
        color: {TOKENS["primary"]};
        text-style: bold;
    }}

    .sidebar-muted {{
        color: {TOKENS["text_muted"]};
    }}

    .sidebar-text {{
        color: {TOKENS["text"]};
    }}

    .diff-add {{
        color: {TOKENS["success"]};
    }}

    .diff-del {{
        color: {TOKENS["error"]};
    }}
    """

    session_id = reactive("")
    session_title = reactive("Sessão Principal")
    can_focus = False
    directory = reactive("")
    model_name = reactive("padrão")
    tokens_count = reactive(0)
    context_percent = reactive(0)
    cost = reactive(0.0)
    arquivos_escritos: list[str] | None = None

    def __init__(
        self,
        project_dir: str = ".",
        session_id: str = "",
        session_title: str = "Sessão Principal",
        model: str = "padrão",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.project_dir = os.path.abspath(project_dir)
        self.session_id = session_id
        self.session_title = session_title
        self.directory = self.project_dir
        self.arquivos_escritos: list[str] = []
        self.model_name = model
        self._content_widget = Static("", id="sidebar-content")
        self.tarefas: list[dict] = []
        self.wave_id: str = ""
        self._modelo_kanban: KanbanLeitura | None = None

    def compose(self) -> ComposeResult:
        yield self._content_widget

    def on_mount(self) -> None:
        self.set_interval(2.0, self._poll_tarefas)
        # A alternância 🔨 é temporal (símbolo ↔ martelo a cada segundo): o
        # re-render precisa acontecer MESMO sem mudança de dados, senão o
        # ícone congela. Só re-renderiza se houver tarefa em andamento.
        self.set_interval(1.0, self._tick_alternancia)
        self.refresh_view()

    def _tick_alternancia(self) -> None:
        if any(tr.get("em_andamento") for tr in self.tarefas):
            self.refresh_view()

    def update_metrics(
        self,
        tokens: int | None = None,
        cost: float | None = None,
        percent: int | None = None,
        title: str | None = None,
        directory: str | None = None,
    ) -> None:
        """Atualiza valores dinâmicos de consumo de contexto e tokens."""
        if tokens is not None:
            self.tokens_count = tokens
        if cost is not None:
            self.cost = cost
        if percent is not None:
            self.context_percent = percent
        if title is not None:
            self.session_title = title
        if directory is not None:
            self.directory = os.path.abspath(directory)
        self.refresh_view()

    def registrar_arquivo(self, caminho: str) -> None:
        """Registra arquivo gravado pela sessão (projetos sem git mostram igual)."""
        if caminho and caminho not in self.arquivos_escritos:
            self.arquivos_escritos.append(caminho)
            self.refresh_view()

    def _poll_tarefas(self) -> None:
        """REGRA DA TELA: o poll NUNCA derruba o app — qualquer falha de
        leitura (lock do processo, db ausente) apenas mantém o quadro como
        está. A tela lê em mode=ro e NUNCA escreve no banco do processo."""
        try:
            self._poll_tarefas_interno()
        except Exception:  # noqa: BLE001, S110 — estabilidade do input > quadro fresco
            pass

    def _poll_tarefas_interno(self) -> None:
        """Fila viva do kanban: Onda + Story + frase curta; atuais em cima,
        próximas embaixo; TETO de 7 somando tudo. Quando a atual sai, entra a
        próxima da fila.

        Status (símbolo/cor):
        🚩 vermelho = bloqueada (linha parada) · 🟠 laranja = em revisão/
        correção (bugs e débitos) · ▶ verde = nova em execução · · cinza =
        aguardando fila · ✓ cinza escuro RISCADA = encerrada (fica visível
        60s; se estiver ocupando vaga de fila, expira e a próxima entra).
        """
        import sqlite3

        db = Path(self.project_dir) / ".bombe-code" / "state.db"
        if not db.exists():
            if self.tarefas:
                self.tarefas = []
                self.refresh_view()
            return
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1.0)
            try:
                wave_row = con.execute("SELECT wave_id FROM wave_state LIMIT 1").fetchone()
            finally:
                con.close()
        except sqlite3.Error:
            return
        self.wave_id = (wave_row[0] if wave_row else "") or ""
        if not self.wave_id:
            return
        if self._modelo_kanban is None:
            self._modelo_kanban = KanbanLeitura(
                str(Path(self.project_dir) / ".bombe-code" / "state.db")
            )
        quadro = quadro_da_onda(self._modelo_kanban, self.wave_id)
        nova: list[dict] = []
        for row in quadro:
            sid = row["story_id"]
            tid = row["task_id"]
            rotulo = f"{sid} {tid} {_frase_curta(row['title'])}".strip()
            profundidade = int(row.get("depth", 0))

            if row["kanban_status"] == "DEV_DONE":
                nova.append(_entrada_fila(rotulo, ICONE_FEITA, _ESTILO_DONE, depth=profundidade))
                continue
            if row["block_tipo"]:
                nova.append(_entrada_fila(rotulo, "🚩", _COR_FILA, False, False, depth=profundidade))
            elif row["kanban_status"] == "EM_DEV":
                _simbolo, _ = _simbolo_tarefa(row["title"])
                esta_queimando = bool(row.get("em_queima", row.get("proxima")))
                nova.append(
                    _entrada_fila(
                        rotulo,
                        _simbolo,
                        _COR_EXECUCAO,
                        rodando=esta_queimando,
                        negrito=True,
                        depth=profundidade,
                    )
                )
            else:
                simbolo_tipo, _ = _simbolo_tarefa(row["title"])
                nova.append(_entrada_fila(rotulo, simbolo_tipo, _COR_FILA, False, False, depth=profundidade))

        nova = nova[:7]
        if nova != self.tarefas:
            self.tarefas = nova
            self.refresh_view()

    def refresh_view(self) -> None:
        """Renderiza a visualização rica do painel lateral."""
        t = Text()

        # 1. Workspace / Projeto
        t.append("📂 WORKSPACE\n", style=f"bold {TOKENS['primary']}")
        dir_name = os.path.basename(self.directory) or self.directory
        t.append(f" {dir_name}\n", style=f"bold {TOKENS['text']}")
        t.append(f" {self.directory}\n", style=f"{TOKENS['text_muted']}")
        t.append(
            f" Sessão: {self.session_id[:16] if self.session_id else 'iniciando'}\n",
            style=f"{TOKENS['text_muted']}",
        )
        t.append("─" * 36 + "\n", style=TOKENS["surface_alt"])

        # 1.5 Tarefas vivas do kanban de agentes (teto 7)
        if self.tarefas:
            titulo_onda = f" · {self.wave_id}" if self.wave_id else ""
            t.append(
                f"📋 TAREFAS{titulo_onda} ({len(self.tarefas)})\n",
                style=f"bold {TOKENS['secondary']}",
            )
            from rich.cells import cell_len
            for tr in self.tarefas:
                # Regras de cor/status: EM DEV = VERDE NEGRITO; AGUARDANDO =
                # cinza claro; DEV DONE = riscado; blocked mantém a cor do
                # status e só troca o ícone pela bandeira. EM EXECUÇÃO (o que
                # o agente está fazendo agora) alterna o ícone com 🔨.
                if tr.get("rodando"):
                    alternando = int(time.time()) % 2 == 0
                    marcador = tr["simbolo"] if alternando else "🔨"
                    estilo = f"bold {tr['cor']}"
                elif tr.get("em_andamento"):
                    marcador = tr["simbolo"]
                    estilo = f"bold {tr['cor']}"
                else:
                    marcador = tr["simbolo"]
                    estilo = tr["cor"]
                # Recuo hierárquico proporcional ao nível da subtask na árvore kanban
                nivel = tr.get("depth", 0)
                recuo = "  " * nivel
                # Emojis/símbolos de largura 1 (ex: ⚙️ ou ✓) recebem 2 espaços após o ícone,
                # enquanto emojis largos de 2 células (ex: 🔨, 🐛, 🚩) recebem 1 espaço.
                # Isso garante coluna alinhada e nunca gruda texto no ícone.
                espaco_icone = "  " if cell_len(marcador) == 1 else " "
                t.append(f" {recuo}{marcador}{espaco_icone}{tr['rotulo']}\n", style=estilo)
            t.append("─" * 36 + "\n", style=TOKENS["surface_alt"])

        # 2. Context & Token Usage
        t.append("🧠 CONTEXTO & TOKENS\n", style=f"bold {TOKENS['secondary']}")
        t.append(f" Modelo: {self.model_name}\n", style=f"{TOKENS['text']}")
        t.append(f" Tokens: {self.tokens_count:,} tokens\n", style=f"{TOKENS['text']}")
        t.append(f" Janela: {self.context_percent}% usada\n", style=f"{TOKENS['text']}")
        # Custo em USD permanece medido (self.cost) porém OCULTO da tela —
        # decisão de produto: não exibir custo por enquanto.
        t.append("─" * 36 + "\n", style=TOKENS["surface_alt"])

        # 3. Modified Files — git (se existir) + arquivos escritos pela sessão
        # ÚLTIMOS 10: escritos da sessão primeiro (trabalho vivo), git preenche
        LIMITE_ARQUIVOS = 10
        files = _get_git_modified_files(self.directory)
        escritos_sessao = [f for f in self.arquivos_escritos if f not in {i["file"] for i in files}]
        escritos_visiveis = escritos_sessao[-LIMITE_ARQUIVOS:]
        vagas_git = max(0, LIMITE_ARQUIVOS - len(escritos_visiveis))
        files_visiveis = files[:vagas_git]
        total_arquivos = len(files) + len(escritos_sessao)
        t.append(f"📝 ARQUIVOS MODIFICADOS ({total_arquivos})\n", style=f"bold {TOKENS['primary']}")
        if not files and not escritos_sessao:
            t.append(" (Nenhum arquivo modificado)\n", style=f"{TOKENS['text_muted']}")
        for item in files_visiveis:
            raw_file = item["file"].rstrip("/")
            p = Path(raw_file)
            if len(p.parts) > 1:
                display_name = f"{p.parts[-2]}/{p.name}"
            else:
                display_name = p.name
            t.append(f" • {display_name[:24]:<24} ", style=f"{TOKENS['text']}")
            if item["additions"]:
                t.append(f"+{item['additions']} ", style=f"{TOKENS['success']}")
            if item["deletions"]:
                t.append(f"-{item['deletions']}", style=f"{TOKENS['error']}")
            t.append("\n")
        for caminho in escritos_visiveis:
            pp = Path(caminho)
            display_name = f"{pp.parts[-2]}/{pp.name}" if len(pp.parts) > 1 else pp.name
            t.append(f" ✍️ {display_name[:30]:<30}\n", style=f"{TOKENS['warning']}")
        if total_arquivos > LIMITE_ARQUIVOS:
            t.append(
                f" ... e mais {total_arquivos - LIMITE_ARQUIVOS} arquivos\n",
                style=f"{TOKENS['text_muted']}",
            )
        t.append("─" * 36 + "\n", style=TOKENS["surface_alt"])

        # 4. Integrações
        t.append("🔌 INTEGRAÇÕES\n", style=f"bold {TOKENS['secondary']}")
        t.append(" • LSP Engine: ", style=f"{TOKENS['text']}")
        t.append("Ativo (AST)\n", style=f"{TOKENS['success']}")
        t.append(" • MCP Protocol: ", style=f"{TOKENS['text']}")
        t.append("Pronto (JSON-RPC)\n", style=f"{TOKENS['success']}")
        t.append(" • Snapshots: ", style=f"{TOKENS['text']}")
        t.append("Git Rollback\n", style=f"{TOKENS['success']}")

        self._last_rendered_text = t
        if self.is_mounted:
            self._content_widget.update(t)
