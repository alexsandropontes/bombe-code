"""Camada de Aplicação (Application Services & Use Cases) do Bombe Code.

Orquestra os fluxos de trabalho da ONDA, Despacho de Intenções e Sessões,
sendo consumida diretamente por todas as interfaces de apresentação (TUI, HTTP Server, CLI).
"""

from .intent.service import IntentApplicationService
from .wave.service import WaveApplicationService

__all__ = ["IntentApplicationService", "WaveApplicationService"]
