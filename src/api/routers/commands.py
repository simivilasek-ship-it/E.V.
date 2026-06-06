"""Auto-migrated from dashboard.py — commands routes."""
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

    @app.post("/api/notify")
    async def send_notification(body: dict):
        """Odešle desktop notifikaci přes libnotify."""
        from notification_engine import get_notification_engine
        ok = get_notification_engine().send(
            title=body.get("title", "JARVIS"),
            body=body.get("body", ""),
            urgent=body.get("urgent", False)
        )
        return {"ok": ok}

    @app.post("/api/command")
    async def run_command(body: dict):
        """Spustí příkaz přes JARVIS a vrátí odpověď."""
        cmd = body.get("command", "").strip()
        if not cmd:
            return {"error": "Prázdný příkaz"}
        try:
            from llm import LLMEngine, LocalRouter
            from config import CONFIG
            router = LocalRouter()
            msg, action = router.route(cmd)
            if action:
                from commands import CommandExecutor
                cmds = CommandExecutor(CONFIG)
                result = cmds.execute(action["action"], action.get("params", {}))
                return {"response": result or msg, "action": action["action"]}
            # Fallback — LLM
            llm = LLMEngine(CONFIG)
            resp, _ = llm.ask(cmd)
            return {"response": resp}
        except Exception as e:
            return {"response": f"Chyba: {e}", "error": str(e)}


