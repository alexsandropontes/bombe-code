from __future__ import annotations

import json
from collections.abc import Sequence

from .models import Message, Part, TextPart, ToolPart


def _text_of(parts: Sequence[Part]) -> str:
    return "".join(p.text for p in parts if isinstance(p, TextPart))


def _tools_of(parts: Sequence[Part]) -> list[ToolPart]:
    return [p for p in parts if isinstance(p, ToolPart)]


def _openai_pair(message: Message, parts: Sequence[Part]) -> list[dict]:
    if message.role == "system":
        return [{"role": "system", "content": _text_of(parts)}]
    if message.role == "user":
        return [{"role": "user", "content": _text_of(parts)}]

    tools = _tools_of(parts)
    text = _text_of(parts)
    out: list[dict] = []
    assistant: dict = {"role": "assistant", "content": text or None}
    if tools:
        assistant["tool_calls"] = [
            {
                "id": t.tool_call_id or t.id,
                "type": "function",
                "function": {"name": t.tool, "arguments": json.dumps(t.arguments)},
            }
            for t in tools
        ]
    out.append(assistant)
    for tool in tools:
        if tool.state in ("completed", "error"):
            content = tool.output if tool.state == "completed" else f"error: {tool.output}"
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": tool.tool_call_id or tool.id,
                    "content": content,
                }
            )
    return out


def _anthropic_pair(message: Message, parts: Sequence[Part]) -> list[dict]:
    if message.role == "system":
        return [
            {
                "role": "user",
                "content": [{"type": "text", "text": f"[system]\n{_text_of(parts)}"}],
            }
        ]
    if message.role == "user":
        return [
            {"role": "user", "content": [{"type": "text", "text": _text_of(parts)}]}
        ]

    tools = _tools_of(parts)
    blocks: list[dict] = []
    text = _text_of(parts)
    if text:
        blocks.append({"type": "text", "text": text})
    for tool in tools:
        blocks.append(
            {
                "type": "tool_use",
                "id": tool.tool_call_id or tool.id,
                "name": tool.tool,
                "input": tool.arguments,
            }
        )
    if not blocks:
        blocks.append({"type": "text", "text": ""})
    out = [{"role": "assistant", "content": blocks}]
    results = [t for t in tools if t.state in ("completed", "error")]
    if results:
        out.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": t.tool_call_id or t.id,
                        "content": t.output,
                        "is_error": t.state == "error",
                    }
                    for t in results
                ],
            }
        )
    return out


def to_provider_messages(
    history: Sequence[tuple[Message, Sequence[Part]]], provider: str
) -> list[dict]:
    mapper = _anthropic_pair if provider == "anthropic" else _openai_pair
    out: list[dict] = []
    for message, parts in history:
        out.extend(mapper(message, parts))
    return out
