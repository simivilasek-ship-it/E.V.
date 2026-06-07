"""
Integration tests — unified runtime: LocalRouter, routing, PC overview, user memory.

No live server or Ollama required for router / classify tests.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.integration]


@pytest.fixture
def router():
    from local_router import LocalRouter
    return LocalRouter()


class TestLocalRouterRoutes:
    """LocalRouter routes common Czech commands without LLM."""

    def test_route_kolik_je_hodin(self, router):
        _msg, action = router.route("kolik je hodin")
        assert action is not None
        assert action["action"] == "get_time"
        assert action["params"] == {}

    def test_route_prehled_o_pc(self, router):
        _msg, action = router.route("prehled o pc")
        assert action is not None
        assert action["action"] == "pc_overview"
        assert action["params"] == {}

    def test_route_pocasi_v_praze(self, router):
        _msg, action = router.route("jake je pocasi v praze")
        assert action is not None
        assert action["action"] == "weather"
        assert action["params"]["city"] == "praze"


class TestPcOverview:
    """cmd_pc_overview returns real system info."""

    def test_returns_hostname(self):
        from commands.system import cmd_pc_overview

        result = cmd_pc_overview()
        hostname = socket.gethostname()
        assert hostname in result
        assert "🖥️" in result or hostname in result


class TestClassifyMode:
    """routing._classify_mode labels UI mode without live server."""

    def test_action_for_local_command(self):
        from routing import _classify_mode

        assert _classify_mode("kolik je hodin") == "action"

    def test_action_for_pc_overview(self):
        from routing import _classify_mode

        assert _classify_mode("prehled o pc") == "action"

    def test_copilot_for_generic_chat(self):
        from routing import _classify_mode

        assert _classify_mode("ahoj jak se mas") == "copilot"

    def test_agent_for_hierarchical_keyword(self):
        from routing import _classify_mode

        assert _classify_mode("deleguj ukoly") == "agent"


class TestUserMemoryExtraction:
    """LLMEngine._extract_user_facts stores city, preferences, favorite apps."""

    @pytest.fixture
    def llm_with_memory(self, mock_config, tmp_path, monkeypatch):
        profile_path = tmp_path / "profile.json"
        mem_dir = tmp_path / "memory_data"
        mem_dir.mkdir()

        monkeypatch.setattr("user_profile._PROFILE_PATH", profile_path)
        monkeypatch.setattr("user_profile._profile", None)

        with patch("memory.Path") as mock_path_cls:
            mock_path_cls.return_value = mem_dir
            from memory import JarvisMemory
            from llm import LLMEngine

            memory = JarvisMemory(mock_config)
            engine = LLMEngine(mock_config, memory=memory)
            engine.inject_profile = MagicMock()
            yield engine

        monkeypatch.setattr("user_profile._profile", None)

    def test_extracts_city_from_weather_query(self, llm_with_memory):
        llm_with_memory._extract_user_facts("jake je pocasi v praze")

        from user_profile import get_user_profile

        assert get_user_profile().get("město") == "Praze"
        llm_with_memory.inject_profile.assert_called()

    def test_extracts_preferuji_preference(self, llm_with_memory):
        llm_with_memory._extract_user_facts("preferuji tmavy rezim")

        from user_profile import get_user_profile

        prefs = get_user_profile().get("preference")
        assert isinstance(prefs, list)
        assert "tmavy rezim" in prefs

    def test_tracks_favorite_app_from_open_command(self, llm_with_memory):
        llm_with_memory._extract_user_facts("otevri chrome")

        from user_profile import get_user_profile

        favs = get_user_profile().get("oblíbené_aplikace")
        assert isinstance(favs, list)
        assert "chrome" in favs
