"""Tests for agent_roles.py — MultiAgent Role System."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"


def _mock_response(content: str) -> MagicMock:
    """Vytvoří mock requests.Response s daným obsahem."""
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"message": {"content": content}}
    return mock


# ── PlannerAgent ────────────────────────────────────────────────────

def test_planner_returns_list():
    """planner.plan() vrátí list stringů."""
    from agent_roles import PlannerAgent
    planner = PlannerAgent(OLLAMA_URL, MODEL)
    mock_content = "1. Vyhledej informace\n2. Zpracuj data\n3. Zobraz výsledek"
    with patch("requests.post", return_value=_mock_response(mock_content)):
        result = planner.plan("Zjisti počasí v Praze")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(s, str) for s in result)


def test_planner_empty_on_error():
    """Chyba Ollama → vrátí []."""
    from agent_roles import PlannerAgent
    planner = PlannerAgent(OLLAMA_URL, MODEL)
    with patch("requests.post", side_effect=Exception("Connection refused")):
        result = planner.plan("Zjisti počasí")
    assert result == []


# ── CriticAgent ─────────────────────────────────────────────────────

def test_critic_success():
    """'SUCCESS: hotovo' → (True, 'hotovo')."""
    from agent_roles import CriticAgent
    critic = CriticAgent(OLLAMA_URL, MODEL)
    with patch("requests.post", return_value=_mock_response("SUCCESS: hotovo")):
        ok, feedback = critic.evaluate("Vyhledej X", "Nalezeno Y")
    assert ok is True
    assert "hotovo" in feedback


def test_critic_retry():
    """'RETRY: chybí X' → (False, 'chybí X')."""
    from agent_roles import CriticAgent
    critic = CriticAgent(OLLAMA_URL, MODEL)
    with patch("requests.post", return_value=_mock_response("RETRY: chybí X")):
        ok, feedback = critic.evaluate("Vyhledej X", "")
    assert ok is False
    assert "chybí X" in feedback


# ── ExecutorAgent ───────────────────────────────────────────────────

def test_executor_returns_string():
    """execute() vrátí string."""
    from agent_roles import ExecutorAgent
    executor = ExecutorAgent(OLLAMA_URL, MODEL)
    with patch("requests.post", return_value=_mock_response("Akce provedena úspěšně.")):
        result = executor.execute("Otevři prohlížeč")
    assert isinstance(result, str)
    assert len(result) > 0


# ── MultiAgentOrchestrator ──────────────────────────────────────────

def test_orchestrator_run_returns_string():
    """run() vrátí neprázdný string."""
    from agent_roles import MultiAgentOrchestrator

    planner_content = "1. Krok první\n2. Krok druhý"
    executor_content = "Hotovo."
    critic_content = "SUCCESS: vše OK"

    responses = [
        _mock_response(planner_content),   # planner.plan()
        _mock_response(executor_content),  # executor krok 1
        _mock_response(critic_content),    # critic krok 1
        _mock_response(executor_content),  # executor krok 2
        _mock_response(critic_content),    # critic krok 2
    ]

    orch = MultiAgentOrchestrator(OLLAMA_URL, MODEL)
    with patch("requests.post", side_effect=responses):
        result = orch.run("Splň složitý úkol")

    assert isinstance(result, str)
    assert len(result) > 0
