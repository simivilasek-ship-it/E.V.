"""Unit tests for error_handling.ErrorHandler."""
from __future__ import annotations

import pytest

from error_handling import (
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    FallbackResult,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def handler():
    return ErrorHandler({"max_error_log": 10, "rate_limit_window": 60.0, "rate_limit_max": 50})


def test_execute_primary_success(handler):
    result = handler.execute_with_fallback("op", lambda: 42)
    assert result.success is True
    assert result.result == 42
    assert result.fallback_used is False


def test_execute_uses_fallback(handler):
    handler.register_fallback("op", lambda: "fb")
    result = handler.execute_with_fallback("op", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert result.success is True
    assert result.result == "fb"
    assert result.fallback_used is True
    assert result.fallback_source == "<lambda>"


def test_execute_all_fail(handler):
    handler.register_fallback("op", lambda: (_ for _ in ()).throw(ValueError("fb fail")))
    result = handler.execute_with_fallback("op", lambda: (_ for _ in ()).throw(RuntimeError("primary")))
    assert result.success is False
    assert result.error_message == "primary"
    assert isinstance(result, FallbackResult)


def test_safe_execute_returns_default(handler):
    value = handler.safe_execute(lambda: 1 / 0, default="ok", error_message="div")
    assert value == "ok"
    assert len(handler.get_errors()) >= 1


def test_safe_execute_success(handler):
    assert handler.safe_execute(lambda: "yes", default="no") == "yes"


def test_log_error_and_get_recent(handler):
    handler.log_error(
        ErrorSeverity.ERROR,
        ErrorCategory.NETWORK,
        source="http",
        message="timeout",
    )
    recent = handler.get_errors(category=ErrorCategory.NETWORK)
    assert any(r.source == "http" for r in recent)
    stats = handler.get_error_stats()
    assert isinstance(stats, dict)


def test_register_recovery(handler):
    called = []

    def recover(record):
        called.append(record.source)
        return True

    handler.register_recovery("network", recover)
    assert "network" in handler._recovery_strategies
