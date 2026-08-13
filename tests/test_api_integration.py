"""Integration tests for E.V. FastAPI — TestClient with mocked runtime where needed."""
from __future__ import annotations

import json
import socket
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

try:
    from dashboard import app

    HAS_APP = True
except Exception:
    HAS_APP = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not HAS_APP, reason="dashboard app nelze importovat"),
]


@pytest.fixture
def client():
    """TestClient without heavy JarvisApp startup."""
    with patch("src.api.runtime.init_runtime"), patch("src.api.runtime.shutdown_runtime"):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def mock_process_chat():
    with patch("src.api.runtime.process_chat", return_value="mocked integration response") as m:
        yield m


class TestContextEndpoint:
    def test_context_returns_hostname_and_cpu(self, client):
        mock_orch = MagicMock()
        mock_orch.get_context_data.return_value = {
            "active": "Terminal",
            "windows": ["Terminal", "Browser"],
            "clipboard": "",
            "system": {
                "hostname": "jarvis-test",
                "cpu": 12.5,
                "ram": 45.0,
                "disk": 60.0,
            },
            "time": "10:00, Monday 01.01.2026",
        }
        mock_orch.get_context.return_value = "Aktuální čas: 10:00"

        with patch("context_orchestrator.get_context_orchestrator", return_value=mock_orch):
            r = client.get("/api/context")

        assert r.status_code == 200
        d = r.json()
        assert "system" in d
        assert d["system"]["hostname"] == "jarvis-test"
        assert "cpu" in d["system"]

    def test_context_real_system_keys(self, client):
        """Fallback: real context orchestrator exposes hostname/cpu when available."""
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


class TestChatEndpoint:
    def test_chat_returns_response_field(self, client, mock_process_chat):
        r = client.post("/api/chat", json={"text": "ahoj jarvis"})
        assert r.status_code == 200
        d = r.json()
        assert d["response"] == "mocked integration response"
        mock_process_chat.assert_called_once()
        assert mock_process_chat.call_args[0][0] == "ahoj jarvis"

    def test_chat_empty_message(self, client, mock_process_chat):
        r = client.post("/api/chat", json={"text": "   "})
        assert r.status_code == 200
        assert r.json()["response"] == "Prázdná zpráva"
        mock_process_chat.assert_not_called()


class TestCommandEndpoint:
    def test_command_deprecated_still_works(self, client, mock_process_chat):
        """Legacy /api/command routes through unified process_chat."""
        r = client.post("/api/command", json={"command": "něco obecného"})
        assert r.status_code == 200
        d = r.json()
        assert d["response"] == "mocked integration response"
        assert d.get("deprecated") is True
        assert d.get("use") == "/api/chat"
        assert r.headers.get("Deprecation") == "true"
        mock_process_chat.assert_called_once()

    def test_command_empty_returns_error(self, client):
        r = client.post("/api/command", json={"command": ""})
        assert r.status_code == 200
        d = r.json()
        assert "error" in d
        assert d.get("deprecated") is True


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code in (200, 503)

    def test_health_has_status_and_ws(self, client):
        r = client.get("/health")
        d = r.json()
        assert "status" in d
        assert d["ws"] == "running"
        assert "checks" in d


class TestWebSocketChat:
    def test_ws_chat_receives_done(self, client, mock_process_chat):
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"command": "test websocket"}))
            seen_done = False
            for _ in range(20):
                msg = json.loads(ws.receive_text())
                if msg.get("type") == "done":
                    seen_done = True
                    break
            assert seen_done
        mock_process_chat.assert_called_once()


class TestWebSocketAudio:
    def test_ws_audio_receives_ready(self, client):
        with patch("config.CONFIG", {"audio_ws_enabled": True, "tts_voice": "cs-CZ-AntoninNeural"}):
            with client.websocket_connect("/ws/audio") as ws:
                msg = json.loads(ws.receive_text())
                assert msg.get("type") == "ready"


class TestAuthMiddleware:
    def test_dashboard_has_auth_middleware(self):
        from src.api.middleware.auth import ApiTokenAuthMiddleware
        from dashboard import app as dash_app

        middleware_classes = [m.cls for m in dash_app.user_middleware]
        assert ApiTokenAuthMiddleware in middleware_classes
