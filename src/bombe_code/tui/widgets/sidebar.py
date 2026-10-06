"""Widget de Sidebar vertical para a TUI do Bombe Code (paridade com OpenCode)."""

from __future__ import annotations

import os
import subprocess
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
        self.model_name = model
        self._content_widget = Static("", id="sidebar-content")

    def compose(self) -> ComposeResult:
        yield self._content_widget

    def on_mount(self) -> None:
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

        # 2. Context & Token Usage
        t.append("🧠 CONTEXTO & TOKENS\n", style=f"bold {TOKENS['secondary']}")
        t.append(f" Modelo: {self.model_name}\n", style=f"{TOKENS['text']}")
        t.append(f" Tokens: {self.tokens_count:,} tokens\n", style=f"{TOKENS['text']}")
        t.append(f" Janela: {self.context_percent}% usada\n", style=f"{TOKENS['text']}")
        # Custo em USD permanece medido (self.cost) porém OCULTO da tela —
        # decisão de produto: não exibir custo por enquanto.
        t.append("─" * 36 + "\n", style=TOKENS["surface_alt"])

        # 3. Modified Files
        files = _get_git_modified_files(self.directory)
        t.append(f"📝 ARQUIVOS MODIFICADOS ({len(files)})\n", style=f"bold {TOKENS['primary']}")
        if not files:
            t.append(" (Nenhum arquivo modificado)\n", style=f"{TOKENS['text_muted']}")
        else:
            for item in files[:8]:
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
            if len(files) > 8:
                t.append(
                    f" ... e mais {len(files) - 8} arquivos\n", style=f"{TOKENS['text_muted']}"
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
