"""Integration tests for F16 desktop shell with pywebview."""

import os

import pytest

from bombe_code.desktop.app import DesktopApp

pytestmark = pytest.mark.integration


def test_desktop_app_window_spec():
    app = DesktopApp(
        url="http://127.0.0.1:4096", title="Bombe Code Desktop", width=1280, height=800
    )
    spec = app.get_window_spec()

    assert spec["url"] == "http://127.0.0.1:4096"
    assert spec["title"] == "Bombe Code Desktop"
    assert spec["width"] == 1280
    assert spec["height"] == 800


def test_desktop_app_headless_detection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    app = DesktopApp(url="http://127.0.0.1:4096")
    # In Linux without DISPLAY or WAYLAND_DISPLAY, is_display_available is False
    if os.name == "posix" and not sys_is_darwin():
        assert app.is_display_available() is False
        assert app.run_headless_safe() == "headless_mode_detected"


def sys_is_darwin():
    import sys

    return sys.platform == "darwin"
