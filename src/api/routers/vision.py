"""Auto-migrated from dashboard.py — vision routes."""
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

    # ── Vision v2 API ─────────────────────────────────

    @app.get("/api/vision/analyze")
    async def vision_analyze():
        """Pořídí screenshot, spustí OCR+UI analýzu, vrátí JSON."""
        try:
            from vision_v2 import VisionOCRPipeline
            import asyncio
            pipeline = VisionOCRPipeline()
            if not pipeline.available:
                return {"error": "OCR pipeline nedostupná (pip install pytesseract opencv-python)"}
            result = await asyncio.get_event_loop().run_in_executor(
                None, pipeline.analyze)
            return {
                "ocr_text":        result.ocr_text,
                "active_app":      result.active_app,
                "ui_elements":     [{"role": e.role, "name": e.name, "x": e.bbox[0], "y": e.bbox[1]} for e in result.ui_elements],
                "clickable_count": len(result.clickable_regions),
            }
        except Exception as e:
            return {"error": str(e)}


