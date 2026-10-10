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


# Status → (símbolo, estilo rich). Vermelho = bloqueada; laranja = revisão/
# correção (bugs e débitos); verde = nova em execução; cinza = fila;
# cinza escuro riscada = encerrada (visível por 60s).
_MARCADORES = {
    "blocked": ("🚩", f"bold {TOKENS['error']}"),
    "review": ("🟠", f"bold {TOKENS['laranja']}"),
    "run": ("▶", f"bold {TOKENS['success']}"),
    "fila": ("·", TOKENS["text_muted"]),
    "done": ("✓", f"{TOKENS['text_dim']} strike"),
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

    def compose(self) -> ComposeResult:
        yield self._content_widget

    def on_mount(self) -> None:
        self.set_interval(2.0, self._poll_tarefas)
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
                # FONTE PRIMÁRIA: kanban de AGENTES (task a task — o que manda).
                cards_task = con.execute(
                    "SELECT story_id, task_id, title, kanban_status, block_tipo "
                    "FROM agent_tasks WHERE task_id != '' ORDER BY ordem"
                ).fetchall()
                # Fallback: projetos sem kanban de agentes → stories.
                cards = con.execute(
                    "SELECT story_id, title, status, is_blocked, updated_at "
                    "FROM kanban_cards ORDER BY rowid"
                ).fetchall()
            finally:
                con.close()
        except sqlite3.Error:
            return
        self.wave_id = (wave_row[0] if wave_row else "") or ""
        agora = time.time()
        nova: list[dict] = []
        if cards_task:
            # ── Tarefas de agentes: BLOCKED (Andon) → EM DEV → fila → done ──
            bloqueadas: list[dict] = []
            em_dev: list[dict] = []
            fila_t: list[dict] = []
            feitas: list[dict] = []
            for sid, tid, titulo, kanban_status, block_tipo in cards_task:
                frase = _frase_curta(titulo)
                rotulo = f"{sid} {tid} {frase}".strip()
                if kanban_status == "BLOCKED":
                    bloqueadas.append(
                        {
                            "rotulo": rotulo,
                            "simbolo": "🚩",
                            "cor": TOKENS["error"],
                            "em_andamento": False,
                        }
                    )
                elif kanban_status == "EM_DEV":
                    # Blocked sendo re-trabalhado mantém a bandeira; nova em
                    # execução usa ▶. EM ANDAMENTO = negrito + alterna 🔨.
                    if block_tipo:
                        em_dev.append(
                            {
                                "rotulo": rotulo,
                                "simbolo": "🚩",
                                "cor": TOKENS["error"],
                                "em_andamento": True,
                            }
                        )
                    else:
                        em_dev.append(
                            {
                                "rotulo": rotulo,
                                "simbolo": "▶",
                                "cor": TOKENS["success"],
                                "em_andamento": True,
                            }
                        )
                elif kanban_status == "DEV_DONE":
                    feitas.insert(
                        0,
                        {
                            "rotulo": rotulo,
                            "simbolo": "✓",
                            "cor": TOKENS["text_muted"],
                            "em_andamento": False,
                        },
                    )
                elif kanban_status == "DONE_DEFINITIVO":
                    feitas.append(
                        {
                            "rotulo": rotulo,
                            "simbolo": "✓",
                            "cor": TOKENS["text_dim"],
                            "em_andamento": False,
                        }
                    )
                else:  # AGUARDANDO_DEV / BACKLOG — fila, sem negrito
                    fila_t.append(
                        {
                            "rotulo": rotulo,
                            "simbolo": "·",
                            "cor": TOKENS["text_muted"],
                            "em_andamento": False,
                        }
                    )
                if len(nova) >= 7:
                    break
            nova = (bloqueadas + em_dev + fila_t + feitas)[:7]
            for item in nova:
                item["estado"] = "task"
        else:
            atuais: list[tuple[str, str, str]] = []
            encerradas: list[tuple[str, str, str]] = []
            fila: list[tuple[str, str, str]] = []
            for sid, titulo, status, is_blocked, updated_at in cards:
                frase = _frase_curta(titulo)
                if is_blocked:
                    atuais.append((sid, frase, "blocked"))
                elif status == "IN_PROGRESS":
                    atuais.append((sid, frase, "run"))
                elif status in ("IN_REVIEW", "VALIDATE"):
                    atuais.append((sid, frase, "review"))
                elif status in ("DONE", "DEV_DONE"):
                    # Encerrada aparece riscada por 60s; depois dá lugar à fila.
                    if agora - float(updated_at or 0) <= 60:
                        encerradas.append((sid, frase, "done"))
                elif status in ("READY", "TODO", "PENDING", "BACKLOG"):
                    fila.append((sid, frase, "fila"))
            for s, f, e in (atuais + encerradas + fila)[:7]:
                marcador, estilo = _MARCADORES[e]
                nova.append(
                    {
                        "estado": e,
                        "rotulo": f"{s} {f}".strip(),
                        "simbolo": marcador,
                        "cor": estilo,
                        "em_andamento": e in ("run", "review"),
                    }
                )
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
            for tr in self.tarefas:
                # Regra: EM ANDAMENTO = NEGRITO + símbolo alternando entre o
                # original da task e 🔨 (em construção). Fila = sem negrito.
                if tr.get("em_andamento"):
                    alternando = int(time.time()) % 2 == 0
                    marcador = tr["simbolo"] if alternando else "🔨"
                    estilo = f"bold {tr['cor']}"
                else:
                    marcador = tr["simbolo"]
                    estilo = tr["cor"]
                t.append(f" {marcador} {tr['rotulo']}\n", style=estilo)
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
