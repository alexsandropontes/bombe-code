"""Testes unitários para o detector de estouro de cota e rate limit de LLMs e Coding Plans."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock

from bombe_code.agents.runner import AgentRunner
from bombe_code.llm.quota_detector import is_quota_or_rate_limit_error


class MockHTTPStatusError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class MockOpenAIRateLimitError(Exception):
    pass


def test_quota_detector_identifies_http_429():
    err = MockHTTPStatusError(429, "Too Many Requests")
    is_quota, reason = is_quota_or_rate_limit_error(err)
    assert is_quota is True
    assert "429" in reason


def test_quota_detector_identifies_http_402():
    err = MockHTTPStatusError(402, "Payment Required")
    is_quota, reason = is_quota_or_rate_limit_error(err)
    assert is_quota is True
    assert "402" in reason


def test_quota_detector_identifies_zai_1301_quota_code():
    class ZaiError(Exception):
        def __init__(self):
            super().__init__("Z.ai Coding Plan Error: 1301 Insufficient balance or quota exceeded")
            self.code = 1301

    err = ZaiError()
    is_quota, reason = is_quota_or_rate_limit_error(err)
    assert is_quota is True
    assert "1301" in reason or "quota" in reason.lower()


def test_quota_detector_identifies_text_patterns():
    patterns = [
        "Your account has exceeded its current quota",
        "insufficient_quota: you do not have enough credits",
        "Rate limit reached for requests per minute",
        "Resource has been exhausted (code 429)",
    ]
    for p in patterns:
        is_quota, reason = is_quota_or_rate_limit_error(RuntimeError(p))
        assert is_quota is True
        assert reason is not None


def test_quota_detector_ignores_generic_errors():
    generic_errors = [
        RuntimeError("Connection reset by peer"),
        ValueError("Invalid JSON response"),
        TimeoutError("Request timed out after 30s"),
    ]
    for err in generic_errors:
        is_quota, reason = is_quota_or_rate_limit_error(err)
        assert is_quota is False
        assert reason is None


def test_agent_runner_marks_quota_exhausted_as_blocked(tmp_path):
    from bombe_code.agents.registry import AgentRegistry

    agent_def = AgentRegistry.default().get("@barbara")

    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_agent.run.side_effect = MockHTTPStatusError(429, "Rate limit / quota exceeded")
    mock_factory.create_agent.return_value = mock_agent

    mock_db = MagicMock()
    mock_db.create_agent_task.return_value = "task-429"

    runner = AgentRunner(
        agent=agent_def,
        llm_factory=mock_factory,
        project_db=mock_db,
    )

    result = runner.run(prompt="Implementar endpoint")

    assert result.success is False
    assert result.status == "QUOTA_EXHAUSTED"
    assert result.is_blocked is True
    assert "429" in result.block_reason
    # Garante que no banco a task foi registrada como blocked, não falha genérica
    from unittest.mock import call

    mock_db.update_agent_task_status.assert_has_calls(
        [
            call("task-429", "in_progress"),
            call("task-429", "blocked", output=result.block_reason),
        ]
    )


def test_parse_quota_reset_info_zai_beijing_timezone():
    from datetime import datetime

    from bombe_code.llm.quota_detector import parse_quota_reset_info

    raw_err = (
        "status_code: 429, model_name: glm-5.3-flash, body: {'code': '1308', "
        "'message': 'Usage limit reached for 5 hour. Your limit will reset at 2026-10-03 16:02:39'}"
    )

    # 1. Simula horário ANTES do reset (ex: 07:02:39 UTC, que é 15:02:39 em Beijing CST)
    t_before = datetime(2026, 10, 3, 7, 2, 39, tzinfo=UTC)
    info = parse_quota_reset_info(raw_err, current_time=t_before)

    assert info.is_exhausted is True
    assert info.is_already_reset is False
    assert info.origin_timezone_name == "Asia/Shanghai (CST UTC+8)"
    assert info.retry_after_seconds == 3600.0  # exatamente 1 hora
    assert "Reset previsto em 60m 0s" in info.human_message

    # 2. Simula horário DEPOIS do reset (ex: 10:29:00 UTC, que é 18:29:00 em Beijing CST)
    t_after = datetime(2026, 10, 3, 10, 29, 0, tzinfo=UTC)
    info_after = parse_quota_reset_info(raw_err, current_time=t_after)

    assert info_after.is_exhausted is True
    assert info_after.is_already_reset is True
    assert info_after.retry_after_seconds <= 0
    assert "já está liberada" in info_after.human_message


def test_parse_quota_reset_info_relative_seconds():
    from datetime import datetime

    from bombe_code.llm.quota_detector import parse_quota_reset_info

    raw_err = "Rate limit reached. Please try again in 45.5s."
    t_now = datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)
    info = parse_quota_reset_info(raw_err, current_time=t_now)

    assert info.is_exhausted is True
    assert info.retry_after_seconds == 45.5
    assert info.is_already_reset is False
    assert "45s" in info.human_message
