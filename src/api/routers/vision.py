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

    @app.post("/api/vision/sandbox/preview")
    async def vision_sandbox_preview(body: dict):
        """Dry-run: ukáže kam by agent klikl, bez provedení akce."""
        import asyncio
        target = (body.get("target") or body.get("description") or "").strip()
        if not target:
            return {"found": False, "error": "Chybí target"}
        try:
            from vision_sandbox import preview_click
            return await asyncio.get_event_loop().run_in_executor(None, lambda: preview_click(target))
        except Exception as e:
            return {"found": False, "error": str(e)}

    @app.get("/api/vision/sandbox/{preview_id}")
    async def vision_sandbox_get(preview_id: str):
        try:
            from vision_sandbox import get_preview
            data = get_preview(preview_id)
            return data if data else {"error": "Náhled nenalezen"}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/vision/sandbox/execute")
    async def vision_sandbox_execute(body: dict):
        """Schválí nebo zamítne dříve vytvořený sandbox náhled."""
        import asyncio
        preview_id = (body.get("preview_id") or body.get("id") or "").strip()
        if not preview_id:
            return {"ok": False, "error": "Chybí preview_id"}
        approved = bool(body.get("approved", True))
        try:
            from vision_sandbox import execute_preview
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: execute_preview(preview_id, approved=approved))
        except Exception as e:
            return {"ok": False, "error": str(e)}


