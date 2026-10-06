"""Módulo de detecção e execução automática de formatadores de código."""

from .runner import detect_formatter_for_file, format_code_file

__all__ = ["detect_formatter_for_file", "format_code_file"]
