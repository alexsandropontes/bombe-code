"""Diálogo de Ajuda e Atalhos para a TUI (Catálogo Completo dos 28 Comandos)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ..tokens import TOKENS


class HelpDialog(ModalScreen[None]):
    """Modal de ajuda exibindo os atalhos de teclado e os 28 comandos de barra."""

    DEFAULT_CSS = f"""
    HelpDialog {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #help-container {{
        width: 80;
        height: 85%;
        border: thick {TOKENS["primary"]};
        background: {TOKENS["surface"]};
        padding: 1 2;
    }}

    #help-title {{
        text-style: bold;
        color: {TOKENS["primary"]};
        margin-bottom: 1;
    }}

    #help-scroll {{
        height: 1fr;
        scrollbar-gutter: stable;
    }}

    #help-content {{
        color: {TOKENS["text"]};
        margin-bottom: 1;
    }}

    #btn-close {{
        width: 100%;
        margin-top: 1;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("ℹ️ Ajuda — Atalhos e 28 Comandos de Barra (/)", id="help-title")
            help_text = (
                "[bold cyan]ATALHOS DE TECLADO:[/bold cyan]\n"
                "• [bold]Enter[/bold]: Enviar prompt\n"
                "• [bold]↑ / ↓[/bold]: Navegar no histórico de mensagens\n"
                "• [bold]Ctrl+B[/bold]: Alternar Sidebar vertical\n"
                "• [bold]Ctrl+C / Esc[/bold]: Interromper turno ativo\n"
                "• [bold]Ctrl+P[/bold]: Abrir Paleta de Comandos\n"
                "• [bold]F1[/bold]: Exibir este diálogo de ajuda\n"
                "• [bold]Ctrl+Q[/bold]: Sair da aplicação\n\n"
                "[bold cyan]TODOS OS 28 COMANDOS DE BARRA (/):[/bold cyan]\n"
                " 1. [bold]/connect[/bold]: Conectar provedores (OpenAI, Anthropic, llama.cpp, Ollama)\n"
                " 2. [bold]/models [nome][/bold]: Listar ou selecionar modelo ativo (alias: /model)\n"
                " 3. [bold]/sessions [id][/bold]: Listar ou alternar sessões (aliases: /resume, /continue)\n"
                " 4. [bold]/new[/bold]: Iniciar uma nova sessão limpa (alias: /clear)\n"
                " 5. [bold]/compact[/bold]: Compactar histórico da sessão (alias: /summarize)\n"
                " 6. [bold]/undo[/bold]: Desfazer último turno e alterações de arquivos\n"
                " 7. [bold]/redo[/bold]: Restaurar turno desfeito\n"
                " 8. [bold]/fork[/bold]: Bifurcar sessão em nova ramificação\n"
                " 9. [bold]/share[/bold]: Compartilhar sessão ativa\n"
                "10. [bold]/unshare[/bold]: Revogar compartilhamento de sessão\n"
                "11. [bold]/export [arquivo][/bold]: Exportar transcrição para Markdown\n"
                "12. [bold]/copy[/bold]: Copiar última resposta para a área de transferência\n"
                "13. [bold]/rename <título>[/bold]: Renomear título da sessão ativa\n"
                "14. [bold]/timeline[/bold]: Exibir linha do tempo cronológica da sessão\n"
                "15. [bold]/help[/bold]: Exibir este catálogo completo de ajuda\n"
                "16. [bold]/init[/bold]: Inicializar AGENTS.md e configuração no projeto\n"
                "17. [bold]/review[/bold]: Revisar diffs e alterações de código no repositório\n"
                "18. [bold]/themes [nome][/bold]: Listar ou alternar tema visual (alias: /theme)\n"
                "19. [bold]/thinking[/bold]: Alternar visualização de raciocínio (alias: /toggle-thinking)\n"
                "20. [bold]/timestamps[/bold]: Alternar carimbos de data/hora (alias: /toggle-timestamps)\n"
                "21. [bold]/details[/bold]: Alternar detalhes de execução de ferramentas\n"
                "22. [bold]/editor[/bold]: Abrir editor externo ($EDITOR) para compor prompt\n"
                "23. [bold]/sidebar[/bold]: Alternar visibilidade da Sidebar vertical (Ctrl+B)\n"
                "24. [bold]/agent [nome][/bold]: Selecionar agente especializado ativo\n"
                "25. [bold]/mcp[/bold]: Exibir servidores e ferramentas MCP ativas\n"
                "26. [bold]/lsp[/bold]: Exibir status de diagnósticos de sintaxe AST/LSP\n"
                "27. [bold]/workspace [dir][/bold]: Inspecionar ou trocar pasta do projeto (alias: /dir)\n"
                "28. [bold]/exit[/bold]: Sair da aplicação com segurança (aliases: /quit, /q)\n"
            )
            with VerticalScroll(id="help-scroll"):
                yield Static(help_text, id="help-content")
            yield Button("Fechar", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)
