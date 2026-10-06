"""Camada de Infraestrutura (Secondary / Outbound Adapters) do Bombe Code."""

from .storage import SqliteWaveRepository

__all__ = ["SqliteWaveRepository"]
