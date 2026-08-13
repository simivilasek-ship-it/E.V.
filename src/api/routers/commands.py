"""Auto-migrated from dashboard.py — commands routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil
from fastapi.responses import JSONResponse

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

    @app.post("/api/notify")
    async def send_notification(body: dict):
        """Odešle desktop notifikaci přes libnotify."""
        from notification_engine import get_notification_engine
        ok = get_notification_engine().send(
            title=body.get("title", "E.V."),
            body=body.get("body", ""),
            urgent=body.get("urgent", False)
        )
        return {"ok": ok}

    _DEPRECATION_HEADERS = {
        "Deprecation": "true",
        "Link": '</api/chat>; rel="successor-version"',
    }

    @app.post("/api/command")
    async def run_command(body: dict):
        """Spustí příkaz přes unified runtime (deprecated — použij /api/chat)."""
        cmd = body.get("command", "").strip()
        if not cmd:
            return JSONResponse(
                status_code=200,
                content={"error": "Prázdný příkaz", "deprecated": True, "use": "/api/chat"},
                headers=_DEPRECATION_HEADERS,
            )
        try:
            from src.api.runtime import process_chat

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: process_chat(cmd),
            )
            return JSONResponse(
                status_code=200,
                content={"response": response, "deprecated": True, "use": "/api/chat"},
                headers=_DEPRECATION_HEADERS,
            )
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={
                    "response": f"Chyba: {e}",
                    "error": str(e),
                    "deprecated": True,
                    "use": "/api/chat",
                },
                headers=_DEPRECATION_HEADERS,
            )


