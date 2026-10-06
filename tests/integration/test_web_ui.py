"""Integration tests for F11 web-ui Reflex components and state."""

import pytest

from bombe_code.web.app import index
from bombe_code.web.state import WebState

pytestmark = pytest.mark.integration


def test_web_ui_component_tree():
    # Verify index page compiles to Reflex component tree
    component = index()
    assert component is not None
    # Component tree contains children
    assert hasattr(component, "children") or hasattr(component, "tag")


@pytest.mark.anyio
async def test_web_ui_state_defaults():
    state = WebState()
    assert state.session_id == ""
    assert state.prompt_text == ""
    assert state.is_streaming is False
    assert state.messages == []
