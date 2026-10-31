"""Resilient fallback parser for tool calls embedded in markdown or plain text."""

from __future__ import annotations

import json
import re
from typing import Any

from bombe_code.providers.protocol import ToolCallChunk


class FallbackToolParser:
    """Extracts tool calls from markdown codeblocks or plain text emitted by compact models."""

    # Pre-compiled regex patterns for maximum runtime performance (< 5ms)
    _MARKDOWN_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.DOTALL)
    _RAW_JSON_PATTERN = re.compile(r"(\{\s*\"(?:tool|name)\"\s*:[\s\S]*?\})", re.DOTALL)

    def extract_tool_calls(self, text: str) -> list[ToolCallChunk]:
        """Extract all valid tool calls found in text without raising exceptions."""
        if not text or ("tool" not in text and "name" not in text):
            return []

        chunks: list[ToolCallChunk] = []

        # 1. Search in markdown codeblocks
        markdown_blocks = self._MARKDOWN_BLOCK_PATTERN.findall(text)
        if markdown_blocks:
            for block in markdown_blocks:
                call = self._parse_json_candidate(block, len(chunks))
                if call is not None:
                    chunks.append(call)
            if chunks:
                return chunks

        # 2. Search for raw JSON candidates in text using balanced raw_decode
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(text):
            brace_idx = text.find("{", pos)
            if brace_idx == -1:
                break
            try:
                obj, end_offset = decoder.raw_decode(text[brace_idx:])
                if isinstance(obj, dict):
                    call = self._build_tool_call_from_dict(obj, len(chunks))
                    if call is not None:
                        chunks.append(call)
                pos = brace_idx + end_offset
            except json.JSONDecodeError:
                pos = brace_idx + 1

        return chunks

    def _build_tool_call_from_dict(self, data: dict[str, Any], index: int) -> ToolCallChunk | None:
        tool_name = data.get("tool") or data.get("name")
        if not tool_name or not isinstance(tool_name, str):
            return None

        raw_args = data.get("arguments") or data.get("parameters") or {}
        if isinstance(raw_args, (dict, list)):
            arguments_delta = json.dumps(raw_args, ensure_ascii=False)
        elif isinstance(raw_args, str):
            arguments_delta = raw_args
        else:
            arguments_delta = json.dumps(raw_args, ensure_ascii=False)

        return ToolCallChunk(
            index=index,
            call_id=f"call_{index}",
            name=tool_name,
            arguments_delta=arguments_delta,
        )

    def _parse_json_candidate(self, candidate_str: str, index: int) -> ToolCallChunk | None:
        """Parse and normalize candidate string to ToolCallChunk, returning None on error."""
        candidate_str = candidate_str.strip()
        try:
            data = json.loads(candidate_str)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        return self._build_tool_call_from_dict(data, index)
