"""
JARVIS Skill — Computer Control MCP
Ovládání celého počítače přes computer-control-mcp (AB498).
Nástroje: screenshot, OCR, klikání, psaní, okna, klávesnice.

Příkazy:
  „screenshot"                     → snímek obrazovky + uložení na plochu
  „udělej screenshot"              → totéž
  „klikni na 500 300"              → klik na souřadnice x=500 y=300
  „klikni doprostřed"              → klik na střed obrazovky
  „napiš Hello World"              → simulace klávesnice (type_text)
  „stiskni Ctrl+C"                 → klávesová zkratka
  „seznam oken"                    → všechna otevřená okna
  „přepni na okno Chrome"          → aktivuje okno podle názvu
  „velikost obrazovky"             → rozlišení monitoru
  „přesuň myš na 100 200"         → pohyb myši
  „přečti obrazovku"               → OCR textu z obrazovky
"""

from __future__ import annotations

import logging
import os
import re
import base64
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

_bridge = None


def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from mcp_bridge import get_mcp_bridge
            _bridge = get_mcp_bridge()
        except Exception as e:
            logger.warning(f"computer-control bridge nedostupný: {e}")
    return _bridge


def _call(tool: str, args: dict) -> str:
    b = _get_bridge()
    if not b:
        return "Computer Control MCP není dostupný."
    return b.call_tool("computer-control", tool, args) or "Žádný výsledek."


def _save_screenshot(b64_data: str) -> str:
    """Uloží base64 PNG na plochu, vrátí cestu."""
    try:
        plocha = Path.home() / "Plocha"
        if not plocha.exists():
            plocha = Path.home() / "Desktop"
        if not plocha.exists():
            plocha = Path.home()
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = plocha / f"screenshot_{ts}.png"
        # Odstraň data URI prefix pokud přítomen
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        path.write_bytes(base64.b64decode(b64_data))
        return str(path)
    except Exception as e:
        return f"(nelze uložit: {e})"


# ── Regex patterny ──────────────────────────────────

_SCREENSHOT_RE = re.compile(
    r"\b(screenshot|sni?mek\s+obrazovky|udelej\s+screenshot|vyfot\s+obrazovku|printscreen)\b",
    re.IGNORECASE,
)
_CLICK_COORD_RE = re.compile(
    r"\b(klikni|klik|click)\b.{0,20}?(\d{1,5})\s+(\d{1,5})",
    re.IGNORECASE,
)
_CLICK_CENTER_RE = re.compile(
    r"\b(klikni|klik)\s+(doprostred|na\s+stred|center)\b",
    re.IGNORECASE,
)
_TYPE_RE = re.compile(
    r"\b(napiste?|napis|type|zadej)\b\s+(.+)",
    re.IGNORECASE,
)
_KEYS_RE = re.compile(
    r"\b(stiskni|zmackni|press|klavesa)\b\s+(.+)",
    re.IGNORECASE,
)
_WINDOWS_RE = re.compile(
    r"\b(seznam\s+oken|vsechna\s+okna|list\s+windows|otevrena\s+okna)\b",
    re.IGNORECASE,
)
_ACTIVATE_RE = re.compile(
    r"\b(prepni\s+na\s+okno|aktivuj\s+okno|aktivuj)\b\s+(.+)",
    re.IGNORECASE,
)
_SCREEN_SIZE_RE = re.compile(
    r"\b(velikost\s+obrazovky|rozliseni|screen\s+size|rozlišení)\b",
    re.IGNORECASE,
)
_MOVE_MOUSE_RE = re.compile(
    r"\b(presun\s+mys|pohyb\s+mys|move\s+mouse)\b.{0,10}?(\d{1,5})\s+(\d{1,5})",
    re.IGNORECASE,
)
_OCR_RE = re.compile(
    r"\b(precti\s+obrazovku|ocr|precti\s+text\s+z\s+obrazovky|co\s+je\s+na\s+obrazovce)\b",
    re.IGNORECASE,
)


# ── Handlery ───────────────────────────────────────

def _handle_screenshot(text: str):
    if not _SCREENSHOT_RE.search(text):
        return None, None
    result = _call("take_screenshot", {})
    # Výsledek je base64 PNG
    if result and len(result) > 100 and not result.startswith("Chyba"):
        path = _save_screenshot(result)
        return f"Screenshot uložen: {path}", {"action": "answer", "params": {}}
    return f"Screenshot: {result[:200]}", {"action": "answer", "params": {}}


