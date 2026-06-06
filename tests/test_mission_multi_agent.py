"""Tests for multi-agent mission modes."""
from unittest.mock import MagicMock, patch

from mission_manager import MissionExecutor


def test_run_step_agent_multi():
    ex = MissionExecutor({"ollama_url": "http://x", "ollama_model": "m"})
    with patch.object(ex, "_run_multi_agent", return_value="multi ok") as m:
        assert ex._run_step_agent("krok", "multi") == "multi ok"
        m.assert_called_once()


def test_run_step_agent_parallel():
    ex = MissionExecutor({"ollama_url": "http://x", "ollama_model": "m"})
    with patch.object(ex, "_run_parallel", return_value="parallel ok") as p:
        assert ex._run_step_agent("krok", "parallel") == "parallel ok"
        p.assert_called_once()


def test_run_step_agent_single_fallback():
    ex = MissionExecutor({"ollama_url": "http://x", "ollama_model": "m"})
    with patch.object(ex, "_run_react", return_value="react ok") as r:
        assert ex._run_step_agent("krok", "single") == "react ok"
        r.assert_called_once()
