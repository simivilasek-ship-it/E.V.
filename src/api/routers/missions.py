"""Auto-migrated from dashboard.py — missions routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil

from src.api.deps import (
    HAS_LOGURU,
    __version__,
    get_scheduler,
    get_security_manager,
    logger,
    logger_module_available,
    start_time,
)
from src.api.paths import ROOT
from src.api.ws import (
    confirm_mgr,
    graph_clients,
    graph_mgr,
    ws_clients,
    ws_mgr,
)

if logger_module_available:
    pass  # imports satisfied above
else:
    def get_scheduler():  # type: ignore
        raise RuntimeError("scheduler unavailable")

    def get_security_manager():  # type: ignore
        raise RuntimeError("security unavailable")


def register(app):

    # ── Mission Manager API ───────────────────────────

    @app.get("/api/missions")
    async def list_missions():
        try:
            from mission_manager import get_mission_manager
            return {"missions": get_mission_manager().list_missions()}
        except Exception as e:
            return {"missions": [], "error": str(e)}

    @app.post("/api/missions")
    async def create_mission(request: Request):
        try:
            from mission_manager import get_mission_manager
            import asyncio
            data = await request.json()
            mgr  = get_mission_manager()
            mission = await asyncio.get_event_loop().run_in_executor(
                None, lambda: mgr.create_mission(
                    data["title"], data.get("description", ""),
                    data.get("deadline")))
            return {"ok": True, "mission": mission}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/pause")
    async def pause_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().pause_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/resume")
    async def resume_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().resume_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.delete("/api/missions/{mission_id}")
    async def delete_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().delete_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


