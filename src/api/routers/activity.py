"""Work Timeline + Activity Feed API routes."""
from __future__ import annotations

import json

from src.api.deps import HAS_FASTAPI, logger

if HAS_FASTAPI:
    from fastapi import Request, WebSocket, WebSocketDisconnect
    import asyncio


_activity_clients: set = set()


async def _broadcast_activity(entry: dict):
    dead = set()
    payload = json.dumps({"type": "activity", **entry})
    for client in list(_activity_clients):
        try:
            await client.send_text(payload)
        except Exception:
            dead.add(client)
    _activity_clients.difference_update(dead)


def register(app):
    if not HAS_FASTAPI:
        return

    @app.get("/api/activity/today")
    async def activity_today():
        from activity_store import get_activity_store
        store = get_activity_store()
        return {"events": store.get_today(), "summary": store.daily_summary()}

    @app.get("/api/activity/feed")
    async def activity_feed():
        from activity_bridge import get_activity_feed
        from activity_store import get_activity_store
        return {
            "feed": get_activity_feed(),
            "events": get_activity_store().get_feed(30),
        }

    @app.get("/api/activity/summary")
    async def activity_summary(day: str = ""):
        from activity_store import get_activity_store
        from datetime import date as _date
        d = _date.fromisoformat(day) if day else None
        return get_activity_store().daily_summary(d)

    @app.get("/api/activity/query")
    async def activity_query(q: str = ""):
        from activity_store import get_activity_store
        if not q:
            return {"answer": "Zadej dotaz, napr. 'Co jsem delal dnes?'", "data": {}}
        return get_activity_store().query_natural(q)

    @app.get("/api/workspace")
    async def workspace_context():
        from context_orchestrator import get_context_orchestrator
        from config import CONFIG
        return get_context_orchestrator(CONFIG).get_context_data()

    @app.get("/api/proactive")
    async def proactive_suggestions():
        from activity_bridge import get_proactive_suggestions
        return {"suggestions": get_proactive_suggestions()}

    @app.post("/api/proactive/dismiss")
    async def dismiss_suggestion(request: Request):
        import activity_bridge as ab
        body = await request.json()
        sid = body.get("id", "")
        ab._proactive_suggestions[:] = [
            s for s in ab._proactive_suggestions if s["id"] != sid
        ]
        return {"ok": True}

    @app.websocket("/ws/activity")
    async def ws_activity(ws: WebSocket):
        await ws.accept()
        _activity_clients.add(ws)
        try:
            from activity_bridge import get_activity_feed, get_proactive_suggestions
            for entry in get_activity_feed():
                await ws.send_text(json.dumps({"type": "activity", **entry}))
            for sug in get_proactive_suggestions():
                await ws.send_text(json.dumps({"type": "proactive", **sug}))
            while True:
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            _activity_clients.discard(ws)
        except Exception:
            _activity_clients.discard(ws)

    # Wire activity broadcaster into bridge
    try:
        from activity_bridge import set_broadcasters
        from src.api import ws as ws_mod

        async def _emit(entry: dict):
            await _broadcast_activity(entry)

        if ws_mod.main_loop:
            set_broadcasters(activity_fn=_emit, loop=ws_mod.main_loop)
    except Exception as e:
        logger.debug(f"Activity broadcaster init: {e}")