def _handle_click_coord(text: str):
    m = _CLICK_COORD_RE.search(text)
    if not m:
        return None, None
    x, y = int(m.group(2)), int(m.group(3))
    result = _call("click_screen", {"x": x, "y": y, "button": "left"})
    return f"Kliknuto na [{x}, {y}]: {result}", {"action": "answer", "params": {}}


def _handle_click_center(text: str):
    if not _CLICK_CENTER_RE.search(text):
        return None, None
    size = _call("get_screen_size", {})
    try:
        import json
        d = json.loads(size)
        x, y = d["width"] // 2, d["height"] // 2
    except Exception:
        x, y = 960, 540
    result = _call("click_screen", {"x": x, "y": y, "button": "left"})
    return f"Kliknuto na střed [{x}, {y}].", {"action": "answer", "params": {}}


def _handle_type(text: str):
    m = _TYPE_RE.search(text)
    if not m:
        return None, None
    typed = m.group(2).strip()
    result = _call("type_text", {"text": typed})
    return f"Napsáno: {typed}", {"action": "answer", "params": {}}


def _handle_keys(text: str):
    m = _KEYS_RE.search(text)
    if not m:
        return None, None
    keys_raw = m.group(2).strip()
    # "Ctrl+C" → ["ctrl", "c"]
    keys = [k.strip().lower() for k in re.split(r"[+\s]+", keys_raw) if k.strip()]
    result = _call("press_keys", {"keys": keys})
    return f"Stisknuto: {'+'.join(keys)}", {"action": "answer", "params": {}}


def _handle_windows(text: str):
    if not _WINDOWS_RE.search(text):
        return None, None
    result = _call("list_windows", {})
    if not result or result.startswith("Chyba"):
        return f"Chyba: {result}", {"action": "answer", "params": {}}
    # Zkrať výstup — max 10 oken
    lines = result.strip().split("\n")
    titles = [l for l in lines if '"title"' in l][:10]
    summary = "\n".join(t.replace('"title":', '').replace('"', '').strip() for t in titles)
    return f"Otevřená okna:\n{summary}", {"action": "answer", "params": {}}


def _handle_activate(text: str):
    m = _ACTIVATE_RE.search(text)
    if not m:
        return None, None
    title = m.group(2).strip()
    result = _call("activate_window", {"title_pattern": title})
    return f"Přepnuto na: {title}", {"action": "answer", "params": {}}


def _handle_screen_size(text: str):
    if not _SCREEN_SIZE_RE.search(text):
        return None, None
    result = _call("get_screen_size", {})
    return f"Rozlišení obrazovky: {result}", {"action": "answer", "params": {}}


def _handle_move_mouse(text: str):
    m = _MOVE_MOUSE_RE.search(text)
    if not m:
        return None, None
    x, y = int(m.group(2)), int(m.group(3))
    result = _call("move_mouse", {"x": x, "y": y})
    return f"Myš přesunuta na [{x}, {y}].", {"action": "answer", "params": {}}


def _handle_ocr(text: str):
    if not _OCR_RE.search(text):
        return None, None
    result = _call("take_screenshot_with_ocr", {})
    if not result or result.startswith("Chyba"):
        return f"OCR chyba: {result}", {"action": "answer", "params": {}}
    return f"Text na obrazovce:\n{result[:1000]}", {"action": "answer", "params": {}}


# ── Exporty ────────────────────────────────────────

def get_routes():
    return [
        {"pattern": _SCREENSHOT_RE,  "handler": _handle_screenshot},
        {"pattern": _CLICK_COORD_RE, "handler": _handle_click_coord},
        {"pattern": _CLICK_CENTER_RE,"handler": _handle_click_center},
        {"pattern": _TYPE_RE,        "handler": _handle_type},
        {"pattern": _KEYS_RE,        "handler": _handle_keys},
        {"pattern": _WINDOWS_RE,     "handler": _handle_windows},
        {"pattern": _ACTIVATE_RE,    "handler": _handle_activate},
        {"pattern": _SCREEN_SIZE_RE, "handler": _handle_screen_size},
        {"pattern": _MOVE_MOUSE_RE,  "handler": _handle_move_mouse},
        {"pattern": _OCR_RE,         "handler": _handle_ocr},
    ]


def get_actions():
    return {}
