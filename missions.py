"""
JARVIS — Mission Control
Sledování dlouhodobých úkolů / release s checklistem.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from activity_store import get_activity_store

logger = logging.getLogger(__name__)


class MissionStore:
    """Persistentní úložiště misí."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or (Path.home() / ".jarvis" / "missions.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"missions": self._default_missions()}

    def _default_missions(self) -> List[dict]:
        return [
            {
                "id": "mission-jarvis-v5",
                "title": "Release v5.0",
                "status": "active",
                "created_at": time.time(),
                "items": [
                    {"id": "1", "label": "Work Timeline", "done": True},
                    {"id": "2", "label": "Proactive AI", "done": True},
                    {"id": "3", "label": "Workspace Awareness", "done": True},
                    {"id": "4", "label": "Mission Control", "done": True},
                    {"id": "5", "label": "Activity Feed", "done": True},
                    {"id": "6", "label": "Voice V2", "done": False},
                ],
            },
        ]

    def _save(self):
        with self._lock:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def list_missions(self, status: Optional[str] = None) -> List[dict]:
        missions = self._data.get("missions", [])
        if status:
            missions = [m for m in missions if m.get("status") == status]
        return [self._enrich(m) for m in missions]

    def _enrich(self, mission: dict) -> dict:
        items = mission.get("items", [])
        done = sum(1 for i in items if i.get("done"))
        total = len(items)
        return {
            **mission,
            "progress": round(done / total * 100) if total else 0,
            "done_count": done,
            "total_count": total,
        }

    def get(self, mission_id: str) -> Optional[dict]:
        for m in self._data.get("missions", []):
            if m["id"] == mission_id:
                return self._enrich(m)
        return None

    def create(self, title: str, items: Optional[List[str]] = None) -> dict:
        mid = f"mission-{uuid.uuid4().hex[:8]}"
        mission = {
            "id": mid,
            "title": title,
            "status": "active",
            "created_at": time.time(),
            "items": [
                {"id": str(i + 1), "label": label, "done": False}
                for i, label in enumerate(items or [])
            ],
        }
        with self._lock:
            self._data.setdefault("missions", []).append(mission)
            self._save()
        get_activity_store().record(
            "mission.update", title=f"Nová mise: {title}",
            source="missions", meta={"mission_id": mid},
        )
        return self._enrich(mission)

    def toggle_item(self, mission_id: str, item_id: str) -> Optional[dict]:
        with self._lock:
            for m in self._data.get("missions", []):
                if m["id"] != mission_id:
                    continue
                for item in m.get("items", []):
                    if item["id"] == item_id:
                        item["done"] = not item.get("done", False)
                        self._save()
                        enriched = self._enrich(m)
                        get_activity_store().record(
                            "mission.update",
                            title=f"{item['label']}: {'✓' if item['done'] else '○'}",
                            source="missions",
                            meta={"mission_id": mission_id, "item_id": item_id},
                        )
                        if enriched["progress"] == 100:
                            m["status"] = "completed"
                            self._save()
                            get_activity_store().record(
                                "mission.complete", title=m["title"],
                                source="missions", meta={"mission_id": mission_id},
                            )
                        return enriched
        return None

    def add_item(self, mission_id: str, label: str) -> Optional[dict]:
        with self._lock:
            for m in self._data.get("missions", []):
                if m["id"] == mission_id:
                    new_id = str(len(m.get("items", [])) + 1)
                    m.setdefault("items", []).append(
                        {"id": new_id, "label": label, "done": False})
                    self._save()
                    return self._enrich(m)
        return None

    def delete_mission(self, mission_id: str) -> bool:
        with self._lock:
            before = len(self._data.get("missions", []))
            self._data["missions"] = [
                m for m in self._data.get("missions", [])
                if m["id"] != mission_id
            ]
            self._save()
            return len(self._data["missions"]) < before


_store: Optional[MissionStore] = None


def get_mission_store() -> MissionStore:
    global _store
    if _store is None:
        _store = MissionStore()
    return _store
