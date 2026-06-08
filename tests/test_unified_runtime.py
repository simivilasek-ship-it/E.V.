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
        assert action["params"]["city"] == "Praha"

    def test_stahni_instagram_is_install_not_video(self, router):
        msg, action = router.route("stahni instagram")
        assert action is not None
        assert action["action"] == "install_app"
        assert action["params"]["name"] == "instagram"
        assert action["params"].get("launch") is True
        assert "spouštím" in msg.lower() or "instaluji" in msg.lower()

    def test_aplikaci_instagram_stahni_is_install(self, router):
        _msg, action = router.route("aplikaci instagram stahni")
        assert action is not None
        assert action["action"] == "install_app"
        assert action["params"]["name"] == "instagram"

    def test_stahni_video_youtube_is_download(self, router):
        _msg, action = router.route("stahni video minecraft tutorial")
        assert action is not None
        assert action["action"] == "youtube_download"


class TestAppInstallSpec:
    """Instagram a další aplikace — snap spec, ne apt."""

    def test_resolve_instagram_snap(self):
        from commands.apps import resolve_app

        spec = resolve_app("instagram")
        assert spec is not None
        assert spec.snap == "instagram-electron"
        assert spec.launch == ["snap", "run", "instagram-electron"]

    def test_install_instagram_uses_snap_not_apt(self):
        from commands.apps import cmd_install_app

        with patch("commands.apps.is_app_installed", return_value=False), \
             patch("commands.apps.threading.Thread") as mock_thread:
            msg = cmd_install_app("instagram", launch=True)
            assert "instagram" in msg.lower()
            assert "snap" in msg.lower()
            mock_thread.assert_called_once()


class TestInstallEventEmission:
    """_install_spec_worker emits progress/error events via EventBus."""

    def test_emits_starting_method_and_success(self):
        from commands.apps import APP_SPECS, _install_spec_worker
        from event_bus import EventType

        mock_bus = MagicMock()
        spec = APP_SPECS["instagram"]

        with patch("commands.apps.get_event_bus", return_value=mock_bus), \
             patch("commands.apps._IS_LINUX", True), \
             patch("commands.apps.shutil.which", return_value="/usr/bin/snap"), \
             patch("commands.apps._snap_installed", return_value=False), \
             patch("commands.apps.safe_run", return_value={"rc": 0, "stdout": "", "stderr": ""}), \
             patch("commands.apps.is_app_installed", return_value=True), \
             patch("commands.apps.launch_app_spec", return_value="ok"):
            _install_spec_worker(spec, launch_after=True)

        emitted = [(c.args[0], c.args[1]) for c in mock_bus.emit.call_args_list]
        types = [t for t, _ in emitted]
        assert EventType.INSTALL_PROGRESS in types
        stages = [d.get("stage") for _, d in emitted]
        assert "starting" in stages
        assert "method" in stages
        assert "success" in stages
        success = next(d for t, d in emitted if d.get("stage") == "success")
        assert success.get("method") == "snap"
        assert success.get("launched") is True

    def test_emits_error_on_install_failure(self):
        from commands.apps import APP_SPECS, _install_spec_worker
        from event_bus import EventType

        mock_bus = MagicMock()
        spec = APP_SPECS["instagram"]

        with patch("commands.apps.get_event_bus", return_value=mock_bus), \
             patch("commands.apps._IS_LINUX", True), \
             patch("commands.apps.shutil.which", return_value="/usr/bin/snap"), \
             patch("commands.apps._snap_installed", return_value=False), \
             patch("commands.apps._flatpak_installed", return_value=False), \
             patch("commands.apps._apt_installed", return_value=False), \
             patch("commands.apps.safe_run", return_value={"rc": 1, "stdout": "", "stderr": "snap failed"}):
            _install_spec_worker(spec, launch_after=False)

        emitted = [(c.args[0], c.args[1]) for c in mock_bus.emit.call_args_list]
        types = [t for t, _ in emitted]
        assert EventType.INSTALL_ERROR in types
        err = next(d for t, d in emitted if t == EventType.INSTALL_ERROR)
        assert err.get("app") == "instagram"
        assert err.get("errors")


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
