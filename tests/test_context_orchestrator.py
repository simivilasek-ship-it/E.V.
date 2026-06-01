"""Testy pro ContextOrchestrator."""

import time
import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from context_orchestrator import ContextOrchestrator


@pytest.fixture
def orch():
    return ContextOrchestrator(config={})


def test_get_time_returns_string(orch):
    result = orch._get_time()
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_clipboard_empty_on_error(orch):
    with patch("subprocess.run", side_effect=Exception("no xclip")):
        with patch.dict("sys.modules", {"pyperclip": None}):
            result = orch._get_clipboard()
    assert result == ""


def test_get_active_window_empty_on_error(orch):
    with patch("subprocess.run", side_effect=Exception("no xdotool")):
        result = orch._get_active_window()
    assert result == ""


def test_format_minimal(orch):
    ctx = {"time": "12:00, Monday 01.01.2024", "window": "", "clipboard": "", "system": {}}
    result = orch._format(ctx)
    lines = result.strip().split("\n")
    assert len(lines) == 1
    assert "Aktuální čas:" in lines[0]


def test_format_with_window(orch):
    ctx = {
        "time": "12:00, Monday 01.01.2024",
        "active": "Firefox — Google",
        "windows": ["Firefox — Google"],
        "clipboard": "",
        "system": {},
    }
    result = orch._format(ctx)
    assert "Aktivní okno:" in result
    assert "Firefox" in result


def test_cache_ttl(orch):
    """Druhé volání get_context() do TTL neaktualizuje data."""
    call_count = 0

    original_get_time = orch._get_time

    def counting_get_time():
        nonlocal call_count
        call_count += 1
        return original_get_time()

    orch._get_time = counting_get_time

    # První volání — cache prázdná, musí zavolat _get_time
    orch.get_context()
    assert call_count == 1

    # Druhé volání ihned — cache platná, nesmí volat _get_time znovu
    orch.get_context()
    assert call_count == 1
