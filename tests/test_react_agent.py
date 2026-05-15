"""Unit testy pro ReAct agenta — používají mock LLM bez Ollamy."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────

def _make_registry(tools: dict = None):
    """Vytvoří ToolRegistry s mock nástroji."""
    from agent_tools import ToolRegistry, Tool, ToolParam
    reg = ToolRegistry()
    for name, fn in (tools or {}).items():
        reg.register(Tool(
            name=name,
            description=f"Mock {name}",
            params=[ToolParam("query", "vstup", required=False)],
            fn=fn,
        ))
    return reg


def _make_agent(responses: list, tools: dict = None):
    """Vytvoří ReactAgent s mock LLM odpověďmi (fronta)."""
    from agent_react import ReactAgent
    reg    = _make_registry(tools)
    agent  = ReactAgent(reg,
                        ollama_url="http://mock/api/chat",
                        model="mock")
    agent._llm = MagicMock(side_effect=responses)
    return agent


# ── should_handle detekce ─────────────────────────────────────────

class TestShouldHandle:

    def test_jednoduchy_prikaz_false(self):
        from agent_react import should_handle
        assert should_handle("kolik je hodin") is False
        assert should_handle("otevři chrome") is False
        assert should_handle("zahraj spotify") is False

    def test_vicesvůlový_true(self):
        from agent_react import should_handle
        assert should_handle("najdi cenu RTX 4080 a ulož ji do poznámky") is True
        assert should_handle("zjisti počasí a zapis ho") is True
        assert should_handle("porovnej ceny GPU modelů") is True
        assert should_handle("zkontroluj web a pak otevři stránku") is True


# ── Parsování Action řádku ────────────────────────────────────────

class TestParseAction:

    def test_jednoduchy_parametr(self):
        from agent_react import _parse_action
        result = _parse_action('Action: web_search(query="RTX 4090")')
        assert result is not None
        name, kwargs = result
        assert name == "web_search"
        assert kwargs["query"] == "RTX 4090"

    def test_vice_parametru(self):
        from agent_react import _parse_action
        result = _parse_action('Action: note_add(note="test", importance=0.8)')
        assert result is not None
        _, kwargs = result
        assert kwargs["note"] == "test"
        assert kwargs["importance"] == pytest.approx(0.8)

    def test_neplatny_radek(self):
        from agent_react import _parse_action
        assert _parse_action("Thought: přemýšlím") is None
        assert _parse_action("Answer: hotovo") is None

    def test_bez_parametru(self):
        from agent_react import _parse_action
        result = _parse_action("Action: get_time()")
        assert result is not None
        name, kwargs = result
        assert name == "get_time"
        assert kwargs == {}


# ── ReAct smyčka ─────────────────────────────────────────────────

class TestReactLoop:

    def test_primy_answer(self):
        """LLM rovnou vrátí Answer: bez akce."""
        agent = _make_agent([
            "Thought: vím odpověď\nAnswer: Je 14:30."
        ])
        result = agent.run("kolik je hodin")
        assert "14:30" in result

    def test_jeden_krok(self):
        """Thought → Action → Observation → Answer."""
        volano = []

        def fake_search(query=""):
            volano.append(query)
            return "RTX 4090 stojí 35 000 Kč"

        agent = _make_agent(
            responses=[
                'Thought: musím vyhledat\nAction: web_search(query="RTX 4090 cena")',
                'Thought: mám výsledek\nAnswer: RTX 4090 stojí 35 000 Kč.',
            ],
            tools={"web_search": fake_search},
        )
        result = agent.run("kolik stojí RTX 4090")
        assert "35 000" in result
        assert volano == ["RTX 4090 cena"]

    def test_dva_kroky(self):
        """Vyhledání → uložení poznámky → Answer."""
        ulozeno = []

        agent = _make_agent(
            responses=[
                'Thought: hledám\nAction: web_search(query="Python cena kurzu")',
                'Thought: ukládám\nAction: note_add(note="Python kurz stojí 5000 Kč")',
                'Thought: hotovo\nAnswer: Cena kurzu uložena do poznámek.',
            ],
            tools={
                "web_search": lambda query="": "Python kurz stojí 5000 Kč",
                "note_add":   lambda note="": (ulozeno.append(note), "Uloženo.")[1],
            },
        )
        result = agent.run("najdi cenu Python kurzu a ulož do poznámky")
        assert "uložena" in result.lower() or "poznámek" in result.lower()
        assert len(ulozeno) == 1
        assert "5000" in ulozeno[0]

    def test_neznamy_nastroj(self):
        """Pokud LLM zavolá neexistující nástroj, agent dostane chybovou Observation."""
        agent = _make_agent(
            responses=[
                'Thought: zkusím\nAction: neexistujici_tool(query="test")',
                'Thought: nástroj neexistuje\nAnswer: Nemohu splnit úkol.',
            ],
            tools={},
        )
        result = agent.run("udělej něco neznámého")
        assert result  # cokoliv — nesmí spadnout

    def test_limit_kroku(self):
        """Pokud LLM nikdy nevrátí Answer:, agent skončí po MAX_STEPS."""
        from agent_react import MAX_STEPS
        responses = [
            f'Thought: krok {i}\nAction: web_search(query="x")'
            for i in range(MAX_STEPS + 2)
        ]
        agent = _make_agent(
            responses=responses,
            tools={"web_search": lambda query="": "výsledek"},
        )
        result = agent.run("nekonečný úkol")
        assert result  # nesmí loop forever

    def test_on_step_callback(self):
        """on_step callback se volá po každé Observation."""
        kroky = []

        agent = _make_agent(
            responses=[
                'Thought: hledám\nAction: web_search(query="test")',
                'Thought: hotovo\nAnswer: Nalezeno.',
            ],
            tools={"web_search": lambda query="": "výsledek"},
        )
        agent.run("hledej test", on_step=lambda s: kroky.append(s))
        assert len(kroky) == 1
        assert "web_search" in kroky[0]

    def test_llm_chyba_vrati_string(self):
        """Při selhání LLM (prázdná odpověď) agent skončí korektně."""
        agent = _make_agent(responses=[""])
        result = agent.run("cokoliv")
        assert isinstance(result, str)


# ── ToolRegistry ──────────────────────────────────────────────────

class TestToolRegistry:

    def test_registrace_a_get(self):
        from agent_tools import ToolRegistry, Tool, ToolParam
        reg = ToolRegistry()
        t = Tool("test", "desc", [], fn=lambda: "ok")
        reg.register(t)
        assert reg.get("test") is t
        assert reg.get("neexistuje") is None

    def test_schema_block_obsahuje_nazvy(self):
        reg = _make_registry({"web_search": lambda q="": "ok",
                               "note_add":   lambda note="": "ok"})
        schema = reg.schema_block()
        assert "web_search" in schema
        assert "note_add"   in schema

    def test_tool_call_chyba_vrati_string(self):
        from agent_tools import Tool
        def boom(**_):
            raise ValueError("test chyba")
        t = Tool("boom", "desc", [], fn=boom)
        result = t.call()
        assert "Chyba" in result
        assert "boom" in result

    def test_build_registry_bez_mcp(self):
        """build_registry funguje i bez MCP bridge."""
        from agent_tools import build_registry
        executor = MagicMock()
        executor.execute.return_value = "ok"
        reg = build_registry(executor, mcp_bridge=None)
        assert reg.get("web_search") is not None
        assert reg.get("note_add")   is not None
        assert reg.get("calculate")  is not None
