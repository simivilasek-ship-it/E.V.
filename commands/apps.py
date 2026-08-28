"""Správa aplikací: otevřít, zavřít, nainstalovat (apt/snap/flatpak) a spustit."""

from __future__ import annotations

import logging
import platform
import shutil
import threading
import webbrowser
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import quote

import psutil

from event_bus import EventType, get_event_bus

from .utils import safe_run, validate_package_name, validate_path

logger = logging.getLogger(__name__)


def _install_method(spec: AppSpec) -> str:
    if spec.snap:
        return "snap"
    if spec.flatpak:
        return "flatpak"
    if spec.apt:
        return "apt"
    if spec.web_url:
        return "web"
    return "unknown"


_PROGRESS: Dict[str, int] = {
    "starting": 10,
    "method": 25,
    "running": 55,
    "success": 100,
    "cancelled": 0,
    "error": 0,
}

_cancel_flags: Dict[str, threading.Event] = {}
_active_installs: Dict[str, bool] = {}


def _emit_install(event_type: str, spec: AppSpec, stage: str, **extra) -> None:
    data = {"app": spec.key, "stage": stage, **extra}
    if "progress" not in data:
        data["progress"] = _PROGRESS.get(stage, 50)
    if "method" not in data and stage in ("starting", "method", "running", "success"):
        data.setdefault("method", _install_method(spec))
    if stage == "error" and data.get("errors"):
        data["error_code"] = "install_failed"
        data["error_detail"] = data["errors"][0] if isinstance(data["errors"], list) else str(data["errors"])
    get_event_bus().emit(event_type, data, source="apps")


def cmd_cancel_install(name: str = "") -> str:
    """Zruší probíhající instalaci aplikace."""
    spec = resolve_app(name)
    key = spec.key if spec else (name or "").lower().strip()
    if not key or not _active_installs.get(key):
        return f"Žádná aktivní instalace: {key or name}"
    flag = _cancel_flags.get(key)
    if flag:
        flag.set()
    if spec:
        _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
    _active_installs.pop(key, None)
    return f"Instalace {key} zrušena."


_IS_LINUX = platform.system() == "Linux"


@dataclass
class AppSpec:
    """Jak nainstalovat a spustit konkrétní aplikaci na Linuxu."""
    key: str
    aliases: List[str] = field(default_factory=list)
    snap: Optional[str] = None
    flatpak: Optional[str] = None
    apt: Optional[str] = None
    launch: Optional[List[str]] = None
    web_url: Optional[str] = None


# Katalog — snap/flatpak/apt + spuštění (Instagram není v apt)
APP_SPECS: Dict[str, AppSpec] = {
    "instagram": AppSpec(
        key="instagram",
        aliases=["instagram", "ig"],
        snap="instagram-electron",
        launch=["snap", "run", "instagram-electron"],
        web_url="https://www.instagram.com",
    ),
    "spotify": AppSpec(
        key="spotify",
        aliases=["spotify"],
        snap="spotify",
        apt="spotify-client",
        launch=["spotify"],
        web_url="https://open.spotify.com",
    ),
    "discord": AppSpec(
        key="discord",
        aliases=["discord"],
        snap="discord",
        launch=["discord"],
        web_url="https://discord.com/app",
    ),
    "telegram": AppSpec(
        key="telegram",
        aliases=["telegram"],
        snap="telegram-desktop",
        apt="telegram-desktop",
        launch=["telegram-desktop"],
    ),
    "whatsapp": AppSpec(
        key="whatsapp",
        aliases=["whatsapp", "wa"],
        snap="whatsapp-for-linux",
        web_url="https://web.whatsapp.com",
    ),
    "vlc": AppSpec(
        key="vlc",
        aliases=["vlc"],
        apt="vlc",
        snap="vlc",
        launch=["vlc"],
    ),
    "firefox": AppSpec(
        key="firefox",
        aliases=["firefox", "mozilla firefox"],
        apt="firefox",
        snap="firefox",
        launch=["firefox"],
    ),
    "chrome": AppSpec(
        key="chrome",
        aliases=["chrome", "google chrome", "chromium"],
        apt="chromium-browser",
        launch=["google-chrome", "chromium", "chromium-browser"],
    ),
    "code": AppSpec(
        key="code",
        aliases=["vscode", "code", "visual studio code"],
        snap="code",
        apt="code",
        launch=["code"],
    ),
    "steam": AppSpec(
        key="steam",
        aliases=["steam"],
        apt="steam",
        launch=["steam"],
    ),
    "gimp": AppSpec(
        key="gimp",
        aliases=["gimp"],
        apt="gimp",
        snap="gimp",
        launch=["gimp"],
    ),
    "obs": AppSpec(
        key="obs",
        aliases=["obs", "obs studio"],
        snap="obs-studio",
        apt="obs-studio",
        launch=["obs"],
    ),
    "slack": AppSpec(
        key="slack",
        aliases=["slack"],
        snap="slack",
        web_url="https://slack.com",
    ),
    "zoom": AppSpec(
        key="zoom",
        aliases=["zoom"],
        apt="zoom",
        snap="zoom-client",
        launch=["zoom"],
    ),
}

