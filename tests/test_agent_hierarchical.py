"""Tests for agent_hierarchical.py — Hierarchical Supervisor Agent System."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"message": {"content": content}}
    return mock

# ── Detekce by should_handle ──────────────────────────────────────

def test_should_handle_keywords():
    from agent_hierarchical import should_handle
    assert should_handle("deleguj úkoly na agenty") is True
    assert should_handle("spusť hierarchický dohled") is True
    assert should_handle("rozdel ukoly pro asistenta") is True
    assert should_handle("normální dotaz na počasí") is False

# ── Rozklad úkolu (Decomposition) ───────────────────────────────

def test_decomposition_returns_list():
    from agent_hierarchical import HierarchicalAgent
    from agent_tools import ToolRegistry
    
    reg = ToolRegistry()
    agent = HierarchicalAgent(reg, OLLAMA_URL, MODEL)
    
    mock_json = json.dumps([
        {"sub_agent": "Researcher", "task": "Najdi cenu GPU"},
        {"sub_agent": "MemorySpecialist", "task": "Ulož cenu GPU"}
    ])
    
    with patch("requests.post", return_value=_mock_response(mock_json)):
        result = agent._decompose_task("Najdi cenu RTX 4080 a ulož ji")
        
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["sub_agent"] == "Researcher"
    assert result[1]["sub_agent"] == "MemorySpecialist"

def test_decomposition_fallback_on_invalid_json():
    from agent_hierarchical import HierarchicalAgent
    from agent_tools import ToolRegistry
    
    reg = ToolRegistry()
    agent = HierarchicalAgent(reg, OLLAMA_URL, MODEL)
    
    with patch("requests.post", return_value=_mock_response("Neplatný ne-JSON výstup")):
        result = agent._decompose_task("Udělej cokoliv")
        
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["sub_agent"] == "GenericAgent"

# ── Spuštění hierarchické smyčky (Run & Synthesize) ──────────────

def test_hierarchical_run_success():
    from agent_hierarchical import HierarchicalAgent
    from agent_tools import ToolRegistry, Tool
    
    # Sestavíme registry s mock nástrojem
    reg = ToolRegistry()
    reg.register(Tool("web_search", "Hledání", [], fn=lambda query="": "RTX 4080 stojí 30 000 Kč"))
    
    agent = HierarchicalAgent(reg, OLLAMA_URL, MODEL)
    
    # Mock odpovědi v pořadí:
    # 1. _decompose_task -> JSON
    # 2. sub_agent _generate_plan call -> JSON
    # 3. sub_agent web_search call -> Thought/Action/Answer
    # 4. synthesis -> Finální shrnutí
    mock_decomp = json.dumps([{"sub_agent": "Researcher", "task": "Zjisti cenu RTX 4080"}])
    mock_sub_plan = json.dumps(["Zjisti cenu"])
    mock_sub_run = "Thought: musím hledat\nAction: web_search(query=\"RTX 4080\")\nObservation: RTX 4080 stojí 30 000 Kč\nThought: hotovo\nAnswer: Cena RTX 4080 je 30 000 Kč."
    mock_synth = "Cena grafické karty RTX 4080 byla zjištěna sub-agentem a činí 30 000 Kč."
    
    responses = [
        _mock_response(mock_decomp),
        _mock_response(mock_sub_plan),
        _mock_response(mock_sub_run),
        _mock_response(mock_synth)
    ]
    
    with patch("requests.post", side_effect=responses):
        result = agent.run("deleguj vyhledání ceny RTX 4080")
        
    assert "30 000" in result
    assert "RTX 4080" in result
