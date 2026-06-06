"""Auto-migrated from dashboard.py — chat routes."""
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

    @app.post("/api/agent/parallel")
    async def agent_parallel(body: dict):
        """Spustí MultiAgentOrchestrator v paralelním režimu.

        Body: {"task": "...", "max_steps": 5}
        Vrátí výsledky kroků s časováním.
        """
        task = body.get("task", "").strip()
        if not task:
            return {"error": "Chybí task"}
        max_steps = min(int(body.get("max_steps", 5)), 8)
        try:
            from config import CONFIG
            from commands import CommandExecutor
            from agent_roles import MultiAgentOrchestrator
            url   = CONFIG.get("ollama_url",   "http://localhost:11434/api/chat")
            model = CONFIG.get("ollama_model", "qwen2.5:3b")
            orch  = MultiAgentOrchestrator(url, model, executor=CommandExecutor(CONFIG))
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: orch.run_parallel(task, max_steps=max_steps))
            return {"result": result, "task": task}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/chat")
    async def chat_rest(body: dict):
        """REST fallback pro chat — vrátí celou odpověď najednou."""
        text = body.get("text", "").strip()
        if not text:
            return {"response": "Prázdná zpráva"}
        try:
            from local_router import LocalRouter
            from config import CONFIG
            msg, action = LocalRouter().route(text)
            if action and action.get("action") not in ("answer", None):
                from commands import CommandExecutor
                result = CommandExecutor(CONFIG).execute(action["action"], action.get("params", {}))
                return {"response": result or msg or "Hotovo."}
            from llm import LLMEngine
            resp, _ = LLMEngine(CONFIG).ask(text)
            return {"response": resp}
        except Exception as e:
            return {"response": f"Chyba: {e}"}

    @app.websocket("/ws/chat")
    async def ws_chat(ws: WebSocket):
        """WebSocket chat — streaming odpovědi chunk po chunku."""
        await ws.accept()

        async def send(obj: dict):
            try:
                await ws.send_text(json.dumps(obj))
            except Exception:
                pass

        try:
            while True:
                raw  = await ws.receive_text()
                data = json.loads(raw)
                text = (data.get("command") or data.get("text") or "").strip()
                if not text:
                    continue

                try:
                    from llm import LocalRouter, LLMEngine
                    from config import CONFIG

                    # LocalRouter je rychlý (regex) — OK synchronně
                    msg, action = LocalRouter().route(text)

                    if action and action.get("action") not in ("answer", None):
                        # Blokující OS příkaz → thread aby neblokoval event loop
                        from commands import CommandExecutor
                        def _run_cmd():
                            return CommandExecutor(CONFIG).execute(
                                action["action"], action.get("params", {}))
                        try:
                            import anyio
                            result = await anyio.to_thread.run_sync(_run_cmd)
                        except ImportError:
                            result = await asyncio.get_event_loop().run_in_executor(
                                None, _run_cmd)
                        reply = result or msg or "Hotovo."
                        await send({"type": "chunk", "data": reply})
                        await send({"type": "done"})
                    else:
                        # stream_ask je synchronní generátor — spusť v threadu,
                        # výsledky přeposílej přes asyncio.Queue do event loopu
                        llm    = LLMEngine(CONFIG)
                        q: asyncio.Queue = asyncio.Queue()

                        loop = asyncio.get_event_loop()

                        def _stream():
                            try:
                                for chunk in llm.stream_ask(text):
                                    if isinstance(chunk, str) and chunk:
                                        asyncio.run_coroutine_threadsafe(
                                            q.put(chunk), loop)
                            finally:
                                asyncio.run_coroutine_threadsafe(
                                    q.put(None), loop)

                        loop.run_in_executor(None, _stream)

                        while True:
                            chunk = await q.get()
                            if chunk is None:
                                break
                            await send({"type": "chunk", "data": chunk})
                            await asyncio.sleep(0)
                        await send({"type": "done"})

                except Exception as e:
                    logger.error(f"ws_chat chyba: {e}")
                    await send({"type": "error", "data": str(e)})

        except WebSocketDisconnect:
            await ws_mgr.disconnect(ws)
        except Exception as e:
            logger.warning(f"ws_chat uzavřen: {e}")
            await ws_mgr.disconnect(ws)


