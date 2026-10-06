"""Módulo Web UI do Bombe Code."""

from .app import app, index
from .state import WebState

__all__ = ["WebState", "app", "index"]
