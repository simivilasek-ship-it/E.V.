"""Integration tests for Work Timeline API."""

import pytest


@pytest.fixture
def client():
    try:
        from fastapi.testclient import TestClient
        from src.api.app import app
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"FastAPI app unavailable: {e}")


class TestActivityAPI:
    def test_activity_today(self, client):
        r = client.get("/api/activity/today")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert "summary" in data

    def test_activity_query_empty(self, client):
        r = client.get("/api/activity/query")
        assert r.status_code == 200
        assert "answer" in r.json()

    def test_activity_query_today(self, client):
        r = client.get("/api/activity/query", params={"q": "Co jsem delal dnes?"})
        assert r.status_code == 200
        assert r.json().get("answer")

    def test_proactive(self, client):
        r = client.get("/api/proactive")
        assert r.status_code == 200
        assert "suggestions" in r.json()

    def test_workspace(self, client):
        r = client.get("/api/workspace")
        assert r.status_code == 200

    def test_missions_checklist(self, client):
        r = client.get("/api/missions/checklist")
        assert r.status_code == 200
        assert "missions" in r.json()

    def test_missions_checklist_crud(self, client):
        r = client.post("/api/missions/checklist", json={"title": "Test release", "items": ["step 1"]})
        assert r.status_code == 200
        mid = r.json().get("id")
        assert mid
        r2 = client.delete(f"/api/missions/checklist/{mid}")
        assert r2.status_code == 200
        assert r2.json().get("ok") is True
