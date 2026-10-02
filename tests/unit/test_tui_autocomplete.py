"""Testes unitários para autocompletar (PromptSuggester e PromptInput com Tab)."""

from __future__ import annotations

import pytest

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.prompt_input import PromptInput, PromptSuggester


@pytest.mark.anyio
async def test_prompt_suggester_slash_commands():
    suggester = PromptSuggester(project_dir=".")

    # Sugestão de comando geral
    res = await suggester.get_suggestion("/mo")
    assert res == "/models"

    res_agent = await suggester.get_suggestion("/agent p")
    assert res_agent == "/agent plan"

    res_theme = await suggester.get_suggestion("/themes d")
    assert res_theme == "/themes dracula"


@pytest.mark.anyio
async def test_prompt_suggester_file_mentions():
    suggester = PromptSuggester(project_dir=".")

    # Menção de arquivo @
    res = await suggester.get_suggestion("@py")
    assert res is not None
    assert res.startswith("@pyproject.toml") or "@py" in res


@pytest.mark.anyio
async def test_prompt_input_tab_autocomplete_and_cycle():
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)

        # Autocompletar /mo com Tab
        inp.value = "/mo"
        await pilot.pause(0.05)
        await pilot.press("tab")
        await pilot.pause(0.05)
        assert inp.value == "/models"

        # Autocompletar /co e ciclar com Tab
        inp.value = "/co"
        await pilot.pause(0.05)
        await pilot.press("tab")
        await pilot.pause(0.05)
        first_val = inp.value
        assert first_val.startswith("/co")

        await pilot.press("tab")
        await pilot.pause(0.05)
        second_val = inp.value
        assert second_val.startswith("/co")
        assert second_val != first_val
