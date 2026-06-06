"""Chat routes — unified Copilot + Agent pipeline."""
from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from src.api.deps import logger
from src.api.ws import ws_mgr


def register(app):

    @app.post("/api/agent/parallel")
    async def agent_parallel(body: dict):
        task = body.get("task", "").strip()
        if not task:
            return {"error": "Chybí task"}
        max_steps = min(int(body.get("max_steps", 5)), 8)
        try:
            from src.api.runtime import get_runtime
            from agent_roles import MultiAgentOrchestrator

            rt = get_runtime()
            orch = MultiAgentOrchestrator(
                rt.llm.url, rt.llm.model, executor=rt.cmds, mcp_bridge=getattr(rt, "mcp", None),
            )
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: orch.run_parallel(task, max_steps=max_steps),
            )
            return {"result": result, "task": task}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/chat")
    async def chat_rest(body: dict):
        text = body.get("text", "").strip()
        if not text:
            return {"response": "Prázdná zpráva"}
        try:
            from src.api.runtime import process_chat

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: process_chat(text),
            )
            return {"response": response}
        except Exception as e:
            return {"response": f"Chyba: {e}"}

    @app.websocket("/ws/chat")
    async def ws_chat(ws: WebSocket):
        """WebSocket chat — streaming přes unified runtime."""
        await ws.accept()

        async def send(obj: dict):
            try:
                await ws.send_text(json.dumps(obj))
            except Exception:
                pass

        try:
            while True:
                raw = await ws.receive_text()
                data = json.loads(raw)
                text = (data.get("command") or data.get("text") or "").strip()
                if not text:
                    continue

                try:
                    from src.api.runtime import process_chat

                    loop = asyncio.get_event_loop()
                    q: asyncio.Queue = asyncio.Queue()

                    def on_chunk(chunk: str) -> None:
                        if chunk:
                            asyncio.run_coroutine_threadsafe(
                                q.put({"type": "chunk", "data": chunk}), loop,
                            )

                    def on_agent_step(step: str) -> None:
                        if step:
                            asyncio.run_coroutine_threadsafe(
                                q.put({"type": "agent_step", "data": step}), loop,
                            )

                    def on_status(status: str) -> None:
                        if status:
                            asyncio.run_coroutine_threadsafe(
                                q.put({"type": "status", "data": status}), loop,
                            )

                    def _run():
                        try:
                            process_chat(
                                text,
                                on_chunk=on_chunk,
                                on_agent_step=on_agent_step,
                                on_status=on_status,
                            )
                        finally:
                            asyncio.run_coroutine_threadsafe(
                                q.put({"type": "_done"}), loop,
                            )

                    loop.run_in_executor(None, _run)

                    while True:
                        msg = await q.get()
                        if msg.get("type") == "_done":
                            break
                        await send(msg)

                    await send({"type": "done"})

                except Exception as e:
                    logger.error(f"ws_chat chyba: {e}")
                    await send({"type": "error", "data": str(e)})

        except WebSocketDisconnect:
            await ws_mgr.disconnect(ws)
        except Exception as e:
            logger.warning(f"ws_chat uzavřen: {e}")
            await ws_mgr.disconnect(ws)
