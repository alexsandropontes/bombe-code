from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ...config.paths import get_paths
from ...storage.kv import write_json
from ..base import ToolContext, ToolDef


class InvalidArgs(BaseModel):
    error: str


class QuestionArgs(BaseModel):
    question: str


class TaskArgs(BaseModel):
    prompt: str


class TodoItem(BaseModel):
    content: str
    status: Literal["pending", "in_progress", "completed"]


class TodowriteArgs(BaseModel):
    todos: list[TodoItem]


class SkillArgs(BaseModel):
    name: str


def _invalid(args: dict, ctx: ToolContext) -> str:
    return (
        "Invalid tool call. Reason: "
        f"{args['error']}. Correct the arguments and call the tool again."
    )


def _question(args: dict, ctx: ToolContext) -> str:
    return str(ctx.ask("question", args["question"]))


def _task(args: dict, ctx: ToolContext) -> str:
    return str(ctx.run_subtask(args["prompt"]))


def _todowrite(args: dict, ctx: ToolContext) -> str:
    session = ctx.session_id or "sem-sessao"
    path = get_paths().data / "storage" / "todos" / f"{session}.json"
    todos = [TodoItem.model_validate(item).model_dump() for item in args["todos"]]
    write_json(path, {"todos": todos})
    return f"Todos atualizados: {len(todos)}"


def _skill(args: dict, ctx: ToolContext) -> str:
    from ...skills.discovery import discover_skills, get_skill_by_name

    base = Path(ctx.project_dir or ".")
    skills = discover_skills(base)
    found = get_skill_by_name(skills, args["name"])
    if found:
        return found.content

    candidates = [
        base / ".agent" / "skills" / args["name"] / "SKILL.md",
        base / ".bombe" / "skills" / args["name"] / "SKILL.md",
        base / ".bombe" / "skills" / args["name"] / f"{args['name']}.md",
        base / ".bombe" / "skills" / f"{args['name']}.md",
        base / "skills" / args["name"] / f"{args['name']}.md",
        base / "skills" / f"{args['name']}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return f"Erro: skill nao encontrada: {args['name']}"


INVALID_TOOL = ToolDef(
    id="invalid",
    description="Retorna feedback de tool call invalida",
    parameters=InvalidArgs,
    execute=_invalid,
)
QUESTION_TOOL = ToolDef(
    id="question", description="Faz pergunta ao usuario", parameters=QuestionArgs, execute=_question
)
TASK_TOOL = ToolDef(
    id="task", description="Delega para subtask/subagente", parameters=TaskArgs, execute=_task
)
TODOWRITE_TOOL = ToolDef(
    id="todowrite",
    description="Persiste lista de todos",
    parameters=TodowriteArgs,
    execute=_todowrite,
)
SKILL_TOOL = ToolDef(
    id="skill",
    description="Carrega skill markdown do projeto",
    parameters=SkillArgs,
    execute=_skill,
)
