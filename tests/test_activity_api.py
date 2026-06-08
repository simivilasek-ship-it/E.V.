"""Integration tests for Work Timeline API."""

import pytest

pytestmark = pytest.mark.integration


class TestActivityAPI:
    def test_activity_today(self, api_client):
        r = api_client.get("/api/activity/today")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert "summary" in data

    def test_activity_query_empty(self, api_client):
        r = api_client.get("/api/activity/query")
        assert r.status_code == 200
        assert "answer" in r.json()

    def test_activity_query_today(self, api_client):
        r = api_client.get("/api/activity/query", params={"q": "Co jsem delal dnes?"})
        assert r.status_code == 200
        assert r.json().get("answer")

    def test_proactive(self, api_client):
        r = api_client.get("/api/proactive")
        assert r.status_code == 200
        assert "suggestions" in r.json()

    def test_workspace(self, api_client):
        r = api_client.get("/api/workspace")
        assert r.status_code == 200

    def test_missions_checklist(self, api_client):
        r = api_client.get("/api/missions/checklist")
        assert r.status_code == 200
        assert "missions" in r.json()

    def test_missions_checklist_crud(self, api_client):
        r = api_client.post(
            "/api/missions/checklist",
            json={"title": "Test release", "items": ["step 1"]},
        )
        assert r.status_code == 200
        mid = r.json().get("id")
        assert mid
        r2 = api_client.delete(f"/api/missions/checklist/{mid}")
        assert r2.status_code == 200
        assert r2.json().get("ok") is True
