"""Integration F6 — contrato dos adaptadores LLM via HTTP/SSE REAL local."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from bombe_code.providers.adapters.anthropic import AnthropicAdapter
from bombe_code.providers.adapters.openai_compat import OpenAICompatAdapter

pytestmark = pytest.mark.integration

OPENAI_SSE = (
    'data: {"choices":[{"index":0,"delta":{"content":"Ola"}}]}\n\n'
    'data: {"choices":[{"index":0,"delta":{"content":" mundo"}}]}\n\n'
    'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
    "data: [DONE]\n\n"
)

OPENAI_TOOL_SSE = (
    'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
    '"id":"call_9","function":{"name":"read","arguments":"{\\"path\\":\\"a.py\\"}"}}]}}]}\n\n'
    'data: {"choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}\n\n'
    "data: [DONE]\n\n"
)

ANTHROPIC_SSE = (
    "event: message_start\n"
    'data: {"type":"message_start"}\n\n'
    "event: content_block_delta\n"
    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Oi"}}\n\n'
    "event: message_delta\n"
    'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"}}\n\n'
    "event: message_stop\n"
    'data: {"type":"message_stop"}\n\n'
)


class _Recorder:
    def __init__(self) -> None:
        self.bodies: list[dict] = []
        self.headers: list[dict] = []


def _serve(body: str, recorder: _Recorder):
    class Handler(BaseHTTPRequestHandler):
        def _respond(self) -> None:
            recorder.headers.append(dict(self.headers))
            length = int(self.headers.get("Content-Length", 0))
            if length:
                recorder.bodies.append(json.loads(self.rfile.read(length)))
            payload = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            self._respond()

        def do_GET(self):
            self._respond()

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_openai_compat_stream_text_e_finish():
    recorder = _Recorder()
    server, base = _serve(OPENAI_SSE, recorder)
    try:
        adapter = OpenAICompatAdapter(model="gpt-4o", api_key="k", base_url=base)
        events = list(adapter.stream(messages=[{"role": "user", "content": "hi"}]))
    finally:
        server.shutdown()

    assert events == [
        {"type": "text-delta", "text": "Ola"},
        {"type": "text-delta", "text": " mundo"},
        {"type": "finish", "reason": "stop"},
    ]


def test_openai_compat_stream_emite_tool_call():
    recorder = _Recorder()
    server, base = _serve(OPENAI_TOOL_SSE, recorder)
    try:
        adapter = OpenAICompatAdapter(model="gpt-4o", api_key="k", base_url=base)
        events = list(adapter.stream(messages=[{"role": "user", "content": "hi"}]))
    finally:
        server.shutdown()

    tool_events = [e for e in events if e["type"] == "tool-call"]
    assert tool_events and tool_events[0]["name"] == "read"
    assert tool_events[0]["arguments"] == {"path": "a.py"}
    assert events[-1] == {"type": "finish", "reason": "tool-calls"}


def test_openai_adapter_envia_payload_valido():
    recorder = _Recorder()
    server, base = _serve(OPENAI_SSE, recorder)
    try:
        adapter = OpenAICompatAdapter(model="gpt-4o", api_key="sk-teste", base_url=base)
        list(
            adapter.stream(
                messages=[{"role": "user", "content": "hi"}],
                system="regras do projeto",
                tools=[
                    {
                        "id": "read",
                        "description": "le",
                        "schema": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                        },
                    }
                ],
            )
        )
    finally:
        server.shutdown()

    payload = recorder.bodies[0]
    assert payload["model"] == "gpt-4o"
    assert payload["stream"] is True
    assert payload["messages"][0] == {"role": "system", "content": "regras do projeto"}
    assert payload["messages"][1] == {"role": "user", "content": "hi"}
    assert payload["tools"][0]["function"]["name"] == "read"
    assert recorder.headers[0].get("Authorization") == "Bearer sk-teste"


def test_anthropic_stream_text_e_finish():
    recorder = _Recorder()
    server, base = _serve(ANTHROPIC_SSE, recorder)
    try:
        adapter = AnthropicAdapter(model="claude-sonnet-4", api_key="k", base_url=base)
        events = list(adapter.stream(messages=[{"role": "user", "content": "hi"}]))
    finally:
        server.shutdown()

    assert events == [
        {"type": "text-delta", "text": "Oi"},
        {"type": "finish", "reason": "stop"},
    ]


def test_anthropic_adapter_envia_payload_valido():
    recorder = _Recorder()
    server, base = _serve(ANTHROPIC_SSE, recorder)
    try:
        adapter = AnthropicAdapter(model="claude-sonnet-4", api_key="sk-ant", base_url=base)
        list(adapter.stream(messages=[{"role": "user", "content": "hi"}], system="sys"))
    finally:
        server.shutdown()

    payload = recorder.bodies[0]
    assert payload["model"] == "claude-sonnet-4"
    assert payload["system"] == "sys"
    assert payload["messages"] == [{"role": "user", "content": "hi"}]
    assert recorder.headers[0].get("x-api-key") == "sk-ant"
