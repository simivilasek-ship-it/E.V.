"""Auto-migrated from dashboard.py — workflows routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil
from pydantic import BaseModel

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


# ── Workflow Graph Pydantic models ────────────────────────────────────────────
# Edges keep the UI's field names (from/to) stored verbatim; "source"/"target"
# are the canonical names used internally when edges are created via the API.

class WorkflowNode(BaseModel):
    id: str
    type: str   # "trigger" | "action" | "condition" | "delay" | "notify"
    label: str
    x: float = 0
    y: float = 0
    data: dict = {}


class WorkflowEdge(BaseModel):
    id: str = ""
    source: str = ""
    target: str = ""


class WorkflowGraph(BaseModel):
    id: str = ""
    name: str
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    enabled: bool = True


def register(app):

    # ── Workflow Builder ──────────────────────────────
    @app.get("/api/workflows")
    async def list_workflows():
        from workflow_engine import get_workflow_engine
        result = []
        for wf in get_workflow_engine().list_all():
            if wf.get("trigger_type") == "graph" and isinstance(wf.get("trigger_config"), dict):
                graph = wf["trigger_config"].get("_graph")
                if graph:
                    # Return the stored graph with the persisted id and enabled state
                    result.append({**graph, "id": wf["id"], "enabled": wf.get("enabled", True)})
                    continue
            result.append(wf)
        return {"workflows": result}

    @app.post("/api/workflows")
    async def create_workflow(body: dict):
        import uuid
        from workflow_engine import get_workflow_engine, Workflow

        if "nodes" in body:
            # Graph format sent by WorkflowEditor
            graph_id = body.get("id") or str(uuid.uuid4())[:8]
            wf = Workflow(
                id=graph_id,
                name=body.get("name", "Nový workflow"),
                trigger_type="graph",
                trigger_config={"_graph": body},
                action="",
                enabled=body.get("enabled", True),
            )
        else:
            # Legacy plain-action format
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

    @app.post("/api/workflows/graph/test")
    async def test_workflow_graph(body: dict):
        """Projde graf workflow a spustí action uzly jako příkazy (test run)."""
        nodes = body.get("nodes") or []
        edges = body.get("edges") or []
        if not nodes:
            return {"ok": False, "error": "Prázdný workflow"}

        by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id")}
        children: dict[str, list[str]] = {nid: [] for nid in by_id}
        indeg: dict[str, int] = {nid: 0 for nid in by_id}
        for e in edges:
            if not isinstance(e, dict):
                continue
            # Accept both UI format (from/to) and canonical format (source/target)
            f = e.get("from") or e.get("source")
            t = e.get("to") or e.get("target")
            if f in by_id and t in by_id:
                children[f].append(t)
                indeg[t] = indeg.get(t, 0) + 1

        queue = [nid for nid, d in indeg.items() if d == 0]
        order: list[str] = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for ch in children.get(nid, []):
                indeg[ch] -= 1
                if indeg[ch] == 0:
                    queue.append(ch)

        results = []
        for nid in order:
            node = by_id.get(nid, {})
            if node.get("type") != "action":
                continue
            cmd = (node.get("config") or node.get("data") or {}).get("command") or node.get("label") or ""
            cmd = str(cmd).strip()
            if not cmd:
                results.append({"node": nid, "skipped": True})
                continue
            try:
                from llm import LocalRouter
                from config import CONFIG
                from commands import CommandExecutor
                msg, action = LocalRouter().route(cmd)
                if action and action.get("action") not in ("answer", None):
                    out = CommandExecutor(CONFIG).execute(action["action"], action.get("params", {}))
                    results.append({"node": nid, "command": cmd, "result": out or msg})
                else:
                    results.append({"node": nid, "command": cmd, "result": msg or "(routed to LLM)"})
            except Exception as ex:
                results.append({"node": nid, "command": cmd, "error": str(ex)})

        return {"ok": True, "order": order, "results": results}


