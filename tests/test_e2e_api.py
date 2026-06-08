"""E2E / integrační API testy — běží v CI s pytest -m integration."""

import pytest

pytestmark = pytest.mark.integration


class TestHealthE2E:
    def test_health(self, api_client):
        r = api_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ("ok", "healthy")
        assert "version" in data


class TestActivityE2E:
    def test_activity_today(self, api_client):
        r = api_client.get("/api/activity/today")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert "summary" in data

    def test_activity_query(self, api_client):
        r = api_client.get("/api/activity/query", params={"q": "Co jsem delal dnes?"})
        assert r.status_code == 200
        assert r.json().get("answer")

    def test_proactive_and_workspace(self, api_client):
        assert api_client.get("/api/proactive").status_code == 200
        assert api_client.get("/api/workspace").status_code == 200


class TestMissionsE2E:
    def test_autonomous_missions_list(self, api_client):
        r = api_client.get("/api/missions")
        assert r.status_code == 200
        assert "missions" in r.json()

    def test_checklist_crud(self, api_client):
        r = api_client.post(
            "/api/missions/checklist",
            json={"title": "E2E Release", "items": ["Bump", "Test", "Push"]},
        )
        assert r.status_code == 200
        data = r.json()
        mid = data.get("id")
        assert mid
        assert data.get("total_count") == 3

        r2 = api_client.post(
            f"/api/missions/checklist/{mid}/toggle",
            json={"item_id": "1"},
        )
        assert r2.status_code == 200
        assert r2.json().get("done_count") == 1

        r3 = api_client.delete(f"/api/missions/checklist/{mid}")
        assert r3.status_code == 200
        assert r3.json().get("ok") is True

    def test_checklist_not_in_autonomous_list(self, api_client):
        created = api_client.post(
            "/api/missions/checklist",
            json={"title": "Isolated checklist"},
        ).json()
        mid = created["id"]
        missions = api_client.get("/api/missions").json().get("missions", [])
        assert not any(m["id"] == mid for m in missions)
        api_client.delete(f"/api/missions/checklist/{mid}")


class TestAgentTimelineE2E:
    def test_agent_timeline(self, api_client):
        r = api_client.get("/api/agent/timeline")
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data

    def test_agent_timeline_schema(self, api_client):
        api_client.post("/api/agent/timeline", json={
            "id": "e2e-run-1",
            "task": "E2E test task",
            "steps": [{"type": "plan", "message": "test"}],
            "result": "OK",
            "status": "done",
            "duration": 1.5,
        })
        runs = api_client.get("/api/agent/timeline").json().get("runs", [])
        hit = next((x for x in runs if x.get("id") == "e2e-run-1"), None)
        assert hit is not None
        assert hit.get("answer") == "OK"
        assert "duration_ms" in hit
        assert "started_at" in hit


class TestUnifiedMissionsDB:
    """Checklisty i autonomní mise sdílí SQLite missions.db."""

    def test_shared_db_checklist_persists(self, api_client, tmp_path, monkeypatch):
        from mission_manager import get_mission_manager, get_db_path
        from config import CONFIG

        r = api_client.post(
            "/api/missions/checklist",
            json={"title": "DB unity", "items": ["a"]},
        )
        mid = r.json()["id"]
        mgr = get_mission_manager(CONFIG)
        checklists = mgr.list_checklists()
        assert any(c["id"] == mid for c in checklists)
        assert get_db_path().exists()
        api_client.delete(f"/api/missions/checklist/{mid}")
