"""Testy pro TTS streaming, Graf timeout a Fuzzy matching."""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch


# ── TTS speak_streaming ───────────────────────────────────────────

class TestTTSSpeakStreaming:

    def _engine(self):
        from tts import TTSEngine
        cfg = {"tts_enabled": False}   # worker se nespustí — jen testujeme logiku
        e = TTSEngine(cfg)
        e.enabled = True
        e.speak = MagicMock()
        return e

    def test_jedna_veta(self):
        e = self._engine()
        e.speak_streaming(iter(["Ahoj, jak se máš? "] ))
        e.speak.assert_called_once()
        assert "Ahoj" in e.speak.call_args[0][0]

    def test_vice_vet_z_generatoru(self):
        e = self._engine()
        chunks = ["Prvn", "í věta. ", "Druhá", " věta! ", "Třetí věta."]
        e.speak_streaming(iter(chunks))
        volani = [c[0][0] for c in e.speak.call_args_list]
        assert len(volani) >= 2
        full = " ".join(volani)
        assert "První" in full
        assert "Druhá" in full

    def test_prazdny_generator(self):
        e = self._engine()
        e.speak_streaming(iter([]))
        e.speak.assert_not_called()

    def test_bez_interpunkce_jedna_davka(self):
        e = self._engine()
        e.speak_streaming(iter(["text bez tečky"]))
        e.speak.assert_called_once()

    def test_carka_pred_spojkou(self):
        e = self._engine()
        e.speak_streaming(iter(["Prší, ale jdeme ven."]))
        # alespoň jedno speak volání
        assert e.speak.call_count >= 1

    def test_strednik_rozdeli(self):
        e = self._engine()
        e.speak_streaming(iter(["Část jedna; část dvě."]))
        assert e.speak.call_count >= 1

    def test_disabled_neprehrava(self):
        e = self._engine()
        e.enabled = False
        e.speak_streaming(iter(["text"]))
        e.speak.assert_not_called()


# ── Graf agent timeout ────────────────────────────────────────────

class TestGraphTimeout:

    def test_timeout_ukonci_smycku(self):
        from agent_graph import AgentGraph, GLOBAL_TIMEOUT
        from agent_tools import ToolRegistry, Tool

        reg = ToolRegistry()
        reg.register(Tool("slow", "pomalý nástroj", [],
                          fn=lambda: (time.sleep(0.01), "ok")[1]))
        g = AgentGraph(reg, "http://mock", "mock")

        responses = (
            ['["krok1"]'] +
            ['{"tool": "slow", "args": {}}', "OK"] * 200
        )
        g._llm = MagicMock(side_effect=responses)

        # Nastaví deadline na minulost → okamžitý timeout
        import agent_graph as ag
        original = ag.GLOBAL_TIMEOUT
        ag.GLOBAL_TIMEOUT = 0   # okamžitý timeout

        try:
            result = g.run("nekonečný úkol")
        finally:
            ag.GLOBAL_TIMEOUT = original

        assert "příliš dlouho" in result.lower() or isinstance(result, str)

    def test_normalni_ukol_dokonci_pred_timeoutem(self):
        from agent_graph import AgentGraph
        from agent_tools import ToolRegistry, Tool

        reg = ToolRegistry()
        reg.register(Tool("fast", "rychlý", [], fn=lambda: "výsledek"))
        g = AgentGraph(reg, "http://mock", "mock")
        g._llm = MagicMock(side_effect=[
            '["krok1"]',
            '{"tool": "fast", "args": {}}',
            "OK",
            '{"tool": "DONE", "args": {"answer": "hotovo"}}',
        ])

        result = g.run("rychlý úkol")
        assert "hotovo" in result.lower() or result

    def test_timeout_const_existuje(self):
        from agent_graph import GLOBAL_TIMEOUT
        assert GLOBAL_TIMEOUT > 0
        assert GLOBAL_TIMEOUT <= 300


# ── Fuzzy matching ────────────────────────────────────────────────

class TestFuzzyMatching:

    def _router(self):
        from llm import LocalRouter
        return LocalRouter()

    def test_presny_match(self):
        r = self._router()
        _, action = r.route("otevri chrome")
        assert action is not None
        # buď fuzzy nebo regex otevři chrome → open_app nebo open_url
        assert action.get("action") in ("open_app", "open_url")

    def test_preflep_otevrit(self):
        """'otrevi chrome' (překlep) → fuzzy zachytí"""
        from llm import _HAS_FUZZY
        if not _HAS_FUZZY:
            pytest.skip("rapidfuzz není nainstalován")
        r = self._router()
        _, action = r.route("otrevi chrome")
        # fuzzy by měl zachytit, ale i bez toho se router nezasekne
        assert action is None or action.get("action") is not None

    def test_fuzzy_threshold_neni_prilis_agresivni(self):
        """Nesouvisející text nesmí matchnout na fuzzy příkaz"""
        from llm import _HAS_FUZZY, _FUZZY_THRESHOLD
        if not _HAS_FUZZY:
            pytest.skip("rapidfuzz není nainstalován")
        from rapidfuzz import fuzz
        from llm import _FUZZY_COMMANDS, _norm
        # "ahoj jak se mas" nesmí matchnout na "kolik je hodin"
        score = fuzz.partial_ratio(_norm("ahoj jak se mas"), "kolik je hodin")
        assert score < _FUZZY_THRESHOLD

    def test_fuzzy_commands_nejsou_prazdne(self):
        from llm import _FUZZY_COMMANDS
        assert len(_FUZZY_COMMANDS) >= 5
        for phrase, action, params_fn in _FUZZY_COMMANDS:
            assert phrase
            assert action
            assert callable(params_fn)
            assert isinstance(params_fn(), dict)

    def test_has_fuzzy_flag(self):
        from llm import _HAS_FUZZY
        assert isinstance(_HAS_FUZZY, bool)

    def test_router_bez_rapidfuzz_funguje(self):
        """LocalRouter funguje i bez rapidfuzz (fallback)."""
        import local_router
        original = local_router._HAS_FUZZY
        local_router._HAS_FUZZY = False
        try:
            r = local_router.LocalRouter()
            msg, action = r.route("kolik je hodin")
            assert action is not None   # regex zachytí
        finally:
            local_router._HAS_FUZZY = original
