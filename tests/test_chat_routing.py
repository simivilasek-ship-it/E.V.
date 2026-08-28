"""Chat routing: local commands still win; casual talk is not one canned line."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app_core import EVApp, _HeadlessGUI
from commands import CommandExecutor
from event_bus import get_event_bus
from local_router import LocalRouter
from routing import CommandRouter
from security_v2 import get_security_manager
from src.personality import EVPersonality

pytestmark = [pytest.mark.unit]


def test_casual_dnes_is_not_the_date():
    _, action = LocalRouter().route("jak se dnes cítíš")
    assert action is None or action.get("action") != "get_date"


def test_explicit_date_still_works():
    _, action = LocalRouter().route("jaké je datum")
    assert action is not None
    assert action["action"] == "get_date"


def test_jaky_je_smysl_is_not_the_time():
    _, action = LocalRouter().route("jaký je smysl života")
    assert action is None or action.get("action") != "get_time"


def _runtime():
    app_obj = EVApp.__new__(EVApp)
    app_obj.gui = _HeadlessGUI()
    app_obj.cmds = CommandExecutor({})
    app_obj.security = get_security_manager()
    app_obj.bus = get_event_bus()
    app_obj.plugin_manager = None
    app_obj.error_handler = MagicMock()
    app_obj.hierarchical_agent = None
    app_obj.graph_agent = None
    app_obj.react_agent = None

    router = LocalRouter()
    llm = MagicMock()
    llm.quick_match = router.route
    llm._default_message = lambda action, params: ""
    llm.save_history = MagicMock()
    llm.config = {}
    llm.url = "http://localhost:11434/api/chat"
    llm._cloud = MagicMock(enabled=False)
    llm._cloud.should_use_cloud.return_value = False
    llm._ollama_available = False
    llm._no_llm_reply = lambda text: EVPersonality().no_llm_reply(text, "Simi")

    def _stream(text):
        yield EVPersonality().no_llm_reply(text, "Simi")

    llm.stream_ask = _stream
    app_obj.llm = llm
    app_obj._router = CommandRouter(app_obj)
    app_obj._execute_result = EVApp._execute_result.__get__(app_obj, EVApp)
    app_obj._gui = lambda fn: fn()
    app_obj._ollama_reachable = lambda: False
    return app_obj


def test_time_command_still_local():
    app = _runtime()
    out = app._router.process_for_web("kolik je hodin")
    assert "Ollama není dostupná" not in out
    assert "Je " in out or any(ch.isdigit() for ch in out)


def test_casual_chat_mentions_user_words():
    app = _runtime()
    out = app._router.process_for_web("ahoj jak se máš")
    assert "ahoj jak se máš" in out
    assert "Ollama není dostupná. Lokální příkazy fungují" not in out
    other = app._router.process_for_web("proč je obloha modrá")
    assert "obloha" in other
    assert out != other
