"""Správa aplikací: otevřít, zavřít, nainstalovat."""

import logging
import platform
import shutil
import subprocess
import webbrowser
from typing import Dict, List, Optional
from urllib.parse import quote

import psutil

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
    try:
        subprocess.Popen([app_cmd] + (args or []))
        return "ok"
    except FileNotFoundError:
        return f"Aplikace '{app}' nenalezena"
    except Exception as e:
        return f"Chyba: {e}"


def _launch_spotify(args: Optional[List[str]] = None) -> str:
    if args:
        try:
            subprocess.Popen(["xdg-open", f"spotify:search:{quote(' '.join(args))}"])
            return "ok"
        except Exception:
            pass
    if shutil.which("spotify"):
        subprocess.Popen(["spotify"])
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
    subprocess.Popen(["pkexec", "apt", "install", "-y", name])
    return f"Instaluji: {name}"


def cmd_uninstall_app(name: str = "") -> str:
    subprocess.Popen(["pkexec", "apt", "remove", "-y", name])
    return f"Odinstaluji: {name}"


def cmd_run_script(path: str = "") -> str:
    from pathlib import Path
    subprocess.Popen(["bash", str(Path(path).expanduser())])
    return f"Spouštím: {path}"


def cmd_vscode_open(path: str = "") -> str:
    import os
    p = os.path.expanduser(path)
    subprocess.Popen(["code", p])
    return f"Otevřeno ve VSCode: {p}"
