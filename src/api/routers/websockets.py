"""Auto-migrated from dashboard.py — websockets routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil
from fastapi import WebSocket, WebSocketDisconnect

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

    @app.websocket("/ws/logs")
    async def ws_logs(ws: WebSocket):
        """Live logy přes WebSocket — posílá JSON {level, message, ts}."""
        await ws_mgr.connect(ws)
        ws_clients.add(ws)   # zpětná kompatibilita pro broadcast_log
        try:
            while True:
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await ws_mgr.disconnect(ws)
            ws_clients.discard(ws)

    @app.websocket("/ws/audio")
    async def ws_audio(ws: WebSocket):
        """Duplex audio websocket (MVP).

        Client sends raw PCM16 mono frames (default 16kHz). Server runs VAD and emits
        EventType.AUDIO_SPEECH on detected speech (for barge-in interruption).

        This endpoint is intentionally minimal: it does not perform STT yet.
        """
        await ws.accept()

        try:
            from config import CONFIG
            if not bool(CONFIG.get("audio_ws_enabled", False)):
                await ws.send_text(json.dumps({"type": "error", "data": "audio_ws_enabled is false"}))
                await ws.close()
                return
        except Exception:
            pass

        vad = None
        try:
            from vad import get_vad
            from config import CONFIG
            if bool(CONFIG.get("vad_enabled", True)):
                vad = get_vad(CONFIG)
        except Exception:
            vad = None

        # lazy bus import
        bus = None
        try:
            from event_bus import get_event_bus, EventType
            bus = get_event_bus()
        except Exception:
            bus = None

        try:
            while True:
                frame = await ws.receive_bytes()
                if not frame:
                    continue
                # Debug: optionally broadcast audio frames (off by default)
                try:
                    if bus and False:
                        bus.emit(EventType.AUDIO_FRAME, {"n": len(frame)}, source="ws_audio")
                except Exception:
                    pass

                speech = False
                try:
                    if vad is not None:
                        speech = vad.is_speech(frame)
                except Exception:
                    speech = False

                if speech:
                    # emit event for barge-in
                    try:
                        if bus:
                            bus.emit(EventType.AUDIO_SPEECH, {"ts": time.time()}, source="ws_audio")
                    except Exception:
                        pass
                    # send ack to client
                    try:
                        await ws.send_text(json.dumps({"type": "vad", "speech": True}))
                    except Exception:
                        pass

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws_audio closed: {e}")

    @app.websocket("/ws/graph")
    async def ws_graph(ws: WebSocket):
        """Streaming stavu Graf agenta — posílá JSON eventi."""
        import json as _json
        await graph_mgr.connect(ws)
        graph_clients.add(ws)   # zpětná kompatibilita
        try:
            await ws.send_text(_json.dumps({"type": "ready", "status": "idle"}))
            while True:
                await asyncio.sleep(20)
                await ws.send_text(_json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await graph_mgr.disconnect(ws)
            graph_clients.discard(ws)

    @app.websocket("/ws/confirm")
    async def ws_confirm(ws: WebSocket):
        """Web confirmation channel — pushes confirm_request, accepts approve/deny."""
        import json as _json
        from confirmation_bridge import register_client, unregister_client, respond as confirm_respond

        await confirm_mgr.connect(ws)
        register_client(ws)
        try:
            await ws.send_text(_json.dumps({"type": "ready"}))
            while True:
                raw = await ws.receive_text()
                try:
                    msg = _json.loads(raw)
                except Exception:
                    continue
                if msg.get("type") == "confirm_response":
                    confirm_respond(msg.get("id", ""), bool(msg.get("approved")))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws_confirm closed: {e}")
        finally:
            unregister_client(ws)
            await confirm_mgr.disconnect(ws)

    @app.post("/api/confirm/respond")
    async def api_confirm_respond(body: dict):
        """REST fallback for confirmation modal."""
        from confirmation_bridge import respond as confirm_respond
        req_id = body.get("id", "").strip()
        if not req_id:
            return {"ok": False, "error": "Chybí id"}
        ok = confirm_respond(req_id, bool(body.get("approved")))
        return {"ok": ok}


