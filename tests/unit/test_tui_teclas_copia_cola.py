"""TESTE QUE EU MESMO RODO DA TUI: Ctrl+Shift+C copia, Ctrl+Shift+V cola.
Comportamento exigido = igual opencode original."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pyperclip
import pytest

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.prompt_input import PromptInput  # noqa: F401


@pytest.fixture
def app_tui(tmp_path):
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_teclas", project_dir=str(tmp_path))
    return app


def test_bindings_existem(app_tui):
    acoes = {b.action for b in BombeTuiApp.BINDINGS}
    for acao in ("copiar_tela", "colar_clipboard", "toggle_mouse"):
        assert acao in acoes, f"ação {acao} ausente nos bindings"


def test_ctrl_shift_c_copia_transcricao(app_tui, monkeypatch):
    copiado: dict[str, str] = {}
    monkeypatch.setattr(type(app_tui), "copy_to_clipboard", lambda self, t: copiado.update(osc52=t))
    monkeypatch.setattr(pyperclip, "copy", lambda t: copiado.update(local=t))

    chat = type("FakeView", (), {"children": [
        type("W", (), {"content": "linha da transcrição"})(),
    ]})()
    monkeypatch.setattr(type(app_tui), "query_one", lambda self, _s, _t=None: chat, raising=False)

    app_tui.action_copiar_tela()

    assert "linha da transcrição" in copiado["osc52"]
    assert "linha da transcrição" in copiado["local"]


def test_ctrl_shift_v_cola_no_input(app_tui, monkeypatch):
    monkeypatch.setattr(pyperclip, "paste", lambda: "texto colado do clipboard")

    inp = SimpleNamespace(
        insert=lambda texto, location: chamadas_ins.append(texto),
        location=(0, 0),
        focus=lambda: None,
    )
    chamadas_ins: list[str] = []
    fake_view = type("FakeView", (), {"children": []})()

    def fake_query_one(_self, _sel: str, _t: Any = None):
        if "prompt-input" in _sel:
            return inp
        return fake_view

    monkeypatch.setattr(type(app_tui), "query_one", fake_query_one, raising=False)

    chamadas: list[tuple] = []
    inp.insert = lambda texto, location: chamadas.append((texto, location))  # type: ignore[method-assign]

    app_tui.action_paste_clipboard()

    assert chamadas and "texto colado do clipboard" in chamadas[0][0]


def test_colar_com_clipboard_vazio_nao_quebra(app_tui, monkeypatch):
    monkeypatch.setattr(pyperclip, "paste", lambda: "")

    inp = SimpleNamespace(
        insert=lambda texto, location: None,
        location=(0, 0),
        focus=lambda: None,
    )
    fake_view = type("FakeView", (), {"children": []})()

    def fake_query_one(_self, _sel: str, _t: Any = None):
        if "prompt-input" in _sel:
            return inp
        fv = type("FV", (), {"children": []})()
        fv.mount = lambda widget: None
        return fv

    monkeypatch.setattr(type(app_tui), "query_one", fake_query_one, raising=False)

    inp.insert = lambda texto, location: None  # type: ignore[method-assign]
    app_tui.action_paste_clipboard()  # não levanta


def test_mouse_livre_por_padrao(app_tui):
    """Paridade opencode: mouse LIVRE — seleção nativa do terminal sempre ok."""
    assert app_tui._mouse_ligado is False
