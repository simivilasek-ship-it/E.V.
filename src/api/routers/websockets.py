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


async def _stream_tts(
    ws: WebSocket,
    text: str,
    voice: str,
    cancel: asyncio.Event,
) -> None:
    """Stream Edge-TTS audio jako binary frames do prohlížeče."""
    if not text or len(text) > 800:
        text = (text[:800] + "…") if len(text) > 800 else text
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await ws.send_text(json.dumps({"type": "tts_start"}))
        async for chunk in communicate.stream():
            if cancel.is_set():
                return
            if chunk["type"] == "audio":
                await ws.send_bytes(chunk["data"])
        if not cancel.is_set():
            await ws.send_text(json.dumps({"type": "tts_end"}))
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.debug(f"ws_audio TTS skip: {e}")
        if not cancel.is_set():
            await ws.send_text(json.dumps({"type": "tts_end"}))


def _pcm_has_speech(pcm: bytes, vad) -> bool:
    """Return True if any 30 ms frame in pcm contains speech."""
    if not pcm or vad is None:
        return False
    frame_bytes = int(16000 * 0.03) * 2
    for i in range(0, len(pcm) - frame_bytes + 1, frame_bytes):
        if vad.is_speech(pcm[i:i + frame_bytes]):
            return True
    return False


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
        """Duplex audio — PCM16 mono 16kHz → VAD → STT → chat → TTS stream."""
        await ws.accept()

        try:
            from config import CONFIG
            if not bool(CONFIG.get("audio_ws_enabled", False)):
                await ws.send_text(json.dumps({"type": "error", "data": "audio_ws_enabled is false"}))
                await ws.close()
                return
        except Exception:
            CONFIG = {}

        vad_filter = None
        transcriber = None
        try:
            from whisper_live import VADFilter, WhisperTranscriber, pcm_to_wav
            vad_filter = VADFilter()
            transcriber = WhisperTranscriber(CONFIG)
            if not transcriber.available:
                transcriber = None
        except Exception as e:
            logger.debug(f"ws_audio STT init: {e}")

        bus = None
        try:
            from event_bus import get_event_bus, EventType
            bus = get_event_bus()
        except Exception:
            bus = None

        loop = asyncio.get_event_loop()
        voice = CONFIG.get("tts_voice", "cs-CZ-AntoninNeural")
        barge_in = bool(CONFIG.get("duplex_barge_in", True))

        barge_vad = None
        if barge_in:
            try:
                from src.audio.vad import get_vad
                barge_vad = get_vad(CONFIG)
            except Exception:
                barge_vad = None

        current_tts_task: asyncio.Task | None = None
        tts_cancel = asyncio.Event()

        async def _cancel_tts(*, notify: bool = True) -> None:
            nonlocal current_tts_task
            tts_cancel.set()
            task = current_tts_task
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            current_tts_task = None
            if notify:
                try:
                    await ws.send_text(json.dumps({"type": "tts_cancel"}))
                except Exception:
                    pass

        async def _run_tts(text: str) -> None:
            nonlocal current_tts_task
            try:
                await _stream_tts(ws, text, voice, tts_cancel)
            except asyncio.CancelledError:
                pass
            finally:
                if current_tts_task is asyncio.current_task():
                    current_tts_task = None

        def _start_tts(text: str) -> None:
            nonlocal current_tts_task
            if current_tts_task and not current_tts_task.done():
                tts_cancel.set()
                current_tts_task.cancel()
            tts_cancel.clear()
            current_tts_task = asyncio.create_task(_run_tts(text))

        async def _handle_utterance(pcm: bytes) -> None:
            if not pcm or not transcriber:
                return
            try:
                from whisper_live import pcm_to_wav
                wav = pcm_to_wav(pcm)
                text = await loop.run_in_executor(None, lambda: transcriber.transcribe(wav))
                if not text or len(text.strip()) < 2:
                    return
                await ws.send_text(json.dumps({"type": "transcript", "text": text.strip()}))

                try:
                    from src.api.runtime import process_chat
                    response = await loop.run_in_executor(
                        None, lambda: process_chat(text.strip()),
                    )
                except Exception as ex:
                    response = f"Chyba: {ex}"

                if response:
                    await ws.send_text(json.dumps({"type": "response", "text": response}))
                    if CONFIG.get("audio_ws_tts", True):
                        _start_tts(response)
            except Exception as e:
                logger.warning(f"ws_audio utterance: {e}")
                await ws.send_text(json.dumps({"type": "error", "data": str(e)}))

        try:
            await ws.send_text(json.dumps({"type": "ready"}))
            while True:
                raw = await ws.receive()
                if raw.get("type") == "websocket.disconnect":
                    break

                if "text" in raw and raw["text"]:
                    try:
                        msg = json.loads(raw["text"])
                        if msg.get("type") == "interrupt":
                            if barge_in:
                                await _cancel_tts()
                        elif msg.get("type") == "stop":
                            await _cancel_tts(notify=False)
                            if vad_filter:
                                tail = vad_filter.flush()
                                if tail:
                                    await _handle_utterance(tail)
                            break
                    except json.JSONDecodeError:
                        pass
                    continue

                frame = raw.get("bytes") or b""
                if not frame:
                    continue

                if (
                    barge_in
                    and current_tts_task
                    and not current_tts_task.done()
                    and _pcm_has_speech(frame, barge_vad)
                ):
                    await _cancel_tts()

                if bus:
                    try:
                        bus.emit(EventType.AUDIO_SPEECH, {"ts": time.time(), "n": len(frame)},
                                 source="ws_audio")
                    except Exception:
                        pass

                if vad_filter is not None:
                    utterance = vad_filter.feed(frame)
                    if utterance:
                        await _handle_utterance(utterance)
                else:
                    await ws.send_text(json.dumps({"type": "vad", "speech": True}))

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

