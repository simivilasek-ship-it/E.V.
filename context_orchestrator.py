"""
JARVIS Context Orchestrator
Sbírá kontext prostředí a vkládá ho do system promptu.
Kontext = aktivní okno + clipboard + systém + čas + nedávná aktivita.
"""

import time
from typing import Optional


class ContextOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self._cache: dict = {}
        self._cache_ttl: float = 5.0  # sekundy
        self._last_update: float = 0

    def get_context(self) -> str:
        """Vrátí naformátovaný kontext prostředí pro system prompt."""
        now = time.time()
        if now - self._last_update < self._cache_ttl:
            return self._cache.get("formatted", "")

        ctx = {}
        ctx["time"]      = self._get_time()
        ctx["window"]    = self._get_active_window()
        ctx["clipboard"] = self._get_clipboard()
        ctx["system"]    = self._get_system_quick()

        formatted = self._format(ctx)
        self._cache = {"data": ctx, "formatted": formatted}
        self._last_update = now
        return formatted

    def _get_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M, %A %d.%m.%Y")

    def _get_active_window(self) -> str:
        """Zjistí aktivní okno přes xdotool nebo wmctrl."""
        try:
            import subprocess
            r = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=1
            )
            if r.returncode == 0:
                return r.stdout.strip()[:80]
        except Exception:
            pass
        try:
            import subprocess
            r = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=1
            )
            if r.returncode == 0:
                lines = r.stdout.strip().split("\n")
                if lines:
                    return lines[0].split(None, 3)[-1][:80] if len(lines[0].split()) >= 4 else ""
        except Exception:
            pass
        return ""

    def _get_clipboard(self) -> str:
        """Přečte obsah clipboardu (max 200 znaků)."""
        try:
            import subprocess
            r = subprocess.run(
                ["xclip", "-o", "-selection", "clipboard"],
                capture_output=True, text=True, timeout=1
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

    def _get_system_quick(self) -> dict:
        """CPU, RAM rychle (bez interval čekání)."""
        try:
            import psutil
            return {
                "cpu": round(psutil.cpu_percent(interval=0), 1),
                "ram": round(psutil.virtual_memory().percent, 1),
            }
        except Exception:
            return {}

    def _format(self, ctx: dict) -> str:
        """Naformátuje kontext pro system prompt."""
        parts = [f"Aktuální čas: {ctx['time']}"]
        if ctx.get("window"):
            parts.append(f"Aktivní okno: {ctx['window']}")
        if ctx.get("clipboard"):
            parts.append(f"Obsah schránky: {ctx['clipboard'][:100]}{'...' if len(ctx['clipboard'])>100 else ''}")
        sys_info = ctx.get("system", {})
        if sys_info:
            parts.append(f"Systém: CPU {sys_info.get('cpu',0)}%, RAM {sys_info.get('ram',0)}%")
        return "\n".join(parts)


_orchestrator: Optional["ContextOrchestrator"] = None


def get_context_orchestrator(config: dict = None) -> "ContextOrchestrator":
    global _orchestrator
    if _orchestrator is None:
        from config import CONFIG
        _orchestrator = ContextOrchestrator(config or CONFIG)
    return _orchestrator
