#!/usr/bin/env python3
"""One-shot migration: split dashboard.py route handlers into src/api/routers/."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard.py"
OUT_DIR = ROOT / "src" / "api" / "routers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

text = DASH.read_text(encoding="utf-8")
lines = text.splitlines()

# Extract route block: from first @app.get("/health") to app.broadcast_log assignment
start = next(i for i, l in enumerate(lines) if '@app.get("/health")' in l)
end = next(i for i, l in enumerate(lines) if "app.broadcast_log = _broadcast_log" in l) + 1
route_lines = lines[start:end]

body = "\n".join(route_lines)

# Replacements for extracted module
replacements = [
    ("_ws_mgr", "ws_mgr"),
    ("_graph_mgr", "graph_mgr"),
    ("_confirm_mgr", "confirm_mgr"),
    ("_ws_clients", "ws_clients"),
    ("_graph_clients", "graph_clients"),
    ("_start_time", "start_time"),
    ("_main_loop", "main_loop"),
    ('@app.get("/", response_class=HTMLResponse)\n    async def root():\n        return DASHBOARD_HTML',
     '@app.get("/", include_in_schema=False)\n    async def root():\n        from fastapi.responses import RedirectResponse\n        return RedirectResponse(url="/app", status_code=302)'),
    ("Path(__file__).parent", "ROOT"),
    ("_Path(__file__).parent", "ROOT"),
    ("_TLPath(__file__).parent", "ROOT"),
]

for old, new in replacements:
    body = body.replace(old, new)

# Split into logical router files by section markers
sections = {
    "monitoring": (
        r'@app\.get\("/health"\).*?(?=@app\.post\("/api/notify"\)|\Z)',
    ),
}

# Manual split by line markers in original file (relative to route block)
markers = [
    ("health", '@app.post("/api/notify")'),
    ("commands", "    # ── Plugin Marketplace"),
    ("marketplace", "    @app.get(\"/api/memory\")"),
    ("memory", "    @app.get(\"/api/profile\")"),
    ("config", "    # ── Workflow Builder"),
    ("workflows", "    # ── Mission Manager API"),
    ("missions", "    # ── Vision v2 API"),
    ("vision", "    # ── Agent Timeline"),
    ("agents", "    # ── Skill Generator"),
    ("skills", "    @app.post(\"/api/agent/parallel\")"),
    ("chat", "    @app.websocket(\"/ws/logs\")"),
    ("websockets", "    @app.get(\"/api/models\")"),
    ("settings", "    @app.post(\"/api/vision\")"),
    ("vision_post", "    @app.get(\"/api/graph/state\")"),
    ("graph", "    @app.websocket(\"/ws/agents\")"),
    ("ws_agents", "    # ── Broadcast helper"),
    ("broadcast", None),
]

# Build chunks from route_lines with indices
route_text = "\n".join(route_lines)
chunks: dict[str, str] = {}
for i, (name, end_marker) in enumerate(markers):
    start_marker = markers[i - 1][1] if i > 0 else '@app.get("/health")'
    if i == 0:
        s_idx = route_text.find(start_marker)
    else:
        s_idx = route_text.find(start_marker)
    if end_marker:
        e_idx = route_text.find(end_marker, s_idx + 1)
        chunk = route_text[s_idx:e_idx]
    else:
        chunk = route_text[s_idx:]
    for old, new in replacements:
        chunk = chunk.replace(old, new)
    chunks[name] = chunk

HEADER = '''"""Auto-migrated from dashboard.py — {name} routes."""
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
'''

# Fix monitoring chunk - includes health through audit + CORS was between audit and notify in original
# Re-merge health+monitoring: first chunk should be health through audit only
health_chunk = chunks.get("health", "")
# health chunk currently goes to notify - split at CORS comment if present
cors_split = health_chunk.find("    # ── CORS")
if cors_split != -1:
    monitoring_body = health_chunk[:cors_split]
    commands_prefix = health_chunk[cors_split:]
    chunks["commands"] = commands_prefix + chunks.get("commands", "")
    chunks["monitoring"] = monitoring_body
    del chunks["health"]

for name, chunk in chunks.items():
    if not chunk.strip():
        continue
    fname = OUT_DIR / f"{name}.py"
    # dedupe broadcast - only in broadcast module
    if name != "broadcast" and "app.broadcast_log" in chunk:
        chunk = chunk.split("app.broadcast_log")[0]
    content = HEADER.format(name=name) + "\n" + chunk + "\n"
    # Fix imports used in chunk - add fastapi imports at top of register is fine inside
    fname.write_text(content, encoding="utf-8")
    print(f"Wrote {fname} ({len(chunk)} chars)")

# __init__.py
init = '''"""Register all API routers on the FastAPI app."""
from src.api.routers import (
    agents,
    broadcast,
    chat,
    commands,
    config,
    graph,
    marketplace,
    memory,
    missions,
    monitoring,
    settings,
    skills,
    vision,
    vision_post,
    websockets,
    workflows,
    ws_agents,
)

ROUTERS = (
    monitoring,
    commands,
    marketplace,
    memory,
    config,
    workflows,
    missions,
    vision,
    agents,
    skills,
    chat,
    websockets,
    settings,
    vision_post,
    graph,
    ws_agents,
    broadcast,
)


def register_all(app):
    for mod in ROUTERS:
        mod.register(app)
'''

(OUT_DIR / "__init__.py").write_text(init, encoding="utf-8")
print("Done.")
