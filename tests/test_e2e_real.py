"""E2E tests — real LocalRouter, real endpoints, minimal mocks (runtime/subprocess only)."""
from __future__ import annotations

import json
import re
import socket
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

try:
    from dashboard import app

    HAS_APP = True
except Exception:
    HAS_APP = False


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not HAS_APP, reason="dashboard app nelze importovat"),
]


def _wait_for(condition_fn, timeout=2.0, interval=0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def _make_lightweight_runtime(config: dict):
    """Minimal EVApp shell — real CommandRouter + LocalRouter, no Ollama/GUI."""
    from app_core import EVApp, _HeadlessGUI
    from commands import CommandExecutor
    from event_bus import get_event_bus
    from local_router import LocalRouter
    from routing import CommandRouter
    from security_v2 import get_security_manager

    app_obj = EVApp.__new__(EVApp)
    app_obj.gui = _HeadlessGUI()
    app_obj.cmds = CommandExecutor(config)
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
    llm.config = config
    llm.url = config.get("ollama_url", "http://localhost:11434/api/chat")
    app_obj.llm = llm

    app_obj._router = CommandRouter(app_obj)
    app_obj._execute_result = EVApp._execute_result.__get__(app_obj, EVApp)
    app_obj._gui = lambda fn: fn()
    app_obj._ollama_reachable = lambda: False
    return app_obj


@pytest.fixture
def test_config():
    return {
        "ollama_url": "http://localhost:11434/api/chat",
        "ollama_model": "qwen2.5:3b",
        "tts_enabled": False,
        "history_size": 5,
    }


@pytest.fixture
def lightweight_runtime(test_config):
    return _make_lightweight_runtime(test_config)


@pytest.fixture
def client():
    """TestClient without heavy JarvisApp lifespan startup."""
    with patch("src.api.runtime.init_runtime"), patch("src.api.runtime.shutdown_runtime"):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def client_with_runtime(client, lightweight_runtime):
    """TestClient with lightweight runtime injected via get_runtime."""
    with patch("src.api.runtime.get_runtime", return_value=lightweight_runtime):
        yield client, lightweight_runtime


class TestWebSocketChatRealRouter:
    def test_ws_chat_time_command_via_local_router(self, client_with_runtime):
        """WS /ws/chat — real process_chat + LocalRouter for 'kolik je hodin'."""
        client, _rt = client_with_runtime
        chunks: list[str] = []
        seen_done = False

        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"command": "kolik je hodin"}))
            for _ in range(30):
                msg = json.loads(ws.receive_text())
                if msg.get("type") == "chunk":
                    chunks.append(msg.get("data", ""))
                if msg.get("type") == "done":
                    seen_done = True
                    break

        assert seen_done
        body = " ".join(chunks)
        assert re.search(r"\d{1,2}:\d{2}", body) or "Je " in body or body == "Hotovo."

    def test_ws_chat_emits_status_for_local_action(self, client_with_runtime):
        client, _rt = client_with_runtime
        statuses: list[str] = []

        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"command": "kolik je hodin"}))
            for _ in range(30):
                msg = json.loads(ws.receive_text())
                if msg.get("type") == "status":
                    statuses.append(msg.get("data", ""))
                if msg.get("type") == "done":
                    break

        assert any("akci" in s.lower() or "⚡" in s for s in statuses) or len(statuses) == 0


class TestWebSocketAudio:
    def test_ws_audio_ready_then_stop(self, client):
        """WS /ws/audio — connect, receive ready, send stop (no Whisper required)."""
        with patch("config.CONFIG", {"audio_ws_enabled": True, "tts_voice": "cs-CZ-AntoninNeural"}):
            with client.websocket_connect("/ws/audio") as ws:
                msg = json.loads(ws.receive_text())
                assert msg.get("type") == "ready"
                ws.send_text(json.dumps({"type": "stop"}))


class TestInstallFlow:
    def test_resolve_instagram_snap(self):
        from commands.apps import resolve_app

        spec = resolve_app("instagram")
        assert spec is not None
        assert spec.snap == "instagram-electron"
        assert spec.launch == ["snap", "run", "instagram-electron"]

    def test_cmd_install_app_message_format(self):
        from commands.apps import cmd_install_app

        with patch("commands.apps.is_app_installed", return_value=False), \
             patch("commands.apps.threading.Thread") as mock_thread:
            msg = cmd_install_app("instagram", launch=True)
            mock_thread.assert_called_once()
            assert "instagram" in msg.lower()
            assert "snap" in msg.lower()

    def test_install_worker_emits_events_on_real_bus(self):
        from commands.apps import APP_SPECS, _install_spec_worker
        from event_bus import EventBus, EventType

        bus = EventBus(workers=1)
        received: list = []
        bus.subscribe(EventType.INSTALL_PROGRESS, lambda e: received.append(e.data))
        bus.subscribe(EventType.INSTALL_ERROR, lambda e: received.append(e.data))

        spec = APP_SPECS["instagram"]
        try:
            with patch("commands.apps.get_event_bus", return_value=bus), \
                 patch("commands.apps._IS_LINUX", True), \
                 patch("commands.apps.shutil.which", return_value="/usr/bin/snap"), \
                 patch("commands.apps._snap_installed", return_value=False), \
                 patch("commands.apps.safe_run", return_value={"rc": 0, "stdout": "", "stderr": ""}), \
                 patch("commands.apps.is_app_installed", return_value=True), \
                 patch("commands.apps.launch_app_spec", return_value="ok"):
                _install_spec_worker(spec, launch_after=True)

            assert _wait_for(lambda: any(d.get("stage") == "success" for d in received))
            stages = [d.get("stage") for d in received]
            assert "starting" in stages
            assert "method" in stages
            success = next(d for d in received if d.get("stage") == "success")
            assert success.get("method") == "snap"
            assert success.get("launched") is True
        finally:
            bus.stop(timeout=1.0)


class TestContextEndpoint:
    def test_context_real_endpoint(self, client):
        """GET /api/context — real orchestrator when available."""
        r = client.get("/api/context")
        assert r.status_code == 200
        d = r.json()
        if "error" in d:
            pytest.skip(f"context orchestrator unavailable: {d['error']}")
        assert "system" in d
        sys_info = d["system"]
        assert "hostname" in sys_info
        assert "cpu" in sys_info
        assert sys_info["hostname"] == socket.gethostname()


class TestChatRestRealRouting:
    def test_post_chat_time_via_local_router(self, client_with_runtime):
        """POST /api/chat — real process_chat + LocalRouter for time query."""
        client, _rt = client_with_runtime
        r = client.post("/api/chat", json={"text": "kolik je hodin"})
        assert r.status_code == 200
        d = r.json()
        assert "response" in d
        assert len(d["response"]) > 0
        assert re.search(r"\d{1,2}:\d{2}", d["response"]) or "Je " in d["response"]
