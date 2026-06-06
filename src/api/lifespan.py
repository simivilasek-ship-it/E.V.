"""FastAPI lifespan — EventBus graph events + confirmation bridge."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from src.api.deps import HAS_FASTAPI, logger
from src.api.ws import broadcast_graph_event, confirm_mgr, main_loop as _main_loop_ref

if HAS_FASTAPI:
    from src.api import ws as ws_mod


@asynccontextmanager
async def lifespan(application):
    ws_mod.main_loop = asyncio.get_running_loop()
    try:
        from event_bus import get_event_bus

        def handle_bus_graph(event):
            if ws_mod.main_loop and event.data:
                asyncio.run_coroutine_threadsafe(
                    broadcast_graph_event(event.data),
                    ws_mod.main_loop,
                )

        get_event_bus().subscribe("agent.graph", handle_bus_graph)
        logger.info("Dashboard: Odebírám 'agent.graph' eventy z EventBusu")
    except Exception as e:
        logger.warning(f"Dashboard: nelze se přihlásit k EventBusu: {e}")

    try:
        from confirmation_bridge import set_broadcast

        def _emit_confirm(payload: dict):
            if ws_mod.main_loop:
                asyncio.run_coroutine_threadsafe(
                    confirm_mgr.broadcast(json.dumps(payload)),
                    ws_mod.main_loop,
                )

        set_broadcast(_emit_confirm)
    except Exception as e:
        logger.warning(f"Dashboard: confirmation bridge init failed: {e}")

    # Plný JARVIS runtime — Copilot + Agent pipeline
    try:
        from src.api.runtime import init_runtime

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, init_runtime)
    except Exception as e:
        logger.error(f"JARVIS runtime start selhal: {e}")

    yield

    try:
        from src.api.runtime import shutdown_runtime
        shutdown_runtime()
    except Exception as e:
        logger.debug(f"Runtime shutdown: {e}")
