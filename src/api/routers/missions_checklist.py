"""Mission Control checklist API (missions.py MissionStore)."""
from __future__ import annotations

from fastapi import Request

from src.api.deps import HAS_FASTAPI


def register(app):
    if not HAS_FASTAPI:
        return

    @app.get("/api/missions/checklist")
    async def list_checklists():
        from missions import get_mission_store
        return {"missions": get_mission_store().list_missions()}

    @app.post("/api/missions/checklist")
    async def create_checklist(request: Request):
        body = await request.json()
        title = (body.get("title") or "").strip()
        items = body.get("items") or []
        if not title:
            return {"error": "Chybí title"}
        from missions import get_mission_store
        return get_mission_store().create(title, items)

    @app.post("/api/missions/checklist/{mission_id}/toggle")
    async def toggle_checklist_item(mission_id: str, request: Request):
        body = await request.json()
        item_id = body.get("item_id", "")
        from missions import get_mission_store
        result = get_mission_store().toggle_item(mission_id, item_id)
        if not result:
            return {"error": "Mise nebo položka nenalezena"}
        return result

    @app.post("/api/missions/checklist/{mission_id}/items")
    async def add_checklist_item(mission_id: str, request: Request):
        body = await request.json()
        label = (body.get("label") or "").strip()
        if not label:
            return {"error": "Chybí label"}
        from missions import get_mission_store
        result = get_mission_store().add_item(mission_id, label)
        if not result:
            return {"error": "Mise nenalezena"}
        return result
