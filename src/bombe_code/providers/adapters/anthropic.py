from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


def parse_anthropic_sse(lines) -> Iterator[dict]:
    tool_blocks: dict[int, dict] = {}
    stop_reason: str | None = None
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data:
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta" and delta.get("text"):
                yield {"type": "text-delta", "text": delta["text"]}
            elif delta.get("type") == "input_json_delta":
                index = event.get("index", 0)
                entry = tool_blocks.setdefault(index, {"id": "", "name": "", "arguments": ""})
                entry["arguments"] += delta.get("partial_json", "")
        elif event_type == "content_block_start":
            block = event.get("content_block") or {}
            if block.get("type") == "tool_use":
                index = event.get("index", 0)
                tool_blocks[index] = {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "arguments": "",
                }
        elif event_type == "message_delta":
            stop_reason = (event.get("delta") or {}).get("stop_reason")

    for index in sorted(tool_blocks):
        entry = tool_blocks[index]
        try:
            arguments = json.loads(entry["arguments"] or "{}")
        except json.JSONDecodeError:
            arguments = {}
        yield {
            "type": "tool-call",
            "id": entry["id"] or f"call_{index}",
            "name": entry["name"],
            "arguments": arguments,
        }

    reason = "tool-calls" if stop_reason == "tool_use" else "stop"
    yield {"type": "finish", "reason": reason}


class AnthropicAdapter:
    provider = "anthropic"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def stream(self, messages, tools=None, system=None) -> Iterator[dict]:
        payload: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": list(messages),
            "stream": True,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": tool["id"],
                    "description": tool["description"],
                    "input_schema": tool["schema"],
                }
                for tool in tools
            ]
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        return self._iter(payload, headers)

    def _iter(self, payload: dict, headers: dict) -> Iterator[dict]:
        with (
            httpx.Client(timeout=120.0) as client,
            client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=headers,
            ) as response,
        ):
            response.raise_for_status()
            yield from parse_anthropic_sse(response.iter_lines())
