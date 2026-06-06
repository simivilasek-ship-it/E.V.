"""
Vision Sandbox — dry-run režim pro computer-use akce.

Agent nejdřív ukáže, kam by klikl (screenshot + souřadnice), a teprve po
schválení provede skutečný klik.
"""
from __future__ import annotations

import base64
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PREVIEW_TTL_S = 300


@dataclass
class SandboxPreview:
    id: str
    target: str
    x: int
    y: int
    method: str
    matched_text: str
    screenshot_b64: str
    screen_w: int
    screen_h: int
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_lock = threading.Lock()
_previews: Dict[str, SandboxPreview] = {}


def sandbox_enabled() -> bool:
    try:
        from config import CONFIG
        return bool(CONFIG.get("vision_sandbox_enabled", True))
    except Exception:
        return True


def auto_execute() -> bool:
    try:
        from config import CONFIG
        return bool(CONFIG.get("vision_sandbox_auto_execute", False))
    except Exception:
        return False


def _annotate_screenshot(path: str, x: int, y: int) -> tuple[str, int, int]:
    """Vrátí base64 JPEG s vyznačeným cílem kliknutí."""
    try:
        from PIL import Image, ImageDraw
        from io import BytesIO

        img = Image.open(path)
        w, h = img.size
        draw = ImageDraw.Draw(img)
        r = max(12, min(w, h) // 80)
        draw.ellipse((x - r, y - r, x + r, y + r), outline="#00e5ff", width=4)
        draw.line((x - r * 2, y, x + r * 2, y), fill="#ff4466", width=2)
        draw.line((x, y - r * 2, x, y + r * 2), fill="#ff4466", width=2)
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=82)
        return base64.b64encode(buf.getvalue()).decode("ascii"), w, h
    except Exception as e:
        logger.debug("annotate screenshot failed: %s", e)
        try:
            raw = Path(path).read_bytes()
            return base64.b64encode(raw).decode("ascii"), 0, 0
        except Exception:
            return "", 0, 0


def _purge_expired() -> None:
    now = time.time()
    with _lock:
        dead = [k for k, v in _previews.items() if now - v.created_at > PREVIEW_TTL_S]
        for k in dead:
            del _previews[k]


def preview_click(target: str) -> Dict[str, Any]:
    """Najde cíl a vytvoří dry-run náhled bez kliknutí."""
    target = (target or "").strip()
    if not target:
        return {"found": False, "error": "Prázdný cíl"}

    _purge_expired()
    shot_path: Optional[str] = None
    try:
        from vision_v2 import get_planner

        action, shot_path = get_planner().locate(target)
        if not action.found:
            return {"found": False, "error": action.error or "Element nenalezen"}
        if not shot_path:
            return {"found": False, "error": "Screenshot selhal"}

        b64, sw, sh = _annotate_screenshot(shot_path, action.x, action.y)
        preview_id = uuid.uuid4().hex[:12]
        preview = SandboxPreview(
            id=preview_id,
            target=target,
            x=action.x,
            y=action.y,
            method=action.method,
            matched_text=action.matched_text,
            screenshot_b64=b64,
            screen_w=sw,
            screen_h=sh,
            created_at=time.time(),
        )
        with _lock:
            _previews[preview_id] = preview

        logger.info("Vision sandbox preview %s @ (%d,%d) target=%r", preview_id, action.x, action.y, target)
        return {"found": True, **preview.to_dict()}
    except Exception as e:
        logger.error("preview_click failed: %s", e)
        return {"found": False, "error": str(e)}
    finally:
        if shot_path:
            try:
                Path(shot_path).unlink(missing_ok=True)
            except Exception:
                pass


def get_preview(preview_id: str) -> Optional[Dict[str, Any]]:
    _purge_expired()
    with _lock:
        p = _previews.get(preview_id)
        return p.to_dict() if p else None


def execute_preview(preview_id: str, approved: bool = True) -> Dict[str, Any]:
    """Provede nebo zruší dříve vytvořený náhled."""
    _purge_expired()
    with _lock:
        preview = _previews.pop(preview_id, None)
    if not preview:
        return {"ok": False, "error": "Náhled vypršel nebo neexistuje"}

    if not approved:
        return {"ok": True, "cancelled": True, "preview_id": preview_id}

    try:
        import pyautogui

        pyautogui.moveTo(preview.x, preview.y, duration=0.25)
        pyautogui.click(preview.x, preview.y)
        logger.info("Vision sandbox executed %s @ (%d,%d)", preview_id, preview.x, preview.y)
        return {
            "ok": True,
            "executed": True,
            "preview_id": preview_id,
            "x": preview.x,
            "y": preview.y,
            "target": preview.target,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "preview_id": preview_id}


def click_with_sandbox(target: str, force: bool = False) -> Dict[str, Any]:
    """Jednotný vstup pro agenty — sandbox nebo přímý klik."""
    if not force and sandbox_enabled():
        if auto_execute():
            preview = preview_click(target)
            if not preview.get("found"):
                return {"ok": False, "sandbox": True, **preview}
            return execute_preview(preview["id"], approved=True)

        preview = preview_click(target)
        if not preview.get("found"):
            return {"ok": False, "sandbox": True, **preview}
        return {
            "ok": False,
            "sandbox": True,
            "requires_approval": True,
            "preview_id": preview["id"],
            "x": preview["x"],
            "y": preview["y"],
            "method": preview.get("method"),
            "message": (
                f"SANDBOX: klik na ({preview['x']},{preview['y']}) — "
                f"schval preview_id={preview['id']} v UI nebo /api/vision/sandbox/execute"
            ),
        }

    try:
        from vision_computer_use import get_vision_agent

        result = get_vision_agent().click(target, force=True)
        return {
            "ok": result.success,
            "executed": result.success,
            "x": result.x,
            "y": result.y,
            "error": result.error,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
