"""Unit testy pro grafového agenta — mock LLM, bez Ollamy."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch
from agent_graph import (
    AgentGraph, AgentState, NodeStatus,
    should_handle, _norm,
)


# ── Helpers ───────────────────────────────────────────────────────

def _registry(tools: dict = None):
    from agent_tools import ToolRegistry, Tool, ToolParam
    reg = ToolRegistry()
    for name, fn in (tools or {}).items():
        reg.register(Tool(name, f"Mock {name}",
                          [ToolParam("query", "q", required=False)], fn=fn))
    return reg


def _graph(llm_responses: list, tools: dict = None) -> AgentGraph:
    reg = _registry(tools)
    g   = AgentGraph(reg, ollama_url="http://mock/api/chat", model="mock")
    g._llm = MagicMock(side_effect=llm_responses)
    return g


# ── should_handle ─────────────────────────────────────────────────

class TestShouldHandle:

    def test_jednoduchy_prikaz_false(self):
        assert should_handle("kolik je hodin") is False
        assert should_handle("otevri chrome")  is False
        assert should_handle("zahraj muziku")  is False

    def test_slozity_ukol_true(self):
        assert should_handle("najdi cenu GPU a uloz do poznamky")    is True
        assert should_handle("zjisti pocasi a zapis ho")              is True
        assert should_handle("porovnej ceny modelů RTX 4080 vs 4090") is True
        assert should_handle("udělej report a pak ho otevři")         is True
        assert should_handle("sestav seznam nákupu")                  is True
        assert should_handle("analyzuj výsledky")                     is True


# ── JSON parsery ──────────────────────────────────────────────────

class TestParsers:

    def test_parse_json_list_ok(self):
        raw = '["krok 1", "krok 2", "krok 3"]'
        result = AgentGraph._parse_json_list(raw)
        assert result == ["krok 1", "krok 2", "krok 3"]

    def test_parse_json_list_s_textem_kolem(self):
        raw = 'Tady je plán:\n["a", "b"]\nhotovo'
        assert AgentGraph._parse_json_list(raw) == ["a", "b"]

    def test_parse_json_list_neplatny(self):
        assert AgentGraph._parse_json_list("nesmysl") == []

    def test_parse_json_obj_ok(self):
        raw = '{"tool": "web_search", "args": {"query": "test"}}'
        result = AgentGraph._parse_json_obj(raw)
        assert result["tool"] == "web_search"
        assert result["args"]["query"] == "test"

    def test_parse_json_obj_done(self):
        raw = '{"tool": "DONE", "args": {"answer": "hotovo"}}'
        result = AgentGraph._parse_json_obj(raw)
        assert result["tool"] == "DONE"

    def test_parse_json_obj_neplatny(self):
        assert AgentGraph._parse_json_obj("nesmysl") is None


# ── Planner uzel ─────────────────────────────────────────────────

class TestPlannerNode:

    def test_planner_vytvori_plan(self):
        g     = _graph(['["vyhledej cenu", "ulož výsledek"]'])
        state = AgentState(task="najdi cenu a ulož")
        g._node_planner(state)
        assert state.plan == ["vyhledej cenu", "ulož výsledek"]
        assert state.status == NodeStatus.ROUTING
        assert state.step_idx == 0

    def test_planner_fallback_pri_chybe(self):
        g     = _graph(["nesmysl"])
        state = AgentState(task="udělej X")
        g._node_planner(state)
        assert len(state.plan) == 1
        assert state.plan[0] == "udělej X"

    def test_planner_notifikuje(self):
        kroky = []
        g     = _graph(['["krok1"]'])
        state = AgentState(task="úkol", on_step=lambda s: kroky.append(s))
        g._node_planner(state)
        assert any("krok" in k.lower() or "plán" in k.lower() or "plan" in k.lower()
                   for k in kroky)


# ── Router uzel ──────────────────────────────────────────────────

class TestRouterNode:

    def test_router_vybere_nastroj(self):
        g     = _graph(['{"tool": "web_search", "args": {"query": "test"}}'],
                       {"web_search": lambda query="": "ok"})
        state = AgentState(task="hledej", plan=["vyhledej X"], step_idx=0)
        g._node_router(state)
        assert state.last_tool == "web_search"
        assert state.status    == NodeStatus.EXECUTING

    def test_router_done_kdyz_hotovo(self):
        # step_idx >= len(plan) → router volá _synthesize a nastaví DONE
        g     = _graph(["Vše bylo hotovo."])   # LLM pro _synthesize
        state = AgentState(task="úkol", plan=["krok"], step_idx=1,
                           observations=["výsledek kroku"])
        g._node_router(state)
        assert state.status == NodeStatus.DONE
        assert state.final_answer  # neprázdné

    def test_router_preskoci_nesmysl(self):
        g     = _graph(["nesmysl"])
        state = AgentState(task="úkol", plan=["krok"], step_idx=0)
        g._node_router(state)
        assert state.step_idx == 1   # přeskočeno

    def test_router_done_kdyz_vsechny_kroky(self):
        g     = _graph(['Shrnutí: vše hotovo.'])
        g._synthesize = lambda s: "Vše hotovo."
        state = AgentState(task="úkol", plan=["krok"], step_idx=1)
        g._node_router(state)
        assert state.status == NodeStatus.DONE


# ── Executor uzel ────────────────────────────────────────────────

class TestExecutorNode:

    def test_executor_vola_nastroj(self):
        volano = []
        g     = _graph([])
        g.registry = _registry({"web_search": lambda query="": (volano.append(query), "výsledek")[1]})
        state = AgentState(task="t", plan=["hledej"], step_idx=0)
        state.last_tool = "web_search"
        state.last_args = {"query": "RTX cena"}
        g._node_executor(state)
        assert "RTX cena" in volano
        assert state.last_result  == "výsledek"
        assert state.exec_count   == 1
        assert state.status       == NodeStatus.CRITICIZING

    def test_executor_neznamy_nastroj(self):
        g     = _graph([])
        state = AgentState(task="t", plan=["x"], step_idx=0)
        state.last_tool = "neexistuje"
        state.last_args = {}
        g._node_executor(state)
        assert "neexistuje" in state.last_result
        assert state.status == NodeStatus.CRITICIZING

    def test_executor_zkrati_velky_vystup(self):
        g     = _graph([])
        g.registry = _registry({"big": lambda: "x" * 5000})
        state = AgentState(task="t", plan=["x"], step_idx=0)
        state.last_tool = "big"
        state.last_args = {}
        g._node_executor(state)
        assert len(state.last_result) <= 1000


# ── Critic uzel ──────────────────────────────────────────────────

class TestCriticNode:

    def test_critic_ok_pokracuje(self):
        g     = _graph(["OK"])
        state = AgentState(task="t", plan=["krok1", "krok2"], step_idx=0)
        state.last_result = "výsledek"
        g._node_critic(state)
        assert state.step_idx == 1
        assert state.observations == ["výsledek"]
        assert state.status == NodeStatus.ROUTING

    def test_critic_retry(self):
        from agent_graph import MAX_RETRIES
        g     = _graph(["RETRY"])
        state = AgentState(task="t", plan=["krok"], step_idx=0)
        state.last_result = "chyba"
        g._node_critic(state)
        assert state.retry_count == 1
        assert state.status == NodeStatus.EXECUTING

    def test_critic_retry_limit(self):
        from agent_graph import MAX_RETRIES
        g     = _graph(["RETRY"])
        state = AgentState(task="t", plan=["krok"], step_idx=0)
        state.last_result = "chyba"
        state.retry_count = MAX_RETRIES   # vyčerpáno
        g._node_critic(state)
        assert state.step_idx == 1       # přeskočí na další krok
        assert state.status   == NodeStatus.ROUTING

    def test_critic_replan(self):
        g     = _graph(["REPLAN"])
        state = AgentState(task="t", plan=["krok"], step_idx=0)
        state.last_result = "nefunguje"
        g._node_critic(state)
        assert state.status       == NodeStatus.PLANNING
        assert state.replan_count == 1

    def test_critic_replan_limit(self):
        from agent_graph import MAX_REPLANS
        g     = _graph(["REPLAN"])
        state = AgentState(task="t", plan=["krok"], step_idx=0)
        state.last_result  = "nefunguje"
        state.replan_count = MAX_REPLANS
        g._node_critic(state)
        # Vyčerpán replan → OK path
        assert state.step_idx == 1
        assert state.status   == NodeStatus.ROUTING


# ── Celý run ─────────────────────────────────────────────────────

class TestFullRun:

    def test_jednoduchy_dvou_krokovy_ukol(self):
        volano = []
        g = _graph(
            llm_responses=[
                '["vyhledej cenu", "uloz poznamku"]',         # Planner
                '{"tool": "web_search", "args": {"query": "RTX"}}',  # Router krok 1
                "OK",                                          # Critic krok 1
                '{"tool": "note_add", "args": {"note": "RTX 35k"}}', # Router krok 2
                "OK",                                          # Critic krok 2
                '{"tool": "DONE", "args": {"answer": "Uloženo!"}}',  # Router → DONE
            ],
            tools={
                "web_search": lambda query="": (volano.append("search"), "35 000 Kč")[1],
                "note_add":   lambda note="":  (volano.append("note"),   "Uloženo.")[1],
            },
        )
        result = g.run("najdi cenu RTX a uloz")
        assert "Uloženo" in result or result
        assert "search" in volano
        assert "note"   in volano

    def test_limit_kroku_nezmrazi(self):
        from agent_graph import MAX_STEPS
        # Router stále volá nástroje, nikdy DONE
        responses = (
            ['["krok"]'] +
            ['{"tool": "web_search", "args": {"query": "x"}}', "OK"] * (MAX_STEPS + 2)
        )
        g = _graph(responses, {"web_search": lambda query="": "ok"})
        result = g.run("nekonečný úkol")
        assert isinstance(result, str)

    def test_on_step_callback(self):
        kroky = []
        g = _graph(
            ['["hledej"]',
             '{"tool": "web_search", "args": {"query": "test"}}',
             "OK",
             '{"tool": "DONE", "args": {"answer": "hotovo"}}'],
            {"web_search": lambda query="": "výsledek"},
        )
        g.run("hledej test", on_step=lambda s: kroky.append(s))
        assert len(kroky) >= 1

    def test_llm_chyba_nepadne(self):
        g = _graph(["", "", "", ""])
        result = g.run("úkol")
        assert isinstance(result, str)
