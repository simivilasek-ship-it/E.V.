"""
API contract tests — smoke test every registered endpoint.
Verifies routes exist and return expected HTTP status codes.
Uses TestClient from FastAPI.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JARVIS_TEST_MODE", "1")

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def client():
    try:
        from fastapi.testclient import TestClient
        from src.api.app import app

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    except Exception as exc:
        pytest.skip(f"FastAPI app not available: {exc}")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_root(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_health_check(self, client):
        r = client.get("/api/health/check")
        assert r.status_code == 200
        data = r.json()
        assert "score" in data


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class TestContext:
    def test_context(self, client):
        r = client.get("/api/context")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

class TestSystem:
    def test_system_metrics(self, client):
        r = client.get("/api/system")
        assert r.status_code == 200
        data = r.json()
        assert "cpu" in data

    def test_status(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)


# ---------------------------------------------------------------------------
# Settings & Models
# ---------------------------------------------------------------------------

class TestSettings:
    def test_get_settings(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_patch_settings_empty(self, client):
        # PATCH with empty body returns ok=False with an error message — still 200
        r = client.patch("/api/settings", json={})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_list_models(self, client):
        r = client.get("/api/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert isinstance(data["models"], list)


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class TestActivity:
    def test_activity_today(self, client):
        r = client.get("/api/activity/today")
        # Activity DB may or may not be populated in test mode
        assert r.status_code in (200, 404)

    def test_activity_feed(self, client):
        r = client.get("/api/activity/feed")
        assert r.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class TestMemory:
    def test_memory_query(self, client):
        """GET /api/memory returns results + stats dict."""
        r = client.get("/api/memory")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_memory_stats_or_graph(self, client):
        """/api/memory/stats or /api/memory/graph — at least one must be accessible."""
        r_stats = client.get("/api/memory/stats")
        r_graph = client.get("/api/memory/graph")
        assert r_stats.status_code in (200, 404) and r_graph.status_code in (200, 404)
        # At least one must succeed
        assert r_stats.status_code == 200 or r_graph.status_code == 200


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

class TestDocs:
    def test_list_docs(self, client):
        r = client.get("/api/docs")
        assert r.status_code == 200
        data = r.json()
        assert "docs" in data
        assert isinstance(data["docs"], list)


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------

class TestBriefing:
    def test_briefing_today(self, client):
        r = client.get("/api/briefing/today")
        assert r.status_code == 200
        data = r.json()
        assert "briefing" in data


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class TestChat:
    def test_chat_message(self, client):
        r = client.post("/api/chat/message", json={"text": "kolik je hodin"})
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

class TestMissions:
    def test_missions_list(self, client):
        r = client.get("/api/missions")
        assert r.status_code == 200
        data = r.json()
        assert "missions" in data


# ---------------------------------------------------------------------------
# Misc monitoring endpoints
# ---------------------------------------------------------------------------

class TestMisc:
    def test_onboarding(self, client):
        r = client.get("/api/onboarding")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_agents_status(self, client):
        r = client.get("/api/agents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all(isinstance(item, dict) and "name" in item for item in data)

    def test_mcp_status(self, client):
        r = client.get("/api/mcp/status")
        assert r.status_code == 200
        data = r.json()
        assert "servers" in data
