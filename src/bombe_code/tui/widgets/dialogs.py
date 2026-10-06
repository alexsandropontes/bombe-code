"""Diálogos modais para permissões e perguntas da TUI."""

from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from ..tokens import TOKENS


class PermissionDialog(ModalScreen[str]):
    """Diálogo modal para solicitação de permissão (once / always / reject)."""

    DEFAULT_CSS = f"""
    PermissionDialog {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #dialog-container {{
        width: 60;
        height: auto;
        border: thick {TOKENS["warning"]};
        background: {TOKENS["surface"]};
        padding: 1 2;
    }}

    #dialog-title {{
        text-style: bold;
        color: {TOKENS["warning"]};
        margin-bottom: 1;
    }}

    #dialog-details {{
        color: {TOKENS["text"]};
        margin-bottom: 1;
    }}

    #dialog-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
    }}

    #dialog-buttons Button {{
        margin: 0 1;
    }}
    """

    def __init__(self, permission: str, details: str) -> None:
        super().__init__()
        self.permission = permission
        self.details = details

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-container"):
            yield Label(f"⚠️ Solicitação de Permissão: {self.permission}", id="dialog-title")
            yield Static(f"Detalhes: {self.details}", id="dialog-details")
            with Horizontal(id="dialog-buttons"):
                yield Button("Permitir Uma Vez", variant="success", id="btn-once")
                yield Button("Sempre Permitir", variant="primary", id="btn-always")
                yield Button("Rejeitar", variant="error", id="btn-reject")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-once":
            self.dismiss("once")
        elif event.button.id == "btn-always":
            self.dismiss("always")
        elif event.button.id == "btn-reject":
            self.dismiss("reject")


