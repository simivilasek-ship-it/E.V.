"""
JARVIS v3.0 — REST API
Jednoduché FastAPI rozhraní pro vzdálené ovládání JARVIS.
Spuštění: python api.py  (port 8001)
"""

from __future__ import annotations
import threading
import logging
from typing import Optional
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from config import CONFIG
from llm import LLMEngine, ask_vision
from commands import CommandExecutor

logger = logging.getLogger(__name__)


# ── Modely požadavků ──────────────────────────────────

class ChatRequest(BaseModel):
    text: str
    model: Optional[str] = None

class CommandRequest(BaseModel):
    action: str
    params: dict = {}

class VisionRequest(BaseModel):
    prompt: str
    image_path: str
    model: str = "llava:7b"


# ── Inicializace ──────────────────────────────────────

if HAS_FASTAPI:
    app = FastAPI(
        title="JARVIS API",
        description="REST API pro lokální AI asistenta JARVIS",
        version="3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _llm  = LLMEngine(CONFIG)
    _cmds = CommandExecutor(CONFIG)

    @app.get("/")
    def root():
        return {"status": "ok", "version": "3.0", "model": _llm.model}

    @app.get("/status")
    def status():
        return {
            "ollama": _llm.is_available(),
            "model":  _llm.model,
        }

    @app.get("/models")
    def models():
        import requests as _req
        try:
            r = _req.get(_llm.url.replace("/api/chat", "/api/tags"), timeout=4)
            if r.status_code == 200:
                return {"models": [m["name"] for m in r.json().get("models", [])]}
        except Exception:
            pass
        return {"models": []}

    @app.post("/chat")
    def chat(req: ChatRequest):
        if req.model and req.model != _llm.model:
            # Vytvoř jednorázový engine s jiným modelem místo mutace sdíleného stavu
            from llm import LLMEngine as _LLMEng
            import copy as _copy
            cfg = _copy.copy(_llm.config)
            cfg["ollama_model"] = req.model
            engine = _LLMEng(cfg, memory=_llm.memory)
            msg, action = engine.ask(req.text)
        else:
            msg, action = _llm.ask(req.text)
        return {"message": msg, "action": action}

    @app.post("/command")
    def command(req: CommandRequest):
        result = _cmds.execute(req.action, req.params)
        return {"result": result}

    @app.post("/vision")
    def vision(req: VisionRequest):
        if not Path(req.image_path).exists():
            raise HTTPException(status_code=404, detail="Soubor nenalezen")
        answer = ask_vision(req.prompt, req.image_path, req.model, _llm.url)
        return {"answer": answer}

    @app.delete("/history")
    def clear_history():
        _llm.clear_history()
        return {"ok": True}


def run_api(host: str = "0.0.0.0", port: int = 8001):
    if not HAS_FASTAPI:
        logger.warning("FastAPI není nainstalováno: pip install fastapi uvicorn")
        return
    uvicorn.run(app, host=host, port=port, log_level="warning")


def run_api_background(port: int = 8001):
    """Spustí API server na pozadí."""
    t = threading.Thread(target=run_api, kwargs={"port": port}, daemon=True)
    t.start()
    logger.info(f"JARVIS API běží na http://localhost:{port}")
    return t


if __name__ == "__main__":
    print("JARVIS REST API — http://localhost:8001/docs")
    run_api()
