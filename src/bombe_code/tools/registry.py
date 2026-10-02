from __future__ import annotations

import importlib.util
from collections.abc import Collection
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .base import InvalidArgumentsError, ToolContext, ToolDef, truncate
from .builtin import agent_tools, fs_tools, shell_tools, snippet_tools, web_tools

_GPT_BLOCKED = frozenset({"edit", "write"})


class _EmptyArgs(BaseModel):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> ToolDef:
        try:
            return self._tools[tool_id]
        except KeyError:
            raise KeyError(f"ferramenta desconhecida: {tool_id}") from None

    def list(self) -> list[ToolDef]:
        return list(self._tools.values())

    def tools_for_model(self, model: str, disabled: Collection[str] = ()) -> list[ToolDef]:
        blocked = set(disabled)
        tools = [t for t in self._tools.values() if t.id not in blocked]
        if "gpt" in model.lower():
            tools = [t for t in tools if t.id not in _GPT_BLOCKED]
        return tools

    def execute(self, tool_id: str, args: dict, ctx: ToolContext) -> str:
        tool = self.get(tool_id)
        try:
            parsed = tool.parameters.model_validate(args)
        except ValidationError as exc:
            raise InvalidArgumentsError(str(exc)) from exc
        return truncate(str(tool.execute(parsed.model_dump(), ctx)))


_BUILTINS = (
    agent_tools.INVALID_TOOL,
    agent_tools.QUESTION_TOOL,
    shell_tools.SHELL_TOOL,
    fs_tools.READ_TOOL,
    fs_tools.GLOB_TOOL,
    fs_tools.GREP_TOOL,
    fs_tools.EDIT_TOOL,
    fs_tools.WRITE_TOOL,
    agent_tools.TASK_TOOL,
    web_tools.WEBFETCH_TOOL,
    agent_tools.TODOWRITE_TOOL,
    web_tools.WEBSEARCH_TOOL,
    agent_tools.SKILL_TOOL,
    fs_tools.APPLY_PATCH_TOOL,
    snippet_tools.SNIPPET_SEARCH_TOOL,
    snippet_tools.SNIPPET_GET_TOOL,
)


def builtin_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in _BUILTINS:
        registry.register(tool)
    return registry


def load_custom_tools(registry: ToolRegistry, project_dir: Path | str) -> list[str]:
    base = Path(project_dir)
    loaded: list[str] = []
    for dir_name in ("tools", "tool"):
        directory = base / dir_name
        if not directory.is_dir():
            continue
        for file in sorted(directory.iterdir()):
            if file.is_file() and file.suffix == ".py":
                loaded.extend(_load_py_tool(registry, file))
            elif file.is_file() and file.suffix == ".md":
                loaded.append(_load_md_tool(registry, file))
    return loaded


def _load_py_tool(registry: ToolRegistry, file: Path) -> list[str]:
    spec = importlib.util.spec_from_file_location(f"bombe_custom_{file.stem}", file)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool = getattr(module, "TOOL", None)
    if isinstance(tool, ToolDef):
        registry.register(tool)
        return [tool.id]
    return []


def _load_md_tool(registry: ToolRegistry, file: Path) -> str:
    content = file.read_text(encoding="utf-8")

    def execute(args: dict, ctx: ToolContext, _body: str = content) -> str:
        return _body

    registry.register(
        ToolDef(
            id=file.stem,
            description=f"documento markdown: {file.name}",
            parameters=_EmptyArgs,
            execute=execute,
        )
    )
    return file.stem
