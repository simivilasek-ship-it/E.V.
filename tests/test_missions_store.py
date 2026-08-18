"""Unit tests for MissionStore checklist facade."""
from __future__ import annotations

import pytest

from mission_manager import reset_mission_manager, set_db_path
from missions import MissionStore, get_mission_store, reset_mission_store

pytestmark = [pytest.mark.unit]


@pytest.fixture
def store(tmp_path):
    reset_mission_store()
    reset_mission_manager()
    set_db_path(tmp_path / "missions.db")
    s = MissionStore(path=tmp_path / "missions.db")
    yield s
    reset_mission_store()
    reset_mission_manager()


def test_checklist_crud(store):
    created = store.create("Release", ["build", "test"])
    assert created["title"] == "Release"
    mid = created["id"]

    listed = store.list_missions()
    assert any(m["id"] == mid for m in listed)
    assert store.get(mid)["id"] == mid
    assert store.get("missing") is None

    item_id = created["items"][0]["id"] if created.get("items") else None
    if item_id:
        toggled = store.toggle_item(mid, item_id)
        assert toggled is not None

    added = store.add_item(mid, "deploy")
    assert added is not None

    assert store.delete_mission(mid) is True
    assert store.get(mid) is None


def test_get_mission_store_singleton(tmp_path):
    reset_mission_store()
    reset_mission_manager()
    set_db_path(tmp_path / "missions.db")
    a = get_mission_store()
    b = get_mission_store()
    assert a is b
    reset_mission_store()
    reset_mission_manager()
