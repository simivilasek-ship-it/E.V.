"""Mission Manager API routes."""
from __future__ import annotations

from fastapi import Request

from src.api.deps import logger


def _mission_mgr():
    from config import CONFIG
    from mission_manager import get_mission_manager
    return get_mission_manager(CONFIG)


def register(app):

    @app.get("/api/missions")
    async def list_missions():
        try:
            return {"missions": _mission_mgr().list_missions()}
        except Exception as e:
            return {"missions": [], "error": str(e)}

    @app.post("/api/missions")
    async def create_mission(request: Request):
        try:
            import asyncio
            data = await request.json()
            mgr = _mission_mgr()
            mission = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: mgr.create_mission(
                    data["title"],
                    data.get("description", ""),
                    data.get("deadline"),
                    agent_mode=data.get("agent_mode", "single"),
                ),
            )
            return {"ok": True, "mission": mission}
        except Exception as e:
            logger.debug(f"create_mission: {e}")
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/pause")
    async def pause_mission(mission_id: str):
        try:
            _mission_mgr().pause_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/resume")
    async def resume_mission(mission_id: str):
        try:
            _mission_mgr().resume_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.delete("/api/missions/{mission_id}")
    async def delete_mission(mission_id: str):
        try:
            _mission_mgr().delete_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