# Zpětná kompatibilita s open_app
APP_MAP: Dict[str, List[str]] = {
    spec.key: spec.aliases for spec in APP_SPECS.values()
}
# Doplň aplikace bez vlastního install specu
APP_MAP.update({
    "msedge":      ["edge", "microsoft edge"],
    "libreoffice": ["libreoffice"],
    "nautilus":    ["nautilus", "správce souborů", "files"],
    "gedit":       ["gedit", "textový editor"],
    "tilix":       ["tilix", "terminál", "terminal"],
    "calc":        ["kalkulačka", "calc"],
    "cursor":      ["cursor"],
    "inkscape":    ["inkscape"],
    "blender":     ["blender"],
})


def resolve_app(name: str) -> Optional[AppSpec]:
    """Najde AppSpec podle klíče nebo aliasu."""
    nl = (name or "").lower().strip()
    if not nl:
        return None
    if nl in APP_SPECS:
        return APP_SPECS[nl]
    for spec in APP_SPECS.values():
        if nl == spec.key or nl in [a.lower() for a in spec.aliases]:
            return spec
    return None


def find_app(name: str) -> str:
    spec = resolve_app(name)
    if spec:
        return spec.key
    nl = name.lower().strip()
    for cmd, aliases in APP_MAP.items():
        if nl == cmd or nl in [a.lower() for a in aliases]:
            return cmd
    return nl


def _snap_installed(pkg: str) -> bool:
    r = safe_run(["snap", "list", pkg], timeout=8)
    return r["rc"] == 0 and pkg in r.get("stdout", "")


def _flatpak_installed(app_id: str) -> bool:
    r = safe_run(["flatpak", "info", app_id], timeout=8)
    return r["rc"] == 0


def _apt_installed(pkg: str) -> bool:
    r = safe_run(["dpkg", "-s", pkg], timeout=8)
    return r["rc"] == 0


