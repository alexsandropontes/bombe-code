from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


def parse_sse(lines) -> Iterator[dict]:
    tool_map: dict[int, dict] = {}
    finish_reason: str | None = None
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}

        # 1. Reasoning / Thinking delta (Z.ai glm-5.3-flash, DeepSeek, Ollama, OpenAI o1/o3)
        reasoning = delta.get("reasoning_content") or delta.get("reasoning")
        if reasoning:
            yield {"type": "reasoning-delta", "text": reasoning}

        # 2. Content delta
        content = delta.get("content")
        if content:
            yield {"type": "text-delta", "text": content}
        for call in delta.get("tool_calls") or []:
            index = call.get("index", 0)
            entry = tool_map.setdefault(index, {"id": "", "name": "", "arguments": ""})
            if call.get("id"):
                entry["id"] = call["id"]
            function = call.get("function") or {}
            if function.get("name"):
                entry["name"] = function["name"]
            if function.get("arguments"):
                entry["arguments"] += function["arguments"]
        if choice.get("finish_reason"):
            finish_reason = choice["finish_reason"]

    for index in sorted(tool_map):
        entry = tool_map[index]
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

    if tool_map and finish_reason in (None, "tool_calls"):
        reason = "tool-calls"
    else:
        reason = "stop"
    yield {"type": "finish", "reason": reason}


class OpenAICompatAdapter:
    provider = "openai"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def stream(self, messages, tools=None, system=None) -> Iterator[dict]:
        payload: dict = {
            "model": self.model,
            "messages": self._messages(messages, system),
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["id"],
                        "description": tool["description"],
                        "parameters": tool["schema"],
                    },
                }
                for tool in tools
            ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        return self._iter(payload, headers)

    @staticmethod
    def _messages(messages, system) -> list[dict]:
        out = list(messages)
        if system:
            out = [{"role": "system", "content": system}] + out
        return out

    def _iter(self, payload: dict, headers: dict) -> Iterator[dict]:
        with (
            httpx.Client(timeout=120.0) as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response,
        ):
            response.raise_for_status()
            yield from parse_sse(response.iter_lines())
