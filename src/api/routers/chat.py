"""Chat routes — unified Copilot + Agent pipeline."""
from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response

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

    @app.post("/api/tts/audio")
    async def tts_audio(body: dict):
        """Syntetizuje řeč a vrátí MP3/WAV pro přehrání v prohlížeči."""
        text = (body.get("text") or "").strip()
        if not text:
            return JSONResponse({"error": "Prázdný text"}, status_code=400)
        try:
            from config import CONFIG
            from tts import synthesize_speech

            data, mime = await asyncio.get_event_loop().run_in_executor(
                None, lambda: synthesize_speech(text, CONFIG),
            )
            return Response(content=data, media_type=mime)
        except Exception as e:
            logger.warning(f"/api/tts/audio: {e}")
            return JSONResponse({"error": str(e)}, status_code=503)

    @app.get("/api/voice/greeting")
    async def voice_greeting():
        """Krátký pozdrav při startu — bez čekání na počasí."""
        try:
            from local_router import _USER
            from src.morning_briefing import spoken_hello

            name = str(_USER or "Simone").replace(".", " ").strip().title() or "Simone"
            hello = spoken_hello(name)
            return {"hello": hello, "text": hello, "name": name}
        except Exception as e:
            return {"text": "Čau. Jsem tady.", "hello": "Čau. Jsem tady.", "name": "Simone", "error": str(e)}

    @app.get("/api/voice/briefing")
    async def voice_briefing():
        """Počasí a kalendář — po úvodním pozdravu."""
        try:
            from local_router import _USER
            from src.morning_briefing import spoken_home_briefing

            name = str(_USER or "Simone").replace(".", " ").strip().title() or "Simone"
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, lambda: spoken_home_briefing(name, include_hello=False),
            )
            return {"text": text, "name": name}
        except Exception as e:
            return {"text": "", "error": str(e)}

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
            try:
                from src.api.runtime import speak_web_reply
                speak_web_reply(response)
            except Exception:
                pass
            return {"response": response}
        except Exception as e:
            return {"response": f"Chyba: {e}"}

    @app.post("/api/chat/message")
    async def chat_message(body: dict):
        """Stejná pipeline jako /api/chat — local first, pak LLM/cloud."""
        text = (body.get("text") or "").strip()
        if not text:
            return {"response": "Prázdná zpráva", "source": "local"}
        try:
            from local_router import LocalRouter
            from src.api.runtime import process_chat

            _, action = LocalRouter().route(text)
            source = "local" if action is not None else "llm"
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: process_chat(text),
            )
            return {"response": response, "source": source}
        except Exception as e:
            return {"response": f"Chyba: {e}", "source": "llm"}

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

                    result_box = {"text": ""}

                    def _run():
                        try:
                            result_box["text"] = process_chat(
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
                    try:
                        from src.api.runtime import speak_web_reply
                        speak_web_reply(result_box.get("text") or "")
                    except Exception:
                        pass

                except Exception as e:
                    logger.error(f"ws_chat chyba: {e}")
                    await send({"type": "error", "data": str(e)})

        except WebSocketDisconnect:
            await ws_mgr.disconnect(ws)
        except Exception as e:
            logger.warning(f"ws_chat uzavřen: {e}")
            await ws_mgr.disconnect(ws)
