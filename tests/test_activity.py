"""Testy pro Work Timeline + Activity systém."""

import time
from datetime import date

import pytest


class TestActivityStore:
    def test_record_and_retrieve(self, tmp_path):
        from activity_store import ActivityStore
        store = ActivityStore(db_path=tmp_path / "act.db")
        store.record("git.commit", title="fix bug", project="Jarvis")
        events = store.get_today()
        assert len(events) >= 1
        assert events[-1]["type"] == "git.commit"
        assert events[-1]["project"] == "Jarvis"

    def test_daily_summary(self, tmp_path):
        from activity_store import ActivityStore
        store = ActivityStore(db_path=tmp_path / "act.db")
        store.record("git.commit", title="feat: timeline", project="Jarvis")
        store.record("git.commit", title="feat: feed", project="Jarvis")
        store.record("build.fail", title="Build selhal", project="Jarvis")
        summary = store.daily_summary()
        assert summary["commits"] == 2
        assert summary["builds_failed"] == 1
        assert len(summary["summary"]) >= 2

    def test_query_natural_today(self, tmp_path):
        from activity_store import ActivityStore
        store = ActivityStore(db_path=tmp_path / "act.db")
        store.record("git.commit", title="test", project="X")
        result = store.query_natural("Co jsem dělal dnes?")
        assert "answer" in result
        assert len(result["answer"]) > 0


class TestMissionStore:
    def test_create_and_toggle_sqlite(self, tmp_path):
        from mission_manager import reset_mission_manager, set_db_path
        from missions import MissionStore

        set_db_path(tmp_path / "missions.db")
        reset_mission_manager()
        ms = MissionStore()
        m = ms.create("Test Release", ["Item A", "Item B"])
        assert m["total_count"] == 2
        assert m["progress"] == 0
        updated = ms.toggle_item(m["id"], "1")
        assert updated["done_count"] == 1
        assert updated["progress"] == 50
        assert ms.delete_mission(m["id"]) is True


class TestActivityBridge:
    def test_agent_timeline_recording(self):
        from activity_bridge import (
            record_agent_run_start, record_agent_step,
            record_agent_run_end, get_agent_timeline,
        )
        run_id = record_agent_run_start("Test task", "graph")
        record_agent_step(run_id, "plan", "Plánuji kroky")
        record_agent_run_end(run_id, "Hotovo")
        runs = get_agent_timeline()
        assert len(runs) >= 1
        assert runs[-1]["status"] == "done"
        assert len(runs[-1]["steps"]) == 1
