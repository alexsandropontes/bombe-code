from __future__ import annotations

import fnmatch
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..config.paths import get_paths
from ..storage.kv import read_json, write_json

Action = Literal["allow", "deny", "ask"]
Decision = Literal["once", "always", "reject"]


@dataclass
class Rule:
    permission: str = "*"
    pattern: str = "*"
    action: Action = "ask"


def saved_path() -> Path:
    return get_paths().data / "storage" / "permissions" / "saved.json"


def _expand(pattern: str) -> str:
    if pattern.startswith("~/"):
        return str(Path.home() / pattern[2:])
    if pattern == "~":
        return str(Path.home())
    return pattern


def _matches(rule: Rule, permission: str, details: str) -> bool:
    return fnmatch.fnmatch(permission, rule.permission) and fnmatch.fnmatch(
        details, _expand(rule.pattern)
    )


def _load_approved() -> list[Rule]:
    data = read_json(saved_path())
    if not isinstance(data, dict):
        return []
    return [
        Rule(
            permission=item["permission"],
            pattern=item["pattern"],
            action=item["action"],
        )
        for item in data.get("approved", [])
    ]


class PermissionService:
    def __init__(
        self,
        rules: list[Rule] | None = None,
        approved: list[Rule] | None = None,
    ) -> None:
        self.rules = rules or []
        self.approved = approved if approved is not None else _load_approved()
        self._lock = threading.Lock()
        self._pending: dict[str, threading.Event] = {}
        self._replies: dict[str, str] = {}

    @staticmethod
    def _key(permission: str, details: str) -> str:
        return f"{permission}\x00{details}"

    def evaluate(self, permission: str, details: str = "") -> Action:
        decision: Action = "ask"
        for rule in [*self.rules, *self.approved]:
            if _matches(rule, permission, details):
                decision = rule.action
        return decision

    def disabled_tools(self) -> set[str]:
        hidden = {
            rule.permission
            for rule in [*self.rules, *self.approved]
            if rule.action == "deny" and rule.pattern == "*"
        }
        return hidden

    def ask(self, permission: str, details: str = "", emit=None) -> str:
        decision = self.evaluate(permission, details)
        if decision == "allow":
            return "allow"
        if decision == "deny":
            return "deny"

        key = self._key(permission, details)
        event = threading.Event()
        with self._lock:
            preloaded = self._replies.pop(key, None)
            if preloaded is None:
                self._pending[key] = event

        if preloaded is not None:
            reply = preloaded
        else:
            if emit:
                emit(
                    {
                        "type": "permission.request",
                        "permission": permission,
                        "details": details,
                    }
                )
            event.wait()
            with self._lock:
                reply = self._replies.pop(key, "reject")
                self._pending.pop(key, None)

        return self._resolve(reply, permission, details)

    def _resolve(self, reply: str, permission: str, details: str) -> str:
        if reply == "always":
            self._persist(Rule(permission=permission, pattern=details, action="allow"))
            return "allow"
        if reply == "once":
            return "allow"
        return "deny"

    def reply(self, permission: str, details: str, decision: Decision) -> None:
        key = self._key(permission, details)
        with self._lock:
            self._replies[key] = decision
            event = self._pending.get(key)
        if event is not None:
            event.set()

    def _persist(self, rule: Rule) -> None:
        path = saved_path()
        data = read_json(path) or {"approved": []}
        entry = {
            "permission": rule.permission,
            "pattern": rule.pattern,
            "action": rule.action,
        }
        if entry not in data["approved"]:
            data["approved"].append(entry)
        write_json(path, data)
        with self._lock:
            self.approved.append(rule)


def from_saved(
    rules: list[Rule] | None = None, approved: list[Rule] | None = None
) -> PermissionService:
    return PermissionService(rules=rules, approved=approved)
