"""TuringProgressBus — Barramento de Progresso in-process da ONDA.

Publica eventos de execução (anúncios de etapa, deltas de texto/pensamento,
tool calls, vetos e retrabalho) de worker threads para consumidores asyncio
(TUI, CLI) sem acoplamento direto entre orquestrador e interface.

Modo verboso (padrão): tudo é publicado — cada letra streamada.
Modo quiet: apenas eventos canônicos de anúncio (wave/stage/veto) são publicados.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

ANNOUNCEMENT_EVENTS = frozenset(
    {
        "announcement",
        "agent_usage",
        "agent_start",
        "wave_start",
        "stage_start",
        "stage_end",
        "stage_failed",
        "veto_analysis",
        "veto_rework",
        "escalation",
    }
)


@dataclass(frozen=True)
class ProgressEvent:
    """Evento imutável publicado no barramento de progresso da ONDA."""

    type: str
    agent: str | None = None
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class TuringProgressBus:
    """Hub in-process: publishers em threads, subscribers em asyncio loops."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: list[
            tuple[asyncio.AbstractEventLoop, asyncio.Queue[ProgressEvent | None]]
        ] = []
        self.verbosity: str = "verbose"
        self.dropped: int = 0

    # ------------------------------------------------------------------ pub
    def set_verbosity(self, mode: str) -> None:
        with self._lock:
            self.verbosity = (
                "quiet"
                if str(mode).strip().lower() in ("quiet", "silencioso", "silence")
                else "verbose"
            )

    @property
    def verbosity_mode(self) -> str:
        with self._lock:
            return self.verbosity

    @property
    def is_quiet(self) -> bool:
        return self.verbosity_mode == "quiet"

    def _should_publish(self, event_type: str) -> bool:
        if not self.is_quiet:
            return True
        return event_type in ANNOUNCEMENT_EVENTS

    def publish(
        self, event_type: str, *, agent: str | None = None, text: str = "", **data: Any
    ) -> None:
        """Publica um evento de forma thread-safe (no-op em modo quiet p/ eventos não canônicos)."""
        if not self._should_publish(event_type):
            return
        event = ProgressEvent(type=event_type, agent=agent, text=text, data=data)
        with self._lock:
            subscribers = list(self._queues)
        for loop, queue in subscribers:
            try:
                loop.call_soon_threadsafe(self._offer, queue, event)
            except RuntimeError:
                # Loop do subscriber já fechado; descarta silenciosamente.
                with self._lock:
                    self.dropped += 1

    @staticmethod
    def _offer(queue: asyncio.Queue[ProgressEvent | None], event: ProgressEvent) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:  # pragma: no cover — fila sempre ilimitada
            pass

    def announce(self, text: str, *, agent: str | None = None, **data: Any) -> None:
        """Anúncio canônico (exibido mesmo em modo quiet)."""
        self.publish("announcement", agent=agent, text=text, **data)

    # ----------------------------------------------------------------- sub
    def subscribe(self) -> tuple[asyncio.Queue[ProgressEvent | None], callable]:  # type: ignore[valid-type]
        """Registra um subscriber no loop atual. Retorna (fila, unsubscribe)."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        entry = (loop, queue)
        with self._lock:
            self._queues.append(entry)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._queues.remove(entry)
                except ValueError:  # pragma: no cover
                    pass
            queue.put_nowait(None)

        return queue, unsubscribe

    async def stream(self) -> AsyncIterator[ProgressEvent]:
        """Consome eventos até receber o sentinel de unsubscribe."""
        queue, unsubscribe = self.subscribe()
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            unsubscribe()

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._queues)


ABORT_EVENT = threading.Event()
"""Bandeira global de interrupção humana (ESC ESC). Checada pelo runner a
cada evento de stream e pelo orquestrador entre agentes — aborta de verdade,
sem matar o processo nem perder o que já foi gravado."""


BUS = TuringProgressBus()
"""Barramento global do processo — usado pelo orquestrador, AgentRunner e interfaces."""
