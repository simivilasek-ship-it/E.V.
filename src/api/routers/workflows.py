"""Auto-migrated from dashboard.py — workflows routes."""
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

    # ── Workflow Builder ──────────────────────────────
    @app.get("/api/workflows")
    async def list_workflows():
        from workflow_engine import get_workflow_engine
        return {"workflows": get_workflow_engine().list_all()}

    @app.post("/api/workflows")
    async def create_workflow(body: dict):
        import uuid
        from workflow_engine import get_workflow_engine, Workflow
        wf = Workflow(
            id=str(uuid.uuid4())[:8],
            name=body.get("name", "Nový workflow"),
            trigger_type=body.get("trigger_type", "manual"),
            trigger_config=body.get("trigger_config", {}),
            action=body.get("action", ""),
            cooldown_seconds=body.get("cooldown_seconds", 300),
        )
        get_workflow_engine().add(wf)
        return {"id": wf.id, "ok": True}

    @app.delete("/api/workflows/{workflow_id}")
    async def delete_workflow(workflow_id: str):
        from workflow_engine import get_workflow_engine
        ok = get_workflow_engine().remove(workflow_id)
        return {"ok": ok}