def _which_any(candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if shutil.which(c):
            return c
    return None


def is_app_installed(spec: AppSpec) -> bool:
    if spec.snap and _snap_installed(spec.snap):
        return True
    if spec.flatpak and _flatpak_installed(spec.flatpak):
        return True
    if spec.apt and _apt_installed(spec.apt):
        return True
    if spec.launch:
        cmds = [c for c in spec.launch if not c.startswith("snap")]
        if _which_any(cmds):
            return True
        if spec.snap and _snap_installed(spec.snap):
            return True
    return False


def launch_app_spec(spec: AppSpec) -> str:
    """Spustí aplikaci podle spec (snap run, binárka, nebo web)."""
    if spec.launch:
        # snap run
        if len(spec.launch) >= 3 and spec.launch[0] == "snap":
            if _snap_installed(spec.launch[2]):
                r = safe_run(spec.launch, bg=True)
                if r["rc"] == 0:
                    return "ok"
        # běžné příkazy — zkus všechny varianty
        for cmd in spec.launch:
            if cmd == "snap":
                continue
            if shutil.which(cmd):
                r = safe_run([cmd], bg=True)
                if r["rc"] == 0:
                    return "ok"
    if spec.web_url:
        webbrowser.open(spec.web_url)
        return "ok"
    return f"Aplikaci {spec.key} se nepodařilo spustit"


def _install_spec_worker(spec: AppSpec, launch_after: bool) -> None:
    """Instalace na pozadí + volitelné spuštění."""
    installed = False
    used_method: Optional[str] = None
    errors: List[str] = []
    cancel = threading.Event()
    _cancel_flags[spec.key] = cancel
    _active_installs[spec.key] = True

    def _cancelled() -> bool:
        return cancel.is_set()

    try:
        _emit_install(EventType.INSTALL_PROGRESS, spec, "starting", launch_after=launch_after)
        method = _install_method(spec)
        _emit_install(EventType.INSTALL_PROGRESS, spec, "method", method=method)

        if _cancelled():
            _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
            return

        if not _IS_LINUX:
            if launch_after and spec.web_url:
                webbrowser.open(spec.web_url)
                _emit_install(
                    EventType.INSTALL_PROGRESS, spec, "success",
                    method="web", launched=True,
                )
            else:
                _emit_install(
                    EventType.INSTALL_ERROR, spec, "error",
                    errors=["Instalace podporována pouze na Linuxu"],
                )
            return

        if spec.snap and shutil.which("snap") and not _snap_installed(spec.snap):
            _emit_install(EventType.INSTALL_PROGRESS, spec, "running", method="snap", progress=45)
            if _cancelled():
                _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
                return
            r = safe_run(["snap", "install", spec.snap], timeout=600)
            if r["rc"] != 0 and "access denied" in (r.get("stderr") or "").lower():
                r = safe_run(["pkexec", "snap", "install", spec.snap], timeout=600)
            if r["rc"] == 0:
                installed = True
                used_method = "snap"
                logger.info(f"Snap nainstalován: {spec.snap}")
            else:
                errors.append(f"snap: {r.get('stderr', '')[:200]}")

        if not installed and spec.flatpak and shutil.which("flatpak") and spec.flatpak:
            if not _flatpak_installed(spec.flatpak):
                _emit_install(EventType.INSTALL_PROGRESS, spec, "running", method="flatpak", progress=50)
                if _cancelled():
                    _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
                    return
                r = safe_run(["flatpak", "install", "-y", "flathub", spec.flatpak], timeout=600)
                if r["rc"] == 0:
                    installed = True
                    used_method = "flatpak"
                else:
                    errors.append(f"flatpak: {r.get('stderr', '')[:200]}")

        if not installed and spec.apt and shutil.which("apt"):
            if not _apt_installed(spec.apt):
                _emit_install(EventType.INSTALL_PROGRESS, spec, "running", method="apt", progress=50)
                if _cancelled():
                    _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
                    return
                safe_run(["pkexec", "apt", "install", "-y", spec.apt], timeout=600)
                if _apt_installed(spec.apt):
                    installed = True
                    used_method = "apt"

        launched = False
        if launch_after and not _cancelled():
            if installed or is_app_installed(spec):
                launch_app_spec(spec)
                launched = True
            elif spec.web_url:
                webbrowser.open(spec.web_url)
                launched = True

        if _cancelled():
            _emit_install(EventType.INSTALL_ERROR, spec, "cancelled", errors=["Instalace zrušena uživatelem"])
        elif installed:
            _emit_install(
                EventType.INSTALL_PROGRESS, spec, "success",
                method=used_method or method, launched=launched,
            )
        elif errors:
            _emit_install(EventType.INSTALL_ERROR, spec, "error", errors=errors)
            logger.warning(f"Instalace {spec.key}: {'; '.join(errors)}")
        else:
            _emit_install(
                EventType.INSTALL_ERROR, spec, "error",
                errors=["Instalace se nezdařila — žádný balíčkový manažer neuspěl"],
            )
    finally:
        _active_installs.pop(spec.key, None)
        _cancel_flags.pop(spec.key, None)


def cmd_open_app(app: str, args: Optional[List[str]] = None) -> str:
    spec = resolve_app(app)
    if spec:
        if is_app_installed(spec):
            result = launch_app_spec(spec)
            return "ok" if result == "ok" else result
        if spec.web_url:
            webbrowser.open(spec.web_url)
            return f"Otevírám {spec.key} v prohlížeči (není nainstalováno — řekni 'stahni {spec.key}')."
        return f"Aplikace '{app}' není nainstalována. Řekni 'stahni {spec.key}'."

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


def cmd_install_app(name: str = "", launch: bool = True) -> str:
    """Nainstaluje aplikaci (snap → flatpak → apt) a volitelně spustí."""
    spec = resolve_app(name)
    if spec:
        if is_app_installed(spec):
            if launch:
                launch_app_spec(spec)
                return f"{spec.key} už je nainstalované — spouštím."
            return f"{spec.key} už je nainstalované."

        threading.Thread(
            target=_install_spec_worker,
            args=(spec, launch),
            daemon=True,
            name=f"install-{spec.key}",
        ).start()
        method = "snap" if spec.snap else "flatpak" if spec.flatpak else "apt"
        if launch:
            return f"Stahuji a instaluji {spec.key} ({method})… Po dokončení se spustí."
        return f"Instaluji {spec.key} ({method})…"

    # Neznámá aplikace — fallback apt
    try:
        pkg = validate_package_name(name)
    except ValueError as e:
        return f"Chyba: {e}"
    safe_run(["pkexec", "apt", "install", "-y", pkg], bg=True)
    return f"Instaluji přes apt: {pkg}"


def cmd_uninstall_app(name: str = "") -> str:
    spec = resolve_app(name)
    if spec:
        if spec.snap and _snap_installed(spec.snap):
            safe_run(["pkexec", "snap", "remove", spec.snap], bg=True)
            return f"Odinstalovávám {spec.key} (snap)."
        if spec.flatpak and _flatpak_installed(spec.flatpak):
            safe_run(["flatpak", "uninstall", "-y", spec.flatpak], bg=True)
            return f"Odinstalovávám {spec.key} (flatpak)."
        if spec.apt:
            safe_run(["pkexec", "apt", "remove", "-y", spec.apt], bg=True)
            return f"Odinstalovávám {spec.key} (apt)."
        return f"{spec.key} není nainstalované."

    try:
        pkg = validate_package_name(name)
    except ValueError as e:
        return f"Chyba: {e}"
    safe_run(["pkexec", "apt", "remove", "-y", pkg], bg=True)
    return f"Odinstaluji: {pkg}"


_ALLOWED_SCRIPT_SUFFIXES = {".sh", ".py", ".bash"}


def cmd_run_script(path: str = "") -> str:
    try:
        p = validate_path(path, must_exist=True)
    except ValueError as e:
        return f"Chyba cesty: {e}"
    if p.suffix.lower() not in _ALLOWED_SCRIPT_SUFFIXES:
        return f"Nepodporovaná přípona skriptu: {p.suffix} (povoleno: {', '.join(_ALLOWED_SCRIPT_SUFFIXES)})"
    interpreter = "python3" if p.suffix == ".py" else "bash"
    safe_run([interpreter, str(p)], bg=True)
    return f"Spouštím: {p}"


def cmd_vscode_open(path: str = "") -> str:
    try:
        p = validate_path(path)
    except ValueError as e:
        return f"Chyba cesty: {e}"
    safe_run(["code", str(p)], bg=True)
    return f"Otevřeno ve VSCode: {p}"
