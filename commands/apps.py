"""Správa aplikací: otevřít, zavřít, nainstalovat."""

import logging
import platform
import shutil
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import psutil

from .utils import safe_run

logger = logging.getLogger(__name__)

_IS_LINUX = platform.system() == "Linux"

APP_MAP: Dict[str, List[str]] = {
    "chrome":      ["chrome", "google chrome"],
    "firefox":     ["firefox", "mozilla firefox"],
    "msedge":      ["edge", "microsoft edge"],
    "spotify":     ["spotify"],
    "discord":     ["discord"],
    "code":        ["vscode", "code", "visual studio code"],
    "steam":       ["steam"],
    "vlc":         ["vlc"],
    "telegram":    ["telegram"],
    "gimp":        ["gimp"],
    "libreoffice": ["libreoffice"],
    "nautilus":    ["nautilus", "správce souborů", "files"],
    "gedit":       ["gedit", "textový editor"],
    "tilix":       ["tilix", "terminál", "terminal"],
    "calc":        ["kalkulačka", "calc"],
    "inkscape":    ["inkscape"],
    "blender":     ["blender"],
}


def find_app(name: str) -> str:
    nl = name.lower().strip()
    for cmd, aliases in APP_MAP.items():
        if nl == cmd or nl in [a.lower() for a in aliases]:
            return cmd
    return nl


def cmd_open_app(app: str, args: Optional[List[str]] = None) -> str:
    app_cmd = find_app(app)
    if app_cmd == "spotify":
        return _launch_spotify(args)
    result = safe_run([app_cmd] + (args or []), bg=True)
    if result["rc"] != 0:
        return f"Aplikace '{app}' nenalezena"
    return "ok"


def _launch_spotify(args: Optional[List[str]] = None) -> str:
    if args:
        r = safe_run(["xdg-open", f"spotify:search:{quote(' '.join(args))}"], bg=True)
        if r["rc"] == 0:
            return "ok"
    if shutil.which("spotify"):
        safe_run(["spotify"], bg=True)
    else:
        webbrowser.open("https://open.spotify.com/")
    return "ok"


def cmd_kill_process(name: str) -> str:
    killed = 0
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and name.lower() in proc.info["name"].lower():
            try:
                proc.kill()
                killed += 1
            except Exception:
                pass
    return f"Ukončeno: {killed} procesů" if killed else f"Proces '{name}' nenalezen"


def cmd_install_app(name: str = "") -> str:
    safe_run(["pkexec", "apt", "install", "-y", name], bg=True)
    return f"Instaluji: {name}"


def cmd_uninstall_app(name: str = "") -> str:
    safe_run(["pkexec", "apt", "remove", "-y", name], bg=True)
    return f"Odinstaluji: {name}"


def cmd_run_script(path: str = "") -> str:
    safe_run(["bash", str(Path(path).expanduser())], bg=True)
    return f"Spouštím: {path}"


def cmd_vscode_open(path: str = "") -> str:
    import os
    p = os.path.expanduser(path)
    safe_run(["code", p], bg=True)
    return f"Otevřeno ve VSCode: {p}"
