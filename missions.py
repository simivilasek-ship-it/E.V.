"""
JARVIS — Release Checklist shim
Checklisty jsou uložené v SQLite (mission_manager.py, mission_type='checklist').
Tento modul zachovává API kompatibilitu pro missions_checklist router a testy.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from config import CONFIG
from mission_manager import get_mission_manager, reset_mission_manager, set_db_path


class MissionStore:
    """Fasáda nad MissionManager checklist API."""

    def __init__(self, path: Optional[Path] = None):
        if path is not None:
            db = path.with_suffix(".db") if path.suffix == ".json" else path
            set_db_path(db)
            reset_mission_manager()
        self._mgr = get_mission_manager(CONFIG)

    def list_missions(self, status: Optional[str] = None) -> List[dict]:
        return self._mgr.list_checklists(status)

    def get(self, mission_id: str) -> Optional[dict]:
        for m in self._mgr.list_checklists():
            if m["id"] == mission_id:
                return m
        return None

    def create(self, title: str, items: Optional[List[str]] = None) -> dict:
        return self._mgr.create_checklist(title, items)

    def toggle_item(self, mission_id: str, item_id: str) -> Optional[dict]:
        return self._mgr.toggle_checklist_item(mission_id, item_id)

    def add_item(self, mission_id: str, label: str) -> Optional[dict]:
        return self._mgr.add_checklist_item(mission_id, label)

    def delete_mission(self, mission_id: str) -> bool:
        return self._mgr.delete_checklist(mission_id)


_store: Optional[MissionStore] = None


def reset_mission_store() -> None:
    global _store
    _store = None


def get_mission_store() -> MissionStore:
    global _store
    if _store is None:
        _store = MissionStore()
    return _store
