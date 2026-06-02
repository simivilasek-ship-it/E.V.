"""
JARVIS Context Orchestrator v2
Sbírá kontext prostředí a vkládá ho do system promptu.
Kontext = aktivní okno + seznam oken + clipboard + systém + čas.
"""

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ignorovaná okna (panel, plocha...) při sestavování seznamu
_IGNORE_NAMES = {
    "horní panel", "spodní panel", "pracovní plocha", "desktop",
    "top panel", "bottom panel", "panel",
}


class ContextOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self._cache: dict = {}
        self._cache_ttl: float = 4.0  # sekundy
        self._last_update: float = 0

    def get_context(self) -> str:
        """Vrátí naformátovaný kontext prostředí pro system prompt."""
        now = time.time()
        if now - self._last_update < self._cache_ttl:
            return self._cache.get("formatted", "")

        ctx: dict = {}
        ctx["time"]      = self._get_time()
        ctx["active"]    = self._get_active_window()
        ctx["windows"]   = self._get_open_windows()
        ctx["clipboard"] = self._get_clipboard()
        ctx["system"]    = self._get_system_quick()

        # Emit event if active window changed
        try:
            from event_bus import get_event_bus, EventType
            prev_active = self._cache.get("data", {}).get("active") if self._cache else None
            if ctx["active"] and ctx["active"] != prev_active:
                try:
                    get_event_bus().emit(EventType.ACTIVE_WINDOW_CHANGED, {"title": ctx["active"]})
                except Exception:
                    pass
        except Exception:
            pass

        formatted = self._format(ctx)
        self._cache = {"data": ctx, "formatted": formatted}
        self._last_update = now
        return formatted

    # ── Čas ───────────────────────────────────────────

    def _get_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M, %A %d.%m.%Y")

    # ── Okna (ewmh → xdotool → wmctrl → ps) ──────────

    def _decode_wm_name(self, raw) -> str:
        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace").strip()
        return str(raw or "").strip()

    def _get_active_window(self) -> str:
        # 1. ewmh
        for disp in [os.environ.get("DISPLAY", ""), ":0.0", ":0", ":1"]:
            if not disp:
                continue
            try:
                from Xlib import display as _xlib_display
                import ewmh as _ewmh
                d = _xlib_display.Display(disp)
                e = _ewmh.EWMH(_display=d)
                w = e.getActiveWindow()
                if w:
                    name = self._decode_wm_name(e.getWmName(w))
                    if name:
                        return name[:100]
            except Exception:
                pass

        # 2. xdotool
        try:
            import subprocess
            r = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=1,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            )
            if r.returncode == 0:
                return r.stdout.strip()[:100]
        except Exception:
            pass

        # 3. wmctrl
        try:
            import subprocess
            r = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=1,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        return parts[3][:100]
        except Exception:
            pass

        return ""

    def _get_open_windows(self) -> list[str]:
        """Vrátí seznam názvů otevřených oken (bez systémových panelů)."""
        names: list[str] = []

        # 1. ewmh
        for disp in [os.environ.get("DISPLAY", ""), ":0.0", ":0", ":1"]:
            if not disp:
                continue
            try:
                from Xlib import display as _xlib_display
                import ewmh as _ewmh
                d = _xlib_display.Display(disp)
                e = _ewmh.EWMH(_display=d)
                for w in e.getClientList():
                    try:
                        name = self._decode_wm_name(e.getWmName(w))
                        if name and name.lower() not in _IGNORE_NAMES:
                            names.append(name[:80])
                    except Exception:
                        pass
                if names:
                    return names
            except Exception:
                pass

        # 2. wmctrl -l fallback
        try:
            import subprocess
            r = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=1,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        name = parts[3].strip()
                        if name.lower() not in _IGNORE_NAMES:
                            names.append(name[:80])
        except Exception:
            pass

        return names

    # ── Clipboard ─────────────────────────────────────

    def _get_clipboard(self) -> str:
        try:
            import subprocess
            r = subprocess.run(
                ["xclip", "-o", "-selection", "clipboard"],
                capture_output=True, text=True, timeout=1,
                env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            )
            if r.returncode == 0:
                text = r.stdout.strip()
                if text and len(text) < 500:
                    return text[:200]
        except Exception:
            pass
        try:
            import pyperclip
            text = pyperclip.paste()
            if text and len(text) < 500:
                return text[:200]
        except Exception:
            pass
        return ""

    # ── Systém ────────────────────────────────────────

    def _get_system_quick(self) -> dict:
        try:
            import psutil
            return {
                "cpu": round(psutil.cpu_percent(interval=0), 1),
                "ram": round(psutil.virtual_memory().percent, 1),
            }
        except Exception:
            return {}

    # ── Formátování ───────────────────────────────────

    def _format(self, ctx: dict) -> str:
        parts = [f"Aktuální čas: {ctx['time']}"]

        if ctx.get("active"):
            parts.append(f"Aktivní okno: {ctx['active']}")

        windows = [w for w in ctx.get("windows", []) if w != ctx.get("active")]
        if windows:
            # Deduplikuj a zobraz max 8 oken
            seen: set[str] = set()
            unique = []
            for w in windows:
                if w not in seen:
                    seen.add(w)
                    unique.append(w)
            shown = unique[:8]
            parts.append("Otevřená okna: " + ", ".join(shown))

        if ctx.get("clipboard"):
            clip = ctx["clipboard"][:120]
            parts.append(f"Schránka: {clip}{'…' if len(ctx['clipboard']) > 120 else ''}")

        sys_info = ctx.get("system", {})
        if sys_info:
            parts.append(f"Systém: CPU {sys_info.get('cpu', 0)}%, RAM {sys_info.get('ram', 0)}%")

        return "\n".join(parts)


_orchestrator: Optional["ContextOrchestrator"] = None


def get_context_orchestrator(config: dict = None) -> "ContextOrchestrator":
    global _orchestrator
    if _orchestrator is None:
        from config import CONFIG
        _orchestrator = ContextOrchestrator(config or CONFIG)
    return _orchestrator
