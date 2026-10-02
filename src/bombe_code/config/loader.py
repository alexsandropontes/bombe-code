from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .paths import discover_config, get_paths

_CONFIG_NAMES = ("bombe.json", "bombe.jsonc")


def deep_merge(base: Mapping, override: Mapping) -> dict:
    result = dict(base)
    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = deep_merge(existing, value)
        elif isinstance(existing, list) and isinstance(value, list):
            result[key] = [*existing, *value]
        else:
            result[key] = value
    return result


def _comment_end(text: str, i: int) -> int | None:
    n = len(text)
    if i + 1 >= n or text[i] != "/":
        return None
    if text[i + 1] == "/":
        end = i + 2
        while end < n and text[end] != "\n":
            end += 1
        return end
    if text[i + 1] == "*":
        end = i + 2
        while end + 1 < n and not (text[end] == "*" and text[end + 1] == "/"):
            end += 1
        return min(end + 2, n)
    return None


def _strip_json_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        end = _comment_end(text, i)
        if end is not None:
            i = end
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _load_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonc":
        text = _strip_json_comments(text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise TypeError(f"Config deve ser um objeto JSON: {path}")
    return data


def _find_global_config() -> Path | None:
    config_dir = get_paths().config
    for name in _CONFIG_NAMES:
        candidate = config_dir / name
        if candidate.is_file():
            return candidate
    return None


def load_config(start: Path | None = None) -> dict:
    origin = Path.cwd() if start is None else Path(start)

    global_path = _find_global_config()
    global_data = _load_file(global_path) if global_path else {}

    discovered = discover_config(origin)
    if discovered is None:
        return global_data
    return deep_merge(global_data, _load_file(discovered))
