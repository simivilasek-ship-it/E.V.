"""Auto-migrated from dashboard.py — agents routes."""
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

    # ── Agent Timeline ────────────────────────────────
    # ── Agent Timeline — SQLite persistence ──────────
    import sqlite3 as _sqlite3
    from pathlib import Path as _TLPath

    _TL_DB = ROOT / "memory_data" / "agent_runs.db"
    _TL_DB.parent.mkdir(parents=True, exist_ok=True)

    def _tl_init():
        with _sqlite3.connect(_TL_DB) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id       TEXT PRIMARY KEY,
                    task     TEXT,
                    steps    TEXT,
                    result   TEXT,
                    status   TEXT,
                    duration REAL,
                    ts       REAL
                )
            """)
    _tl_init()

    def _tl_save(run: dict):
        import json as _j, time as _t
        with _sqlite3.connect(_TL_DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO agent_runs VALUES (?,?,?,?,?,?,?)",
                (run.get("id", str(_t.time())),
                 run.get("task", ""),
                 _j.dumps(run.get("steps", []), ensure_ascii=False),
                 run.get("result", ""),
                 run.get("status", "done"),
                 run.get("duration", 0),
                 _t.time()))

    @app.get("/api/agent/timeline")
    async def agent_timeline(limit: int = 30):
        import json as _j
        try:
            with _sqlite3.connect(_TL_DB) as con:
                con.row_factory = _sqlite3.Row
                rows = con.execute(
                    "SELECT * FROM agent_runs ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
            runs = [{
                "id": r["id"], "task": r["task"],
                "steps": _j.loads(r["steps"]),
                "result": r["result"], "status": r["status"],
                "duration": r["duration"], "ts": r["ts"],
            } for r in rows]
            return {"runs": runs, "total": len(runs)}
        except Exception as e:
            return {"runs": [], "error": str(e)}

    @app.post("/api/agent/timeline")
    async def agent_timeline_save(body: dict):
        """Uloží agentský run do SQLite."""
        try:
            _tl_save(body)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


