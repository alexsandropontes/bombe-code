"""Unified protocol and data structures for LLM providers."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""


class VllmConnectionError(LLMProviderError):
    """Raised when communication with the local vLLM server fails."""


class QueueCapacityError(LLMProviderError):
    """Raised when local vLLM queue rejects or exceeds capacity."""


@dataclass(frozen=True)
class CompletionChunk:
    """Immutable streaming completion chunk."""

    delta: str = ""
    finish_reason: str | None = None
    model: str = ""
    usage: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolCallChunk:
    """Immutable tool call streaming delta."""

    index: int = 0
    call_id: str | None = None
    name: str | None = None
    arguments_delta: str = ""


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Unified contract for LLM inference providers."""

    @property
    def name(self) -> str:
        """Provider identifier."""
        ...

    @property
    def provider_type(self) -> str:
        """Type of provider: 'local', 'cloud', etc."""
        ...

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream chat completions asynchronously."""
        ...

    async def check_health(self) -> bool:
        """Check if provider is healthy and ready for inference."""
        ...
