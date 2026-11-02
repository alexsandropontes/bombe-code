"""Unit tests for FallbackToolParser extracting tool calls from markdown and plain text."""

import time

from bombe_code.providers.protocol import ToolCallChunk
from bombe_code.tools.parser import FallbackToolParser


def test_extract_markdown_json_codeblock():
    """AC-01: Verify tool call extraction from ```json ``` block."""
    parser = FallbackToolParser()
    text = (
        "Com certeza, vou ler o arquivo agora:\n\n"
        "```json\n"
        '{\n  "tool": "read_file",\n  "arguments": {"path": "/tmp/test.txt"}\n}\n'
        "```\n\n"
        "Aguardando o resultado."
    )
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 1
    call = calls[0]
    assert isinstance(call, ToolCallChunk)
    assert call.name == "read_file"
    assert '"path": "/tmp/test.txt"' in call.arguments_delta
    assert call.index == 0


def test_extract_markdown_without_json_tag():
    """Verify tool call extraction from generic ``` ``` code block."""
    parser = FallbackToolParser()
    text = (
        "Aqui está o comando:\n"
        "```\n"
        '{"tool": "run_command", "arguments": {"cmd": "git status"}}\n'
        "```"
    )
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 1
    assert calls[0].name == "run_command"
    assert '"cmd": "git status"' in calls[0].arguments_delta


def test_extract_raw_json_in_plain_text():
    """AC-02: Verify tool call extraction from plain text without markdown fences."""
    parser = FallbackToolParser()
    text = 'Vou executar a tool {"name": "list_files", "arguments": {"dir": "src/"}} agora mesmo.'
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 1
    assert calls[0].name == "list_files"
    assert '"dir": "src/"' in calls[0].arguments_delta


def test_extract_multiple_tool_calls_in_single_message():
    """Verify multiple tool call blocks in the same response are all extracted with sequential indices."""
    parser = FallbackToolParser()
    text = (
        "Primeiro vou verificar o status:\n"
        "```json\n"
        '{"tool": "run_command", "arguments": {"command": "git status"}}\n'
        "```\n"
        "Em seguida, lerei o arquivo de configuração:\n"
        "```json\n"
        '{"tool": "read_file", "arguments": {"path": "config.yaml"}}\n'
        "```"
    )
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 2
    assert calls[0].name == "run_command"
    assert calls[0].index == 0
    assert calls[1].name == "read_file"
    assert calls[1].index == 1


def test_preserves_complex_and_nested_arguments():
    """AC-04: Verify nested objects, arrays, and escaped quotes are preserved accurately."""
    parser = FallbackToolParser()
    text = (
        "```json\n"
        "{\n"
        '  "tool": "write_file",\n'
        '  "arguments": {\n'
        '    "path": "/home/app/script.py",\n'
        '    "content": "def hello():\\n    print(\\"Hello, world!\\")\\n",\n'
        '    "metadata": {"tags": ["python", "test"], "version": 2}\n'
        "  }\n"
        "}\n"
        "```"
    )
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 1
    call = calls[0]
    assert call.name == "write_file"
    assert "Hello, world!" in call.arguments_delta
    assert '"tags": ["python", "test"]' in call.arguments_delta


def test_tolerates_name_and_parameters_synonyms():
    """Verify tool calls using 'name' and 'parameters' are normalized transparently."""
    parser = FallbackToolParser()
    text = '```json\n{"name": "fetch_url", "parameters": {"url": "https://api.github.com"}}\n```'
    calls = parser.extract_tool_calls(text)

    assert len(calls) == 1
    assert calls[0].name == "fetch_url"
    assert '"url": "https://api.github.com"' in calls[0].arguments_delta


def test_tolerates_corrupted_or_invalid_json_gracefully():
    """AC-03: Verify truncated, corrupted, or non-tool JSON does not raise exception."""
    parser = FallbackToolParser()
    malformed_texts = [
        "```json\n{ this is clearly not json }\n```",
        '```json\n{\n  "tool": "broken_json",\n  "arguments": { missing closing bracket\n```',
        "Texto comum sem nenhum json embutido.",
        '```json\n{"data": [1, 2, 3], "message": "Just a config payload"}\n```',  # Sem chave tool/name
    ]

    for sample in malformed_texts:
        calls = parser.extract_tool_calls(sample)
        assert isinstance(calls, list)
        assert len(calls) == 0


def test_parsing_performance_benchmark():
    """Verify average parsing latency is strictly under 5ms per chunk."""
    parser = FallbackToolParser()
    payload = (
        "Analisei a solicitação e vou criar o arquivo agora:\n\n"
        "```json\n"
        "{\n"
        '  "tool": "edit_file",\n'
        '  "arguments": {\n'
        '    "path": "src/module.py",\n'
        '    "content": "class MyService:\\n    pass\\n"\n'
        "  }\n"
        "}\n"
        "```\n\n"
        "Por favor confirme a execução."
    )

    # Warmup
    for _ in range(10):
        parser.extract_tool_calls(payload)

    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        res = parser.extract_tool_calls(payload)
        assert len(res) == 1
    duration = time.perf_counter() - start

    avg_ms = (duration / iterations) * 1000
    assert avg_ms < 5.0, f"Average latency too high: {avg_ms:.2f}ms >= 5.0ms"
