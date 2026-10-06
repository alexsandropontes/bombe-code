from __future__ import annotations

import json
import threading


class EventBus:
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._events: list[dict] = []
        self._seq = 0

    def publish(self, event: dict) -> dict:
        with self._cond:
            self._seq += 1
            entry = {"seq": self._seq, **event}
            self._events.append(entry)
            self._cond.notify_all()
            return entry

    def since(self, last_id: int) -> list[dict]:
        with self._cond:
            return [e for e in self._events if e["seq"] > last_id]

    def _wait_batch(self, last_id: int, timeout: float = 0.016) -> list[dict]:
        with self._cond:
            fresh = [e for e in self._events if e["seq"] > last_id]
            if not fresh:
                self._cond.wait(timeout)
                fresh = [e for e in self._events if e["seq"] > last_id]
            return fresh

    def stream(self, last_id: int, session_id: str | None = None, ping_interval: float = 10.0):
        cursor = last_id
        while True:
            batch = self._wait_batch(cursor, timeout=ping_interval)
            if not batch:
                yield {"seq": cursor, "type": "ping", "session_id": session_id}
                continue
            for entry in batch:
                cursor = entry["seq"]
                if session_id is None or entry.get("session_id") == session_id:
                    yield entry


def sse_format(entry: dict) -> str:
    if entry.get("type") == "ping":
        return ": ping\n\n"
    payload = {k: v for k, v in entry.items() if k != "seq"}
    return f"id: {entry['seq']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
