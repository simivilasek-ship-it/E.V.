"""
JARVIS v3.0 — Web Server
FastAPI + WebSocket backend s Three.js frontend
"""

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import uvicorn
import webbrowser

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

# Import modulů
from config import CONFIG, save_config
from llm import LLMEngine
from commands import CommandExecutor

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────
#  INICIALIZACE
# ──────────────────────────────────────────────────────

app  = FastAPI(title="JARVIS v3.0", docs_url=None, redoc_url=None)
llm  = LLMEngine(CONFIG)
cmds = CommandExecutor(CONFIG)

# TTS — edge-tts přes Python
_TTS_VOICE = CONFIG.get("tts_voice", "cs-CZ-AntoninNeural")
_TMP       = tempfile.gettempdir()

# Event loop reference pro thread-safe broadcast
_loop: asyncio.AbstractEventLoop = None

# Připojení WebSocket klientů
_clients: set[WebSocket] = set()


# ──────────────────────────────────────────────────────
#  BROADCAST HELPERS
# ──────────────────────────────────────────────────────

async def _broadcast(data: dict):
    """Odešle zprávu všem připojeným klientům"""
    msg  = json.dumps(data, ensure_ascii=False)
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def broadcast(data: dict):
    """Thread-safe broadcast z libovolného vlákna"""
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(data), _loop)


def set_state(state: str):
    """Broadcast změny stavu ORBu"""
    broadcast({"type": "state", "state": state})


# ──────────────────────────────────────────────────────
#  TTS — generování audia
# ──────────────────────────────────────────────────────

async def _tts_generate(text: str) -> str | None:
    """Generuje TTS audio přes edge-tts, vrátí URL nebo None"""
    try:
        import edge_tts
        fname = f"tts_{int(time.time() * 1000)}.mp3"
        path  = os.path.join(_TMP, fname)
        comm  = edge_tts.Communicate(text, _TTS_VOICE)
        await comm.save(path)
        return f"/audio/{fname}"
    except Exception as e:
        logger.warning(f"TTS chyba: {e}")
        return None


# ──────────────────────────────────────────────────────
#  ZPRACOVÁNÍ PŘÍKAZU
# ──────────────────────────────────────────────────────

def _process_command(text: str):
    """
    Zpracuje příkaz:
    1. Streamuje LLM odpověď → posílá chunky klientům
    2. Detekuje COMMAND → vykoná akci
    3. Generuje TTS audio → pošle URL klientům
    """
    set_state("thinking")
    broadcast({"type": "message", "role": "user", "text": text})

    full_response = ""
    sentence_buf  = ""
    header_sent   = False
    is_command    = False

    # ── Streamování ──────────────────────────────────
    for chunk in llm.stream_ask(text):
        full_response += chunk

        if "COMMAND:" in full_response:
            is_command = True
            break

        sentence_buf += chunk

        # Pošli chunk klientům průběžně
        if not header_sent and sentence_buf.strip():
            header_sent = True
            broadcast({"type": "stream_start"})

        # Věty → TTS průběžně
        while True:
            m = re.search(r"[.!?][\s\n]", sentence_buf)
            if not m:
                break
            sentence     = sentence_buf[: m.end()].strip()
            sentence_buf = sentence_buf[m.end():]

            if sentence:
                broadcast({"type": "stream_chunk", "text": sentence})
                has_code = any(k in sentence for k in ("```", "def ", "import "))
                if not has_code and len(sentence) < 300:
                    set_state("speaking")
                    audio_url = asyncio.run_coroutine_threadsafe(
                        _tts_generate(sentence), _loop
                    ).result(timeout=15)
                    if audio_url:
                        broadcast({"type": "audio", "url": audio_url})
                    set_state("thinking")

    # ── Dočerpej stream ───────────────────────────────
    if is_command:
        for chunk in llm.drain_stream():
            full_response += chunk

    # ── Parsuj výsledek ───────────────────────────────
    message, action_data = llm._parse_response(full_response)

    if sentence_buf.strip():
        broadcast({"type": "stream_chunk", "text": sentence_buf.strip()})

    if header_sent:
        broadcast({"type": "stream_end"})

    # ── Příkaz nebo AI odpověď ────────────────────────
    action = action_data.get("action", "answer")
    params = action_data.get("params", {})

    if not header_sent:
        # COMMAND odpověď — zobraz zprávu
        display_msg = action_data.get("message") or llm._default_message(action, "")
        if display_msg:
            broadcast({"type": "message", "role": "jarvis", "text": display_msg})
            has_code = any(k in display_msg for k in ("```", "def ", "import "))
            if not has_code and len(display_msg) < 300:
                set_state("speaking")
                audio_url = asyncio.run_coroutine_threadsafe(
                    _tts_generate(display_msg), _loop
                ).result(timeout=15)
                if audio_url:
                    broadcast({"type": "audio", "url": audio_url})

    if action not in ("answer", ""):
        broadcast({"type": "action", "action": action, "params": params})
        result = cmds.execute(action, params)
        if result and result != "ok":
            broadcast({"type": "result", "text": result})

    set_state("idle")


# ──────────────────────────────────────────────────────
#  WEBSOCKET ENDPOINT
# ──────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    await websocket.send_text(json.dumps({"type": "state", "state": "idle"}))
    await websocket.send_text(json.dumps({
        "type": "info",
        "model": CONFIG["ollama_model"],
        "voice": _TTS_VOICE,
    }))

    try:
        while True:
            raw  = await websocket.receive_text()
            data = json.loads(raw)

            if data["type"] == "message":
                threading.Thread(
                    target=_process_command,
                    args=(data["text"],),
                    daemon=True,
                ).start()

            elif data["type"] == "clear":
                llm.clear_history()
                await websocket.send_text(json.dumps({"type": "cleared"}))

            elif data["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception as e:
        logger.error(f"WS chyba: {e}")
        _clients.discard(websocket)


# ──────────────────────────────────────────────────────
#  HTTP ENDPOINTS
# ──────────────────────────────────────────────────────

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Servíruje TTS audio soubory"""
    # Bezpečnostní kontrola — pouze mp3 z tmp
    if not filename.endswith(".mp3") or "/" in filename:
        return Response(status_code=403)
    path = os.path.join(_TMP, filename)
    if not os.path.exists(path):
        return Response(status_code=404)
    return FileResponse(path, media_type="audio/mpeg")


@app.get("/api/status")
async def status():
    return {
        "model":     CONFIG["ollama_model"],
        "ollama_ok": llm.is_available(),
        "voice":     _TTS_VOICE,
    }


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


# Statické soubory frontendu
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")


# ──────────────────────────────────────────────────────
#  STARTUP
# ──────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    global _loop
    _loop = asyncio.get_event_loop()
    logger.info("JARVIS v3.0 server spuštěn")

    # Ollama check
    if llm.is_available():
        logger.info(f"Ollama [{CONFIG['ollama_model']}] OK")
    else:
        logger.warning("Ollama není dostupná — spusť: ollama serve")

    # Otevři browser po 1s
    def open_browser():
        time.sleep(1.0)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()


# ──────────────────────────────────────────────────────
#  SPUŠTĚNÍ
# ──────────────────────────────────────────────────────

def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("jarvis.log", encoding="utf-8"),
        ],
    )


if __name__ == "__main__":
    _setup_logging()
    print("\n  JARVIS v3.0 — spouštím server na http://localhost:8000\n")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        reload=False,
    )
