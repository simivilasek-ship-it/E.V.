"""Auto-migrated from dashboard.py — vision_post routes."""
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

    @app.post("/api/vision")
    async def vision_query(body: dict):
        """Popis obrázku pomocí multimodálního LLM (llava)."""
        from pathlib import Path as _Path
        prompt     = body.get("prompt", "Popiš obrázek.")
        image_path = body.get("image_path", "")
        model      = body.get("model", "llava:7b")
        if not _Path(image_path).exists():
            return {"error": f"Soubor nenalezen: {image_path}"}
        try:
            from llm import ask_vision
            from config import CONFIG
            url    = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            answer = ask_vision(prompt, image_path, model, url)
            return {"answer": answer}
        except Exception as e:
            return {"error": str(e)}


