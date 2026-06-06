"""Auto-migrated from dashboard.py — graph routes."""
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

    @app.get("/api/graph/state")
    async def graph_state():
        """Vrátí aktuální stav graf agenta."""
        return {
            "nodes": ["planner", "router", "executor", "critic"],
            "edges": [
                {"from": "planner", "to": "router"},
                {"from": "router", "to": "executor"},
                {"from": "executor", "to": "critic"},
                {"from": "critic", "to": "router"},
                {"from": "critic", "to": "done"},
            ],
            "active_node": None,
            "status": "idle",
        }


