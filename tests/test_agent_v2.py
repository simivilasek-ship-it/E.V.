"""
Testy pro ReactAgentV2 a SupervisorAgent.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── ReactAgentV2 testy ────────────────────────────────────────────

def _make_react_v2():
    """Vytvoří ReactAgentV2 s mock registry a OllamaClient."""
    from agent_react import ReactAgentV2

    registry = MagicMock()
    registry.schema_block.return_value = ""
    registry.all.return_value = []

    with patch("agent_react.OllamaClient") as MockClient:
        MockClient.return_value = MagicMock()
        agent = ReactAgentV2(registry, "http://localhost:11434/api/chat", "test-model")
    return agent


def test_react_v2_introspect_empty():
    """Bez kroků introspect vrátí info zprávu."""
    agent = _make_react_v2()
    result = agent.introspect()
    assert result == "Žádná historie kroků."


def test_react_v2_rollback_no_history():
    """Bez historie rollback_last vrátí info zprávu."""
    agent = _make_react_v2()
    result = agent.rollback_last()
    assert result == "Žádný krok k odvolání."


# ── SupervisorAgent testy ─────────────────────────────────────────

def _make_supervisor():
    """Vytvoří SupervisorAgent s mock sub-agenty."""
    from agent_roles import SupervisorAgent

    with patch("agent_roles.PlannerAgent"), \
         patch("agent_roles.ResearcherAgent"), \
         patch("agent_roles.ExecutorAgent"), \
         patch("agent_roles.CriticAgent"):
        supervisor = SupervisorAgent("http://localhost:11434/api/chat", "test-model")
    return supervisor


def test_supervisor_route_research():
    """Krok obsahující 'vyhledej' je směrován na research."""
    supervisor = _make_supervisor()
    assert supervisor._route_step("vyhledej nejlepší GPU") == "research"


def test_supervisor_route_execute():
    """Krok bez klíčových slov pro research je směrován na execute."""
    supervisor = _make_supervisor()
    assert supervisor._route_step("spusť skript") == "execute"


def test_supervisor_run_with_mock():
    """Mock PlannerAgent + ExecutorAgent + CriticAgent → vrátí neprázdný string."""
    from agent_roles import SupervisorAgent

    with patch("agent_roles.PlannerAgent") as MockPlanner, \
         patch("agent_roles.ResearcherAgent"), \
         patch("agent_roles.ExecutorAgent") as MockExecutor, \
         patch("agent_roles.CriticAgent") as MockCritic:

        MockPlanner.return_value.plan.return_value = ["spusť krok A", "spusť krok B"]
        MockExecutor.return_value.execute.return_value = "výsledek A"
        MockCritic.return_value.evaluate.return_value = (True, "OK")

        supervisor = SupervisorAgent("http://localhost:11434/api/chat", "test-model")
        result = supervisor.run_with_delegation("testovací úkol")

    assert isinstance(result, str)
    assert len(result) > 0
