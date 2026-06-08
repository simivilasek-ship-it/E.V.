"""
JARVIS Context Orchestrator v2
Sb�r� kontext prost?ed� a vkl�d� ho do system promptu.
Kontext = aktivn� okno + seznam oken + clipboard + syst�m + ?as.
"""

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ignorovan� okna (panel, plocha...) p?i sestavov�n� seznamu
_IGNORE_NAMES = {
    "horn� panel", "spodn� panel", "pracovn� plocha", "desktop",
    "top panel", "bottom panel", "panel",
}
_IGNORE_SUBSTR = (
    "ulo?it sn�mek", "save screenshot", "screenshot", "sn�mek obrazovky",
)


class ContextOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self._cache: dict = {}
        self._cache_ttl: float = 4.0  # sekundy
        self._last_update: float = 0

    def get_context(self) -> str:
        """Vr�t� naform�tovan� kontext prost?ed� pro system prompt."""
        now = time.time()
        if now - self._last_update < self._cache_ttl:
            return self._cache.get("formatted", "")

        ctx: dict = {}
        ctx["time"]      = self._get_time()
        ctx["active"]    = self._get_active_window()
        ctx["windows"]   = self._get_open_windows()
        ctx["clipboard"] = self._get_clipboard()
        ctx["system"]    = self._get_system_quick()
        ctx["workspace"] = self._get_workspace()
        ctx["activity"]  = self._get_recent_activity()

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

    def get_context_data(self) -> dict:
        """Strukturovan� data kontextu (po get_context refresh)."""
        self.get_context()
        return dict(self._cache.get("data", {}))

    # ?? ?as ???????????????????????????????????????????

    def _get_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M, %A %d.%m.%Y")

    # ?? Okna (ewmh ? xdotool ? wmctrl ? ps) ??????????

    def _decode_wm_name(self, raw) -> str:
        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace").strip()
        if isinstance(raw, (list, tuple)) and raw:
            return self._decode_wm_name(raw[0])
        return str(raw or "").strip()

    def _should_ignore_window(self, name: str) -> bool:
        low = name.lower().strip()
        if not low or low in _IGNORE_NAMES:
            return True
        return any(s in low for s in _IGNORE_SUBSTR)

    def _xlib_window_title(self, d, win_id: int) -> str:
        from Xlib import X

        try:
            win = d.create_resource_object("window", int(win_id))
            for atom in ("_NET_WM_NAME", "WM_NAME"):
                prop = win.get_full_property(d.intern_atom(atom), X.AnyPropertyType)
                if prop and prop.value:
                    title = self._decode_wm_name(prop.value)
                    if title:
                        return title[:100]
        except Exception:
            pass
        return ""

    def _xlib_desktop_windows(self) -> tuple[str, list[str]]:
        """?ist� Xlib EWMH fallback (bez bal�?ku ewmh)."""
        for disp in [os.environ.get("DISPLAY", ""), ":0.0", ":0", ":1"]:
            if not disp:
                continue
            try:
                from Xlib import display as _xlib_display, X

                d = _xlib_display.Display(disp)
                root = d.screen().root

                active = ""
                ap = root.get_full_property(d.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
                if ap and ap.value:
                    active = self._xlib_window_title(d, int(ap.value[0]))

                names: list[str] = []
                cp = root.get_full_property(d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
                if cp and cp.value:
                    for wid in cp.value:
                        title = self._xlib_window_title(d, int(wid))
                        if title and not self._should_ignore_window(title):
                            names.append(title[:80])

                if active or names:
                    return active, names
            except Exception:
                pass
        return "", []

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

        # 4. ?ist� Xlib (bez ewmh bal�?ku)
        active, _ = self._xlib_desktop_windows()
        if active:
            return active

        return ""

    def _get_open_windows(self) -> list[str]:
        """Vr�t� seznam n�zv? otev?en�ch oken (bez syst�mov�ch panel?)."""
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
                        if name and not self._should_ignore_window(name):
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
                        if not self._should_ignore_window(name):
                            names.append(name[:80])
        except Exception:
            pass

        # 3. ?ist� Xlib
        _, names = self._xlib_desktop_windows()
        if names:
            return names

        return names

    # ?? Clipboard ?????????????????????????????????????

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

    # ?? Syst�m ????????????????????????????????????????

    def _get_system_quick(self) -> dict:
        try:
            import platform
            import psutil
            import socket

            vm = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return {
                "hostname": socket.gethostname(),
                "os": f"{platform.system()} {platform.release()}",
                "cpu": round(psutil.cpu_percent(interval=0), 1),
                "ram": round(vm.percent, 1),
                "ram_used_gb": round(vm.used / 2**30, 1),
                "ram_total_gb": round(vm.total / 2**30, 1),
                "disk": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / 2**30, 1),
            }
        except Exception:
            return {}

    def _get_workspace(self) -> dict:
        """Git repo, docker ? workspace bundle."""
        ws: dict = {"repo": "", "branch": "", "dirty": False, "docker": []}
        try:
            from pathlib import Path
            import subprocess
            cwd = Path.cwd()
            if (cwd / ".git").exists():
                ws["repo"] = cwd.name
                r = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0:
                    ws["branch"] = r.stdout.strip()
                r2 = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True, text=True, timeout=3,
                )
                ws["dirty"] = bool(r2.stdout.strip()) if r2.returncode == 0 else False
        except Exception:
            pass
        try:
            import subprocess
            r = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                ws["docker"] = [n for n in r.stdout.strip().splitlines() if n][:5]
        except Exception:
            pass
        return ws

    def _get_recent_activity(self) -> str:
        """Posledn� aktivita z Work Timeline."""
        try:
            from activity_store import get_activity_store
            events = get_activity_store().get_events(limit=5)
            if not events:
                return ""
            return "; ".join(
                f"{e['title'][:40]}" for e in events[-3:] if e.get("title")
            )
        except Exception:
            return ""

    # ?? Form�tov�n� ???????????????????????????????????

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

        ws = ctx.get("workspace", {})
        if ws.get("repo"):
            branch = f" ({ws['branch']})" if ws.get("branch") else ""
            dirty = " [necommitovano]" if ws.get("dirty") else ""
            parts.append(f"Repo: {ws['repo']}{branch}{dirty}")
        if ws.get("docker"):
            parts.append("Docker: " + ", ".join(ws["docker"]))
        if ctx.get("activity"):
            parts.append(f"Nedavna aktivita: {ctx['activity']}")

        if ctx.get("clipboard"):
            clip = ctx["clipboard"][:120]
            parts.append(f"Schr�nka: {clip}{'?' if len(ctx['clipboard']) > 120 else ''}")

        sys_info = ctx.get("system", {})
        if sys_info:
            host = sys_info.get("hostname", "")
            os_name = sys_info.get("os", "")
            prefix = f"{host} ({os_name})" if host else "Syst�m"
            parts.append(
                f"{prefix}: CPU {sys_info.get('cpu', 0)}%, "
                f"RAM {sys_info.get('ram', 0)}% "
                f"({sys_info.get('ram_used_gb', '?')}/{sys_info.get('ram_total_gb', '?')} GB), "
                f"Disk {sys_info.get('disk', 0)}% "
                f"(volno {sys_info.get('disk_free_gb', '?')} GB)"
            )

        return "\n".join(parts)


_orchestrator: Optional["ContextOrchestrator"] = None


def get_context_orchestrator(config: dict = None) -> "ContextOrchestrator":
    global _orchestrator
    if _orchestrator is None:
        from config import CONFIG
        _orchestrator = ContextOrchestrator(config or CONFIG)
    return _orchestrator