class QuestionDialog(ModalScreen[str]):
    """Diálogo modal para responder a uma pergunta do agente."""

    DEFAULT_CSS = f"""
    QuestionDialog {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #question-container {{
        width: 60;
        height: auto;
        border: thick {TOKENS["primary"]};
        background: {TOKENS["surface"]};
        padding: 1 2;
    }}

    #question-label {{
        text-style: bold;
        color: {TOKENS["primary"]};
        margin-bottom: 1;
    }}

    #question-input {{
        margin-bottom: 1;
    }}
    """

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="question-container"):
            yield Label(f"❓ Pergunta do Agente:\n{self.question}", id="question-label")
            yield Input(placeholder="Digite sua resposta...", id="question-input")
            with Horizontal(id="dialog-buttons"):
                yield Button("Enviar Resposta", variant="primary", id="btn-submit")
                yield Button("Cancelar", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            inp = self.query_one("#question-input", Input)
            self.dismiss(inp.value)
        elif event.button.id == "btn-cancel":
            self.dismiss("")


class ConnectDialog(ModalScreen[tuple[str, str] | None]):
    """Diálogo modal para conectar um provedor de IA via /connect (paridade OpenCode)."""

    DEFAULT_CSS = f"""
    ConnectDialog {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #connect-container {{
        width: 65;
        height: auto;
        border: thick {TOKENS["primary"]};
        background: {TOKENS["surface"]};
        padding: 1 2;
    }}

    #connect-title {{
        text-style: bold;
        color: {TOKENS["primary"]};
        margin-bottom: 1;
    }}

    #connect-hint {{
        color: {TOKENS["text_muted"]};
        margin-bottom: 1;
    }}

    #connect-provider-input, #connect-value-input {{
        margin-bottom: 1;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="connect-container"):
            yield Label("🔌 Conectar Provedor de IA (/connect)", id="connect-title")
            yield Static(
                "Provedores: openai, anthropic, openrouter, groq, llama.cpp, ollama",
                id="connect-hint",
            )
            yield Input(
                placeholder="Provedor (ex: openai, anthropic, llama.cpp)",
                id="connect-provider-input",
            )
            yield Input(
                placeholder="Chave de API ou URL local (ex: sk-... ou http://127.0.0.1:8080/v1)",
                id="connect-value-input",
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("Salvar e Conectar", variant="primary", id="btn-save")
                yield Button("Cancelar", variant="default", id="btn-cancel")

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel_dialog", "Fechar", show=False, priority=True),
    ]

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)

    def on_mount(self) -> None:
        self.query_one("#connect-provider-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "connect-provider-input":
            self.query_one("#connect-value-input", Input).focus()
        elif event.input.id == "connect-value-input":
            self._submit()

    def _submit(self) -> None:
        prov = self.query_one("#connect-provider-input", Input).value.strip().lower()
        val = self.query_one("#connect-value-input", Input).value.strip()
        if prov and val:
            self.dismiss((prov, val))
        else:
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._submit()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class ModelDialog(ModalScreen[str | None]):
    """Diálogo modal para selecionar modelo de IA (/models) com paridade ao OpenCode DialogModel."""

    DEFAULT_CSS = f"""
    ModelDialog {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #model-container {{
        width: 78;
        height: 25;
        border: thick {TOKENS["primary"]};
        background: {TOKENS["surface"]};
        padding: 1 2;
    }}

    #model-title {{
        text-style: bold;
        color: {TOKENS["primary"]};
        margin-bottom: 1;
    }}

    #model-search {{
        margin-bottom: 1;
    }}

    #model-option-list {{
        height: 14;
        border: solid {TOKENS["surface_alt"]};
        background: {TOKENS["surface_alt"]};
        margin-bottom: 1;
    }}

    #dialog-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
    }}

    #dialog-buttons Button {{
        margin: 0 1;
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel_dialog", "Fechar", show=False, priority=True),
    ]

    def __init__(
        self,
        models: list[tuple[str, str, str]] | None = None,
        current_model: str | None = None,
    ) -> None:
        super().__init__()
        self.all_models = models or []
        self.current_model = current_model

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="model-container"):
            yield Label("🧠 Selecionar Modelo (/models)", id="model-title")
            yield Input(
                placeholder="Buscar modelo (ex: mimo, qwen, llama, gpt-4o)...", id="model-search"
            )
            yield OptionList(id="model-option-list")
            with Horizontal(id="dialog-buttons"):
                yield Button("Selecionar", variant="primary", id="btn-select")
                yield Button("Cancelar", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self._populate_options(self.all_models)
        self.query_one("#model-search", Input).focus()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("down", "j"):
            opt_list = self.query_one("#model-option-list", OptionList)
            opt_list.action_cursor_down()
            event.prevent_default()
        elif event.key in ("up", "k"):
            opt_list = self.query_one("#model-option-list", OptionList)
            opt_list.action_cursor_up()
            event.prevent_default()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "model-search":
            opt_list = self.query_one("#model-option-list", OptionList)
            if opt_list.highlighted is not None:
                opt = opt_list.get_option_at_index(opt_list.highlighted)
                if opt.id and not opt.id.startswith("__"):
                    self.dismiss(opt.id)
                    return
            for idx in range(opt_list.option_count):
                opt = opt_list.get_option_at_index(idx)
                if opt.id and not opt.id.startswith("__"):
                    self.dismiss(opt.id)
                    return

    def _populate_options(self, models_to_show: list[tuple[str, str, str]]) -> None:
        opt_list = self.query_one("#model-option-list", OptionList)
        opt_list.clear_options()
        if not models_to_show:
            opt_list.add_option(Option("Nenhum modelo encontrado", id="__none__", disabled=True))
            return

        current_category = None
        target_highlight_index: int | None = None
        first_valid_index: int | None = None
        current_option_idx = 0

        for model_id, label, category in models_to_show:
            if category != current_category:
                current_category = category
                opt_list.add_option(
                    Option(f"── {category} ──", id=f"__cat_{category}__", disabled=True)
                )
                current_option_idx += 1

            is_active = self.current_model and (
                self.current_model == model_id or self.current_model in model_id
            )
            display_label = f"  • {label} (ativo)" if is_active else f"  • {label}"
            opt_list.add_option(Option(display_label, id=model_id))

            if first_valid_index is None:
                first_valid_index = current_option_idx
            if is_active and target_highlight_index is None:
                target_highlight_index = current_option_idx
            current_option_idx += 1

        highlight_to_set = (
            target_highlight_index if target_highlight_index is not None else first_valid_index
        )
        if highlight_to_set is not None:
            opt_list.highlighted = highlight_to_set

    def on_input_changed(self, event: Input.Changed) -> None:
        needle = event.value.strip().lower()
        if not needle:
            self._populate_options(self.all_models)
        else:
            filtered = [
                m
                for m in self.all_models
                if needle in m[0].lower() or needle in m[1].lower() or needle in m[2].lower()
            ]
            self._populate_options(filtered)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id and not event.option.id.startswith("__"):
            self.dismiss(event.option.id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            opt_list = self.query_one("#model-option-list", OptionList)
            if opt_list.highlighted is not None:
                opt = opt_list.get_option_at_index(opt_list.highlighted)
                if opt.id and not opt.id.startswith("__"):
                    self.dismiss(opt.id)
                    return
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
