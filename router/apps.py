"""
E.V. router — app and site routing.
Handles open/close/install commands and website navigation.
"""
import os
import re

from commands.utils import normalize_text as _norm
from .constants import (
    _SITES, _APPS, _PROC_ALIASES, _CLOSE_TRIGGER, _OPEN_TRIGGER,
    _INSTALL_APP_NAMES,
)

_HOME = os.path.expanduser("~")


def _extract_app_name(text: str) -> str:
    """Odstraní trigger slova a vrátí název aplikace/procesu."""
    t = re.sub(
        r"\b(zavri|ukonci|zabij|zabi|kill|stop|ukoncit|otevri|spust|open|start"
        r"|okno|aplikaci|program|proces|appku|app|web|stranku)\b",
        "", _norm(text), flags=re.IGNORECASE,
    ).strip(" ,.-")
    return t


def _extract_install_name(text: str, t: str) -> str:
    """Vrátí název balíčku/aplikace pro install_app."""
    patterns = [
        r"\b(?:nainstaluj|instaluj|nainstalovat|install|apt\s+install)\s+(.+)",
        r"\bstahni\s+(?:aplikaci|appku|app|program)\s+(.+)",
        r"\baplikaci\s+(\S+)\s+stahni",
        r"\bstahni\s+(\S+)\s+aplikaci",
    ]
    for pat in patterns:
        m = re.search(pat, t, re.I)
        if m:
            return m.group(1).strip(" ?.,!")
    m = re.search(r"\bstahni\s+(\S+)", t, re.I)
    if m:
        name = m.group(1).strip(" ?.,!")
        if name.lower() in _INSTALL_APP_NAMES:
            return name
    return ""


def _is_video_download_intent(t: str, text: str) -> bool:
    """True pokud jde o stažení videa/hudby (yt-dlp), ne aplikace."""
    if re.search(r"\b(youtube\.com|youtu\.be)\b", text, re.I):
        return True
    if re.search(
        r"\b(stahni\s+(?:video|youtube|hudbu|mp3|zvuk|skladbu|pisnicku|song)"
        r"|stahni\s+.+\s+(?:z\s+)?youtube"
        r"|uloz\s+video|uloz\s+audio"
        r"|download\s+(?:video|from\s+youtube|mp3))\b",
        t, re.I,
    ):
        return True
    m = re.search(r"\bstahni\s+(.+)", t, re.I)
    if m:
        rest = m.group(1).strip()
        first = rest.split()[0].lower() if rest else ""
        if first in _INSTALL_APP_NAMES:
            return False
        if re.search(r"\b(aplikaci|appku|app|program)\b", t):
            return False
        return len(rest.split()) >= 1 and first not in _INSTALL_APP_NAMES
    return False


def route_apps(text: str, t: str, sites: dict | None = None) -> tuple:
    """
    Handles app open/close/install commands.
    *sites* overrides the default _SITES (pass LocalRouter._sites for custom_sites support).
    """
    _s = sites if sites is not None else _SITES

    # Close / kill app (must run before fuzzy: "zavři X" ≠ "otevři X")
    if _CLOSE_TRIGGER.search(t):
        app_name = _extract_app_name(text)
        if len(app_name) > 1:
            proc = app_name.lower()
            for alias, real in _PROC_ALIASES.items():
                if _norm(alias) in proc:
                    proc = real
                    break
            return f"Ukončuji {app_name}.", {
                "action": "kill_process", "params": {"name": proc}}

    # VSCode open (before generic open_app to avoid mis-routing "otevři code")
    if re.search(r"\b(otevri|open)\s+(ve?\s+)?(vscode|code|editor)\b", t):
        rest = re.sub(
            r"\b(otevri|open)\s+(ve?\s+)?(vscode|code|editor)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        path = os.path.expanduser(rest) if rest else _HOME
        return f"Otevírám ve VSCode: {rest or '~'}.", {
            "action": "vscode_open", "params": {"path": path}}

    # Script run (before open_app so "spusť test.sh" isn't treated as app name)
    m = re.search(r"\b(spust|spusti|spusť|run|execute)\s+(\S+\.(sh|py|bash|zsh|rb|pl))\b", t)
    if m:
        name = m.group(2).strip()
        path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
        return f"Spouštím skript {name}.", {
            "action": "run_script", "params": {"path": os.path.expanduser(path)}}
    m = re.search(r"\b(spust|spusti|spusť|run|execute|bash|sh)\s+skript\s+(\S+)", t)
    if m:
        name = m.group(2).strip()
        path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
        return f"Spouštím skript {name}.", {
            "action": "run_script", "params": {"path": os.path.expanduser(path)}}

    # Rename (before move_file — more specific pattern)
    m = re.search(
        r"\b(prejmenuj|prejmenu(j)?|rename)\s+(?:soubor\s+)?(\S+)\s+(na|to)\s+(\S+)", t)
    if m:
        src = m.group(3).strip()
        dst = m.group(5).strip()
        src_p = os.path.expanduser(src if "/" in src else os.path.join(_HOME, src))
        dst_p = os.path.expanduser(dst if "/" in dst else os.path.join(_HOME, dst))
        return f"Přejmenovávám {src} → {dst}.", {
            "action": "move_file", "params": {"src": src_p, "dst": dst_p}}

    # Install app (before yt-dlp: "stahni instagram" = install, not download)
    install_name = _extract_install_name(text, t)
    if install_name and not _is_video_download_intent(t, text):
        from commands.apps import find_app, resolve_app
        pkg = find_app(install_name)
        spec = resolve_app(pkg)
        label = spec.key if spec else pkg
        return f"Stahuji, instaluji a spouštím {label}…", {
            "action": "install_app", "params": {"name": pkg, "launch": True}}

    if re.search(r"\b(odinstaluj|odstran\s+aplikaci|uninstall)\b", t):
        m = re.search(r"\b(?:odinstaluj|uninstall|odstran\s+aplikaci)\s+(.+)", t, re.I)
        if m:
            from commands.apps import find_app
            pkg = find_app(m.group(1).strip(" ?.,!"))
            return f"Odinstalovávám: {pkg}.", {
                "action": "uninstall_app", "params": {"name": pkg}}

    # Open trigger: sites, then apps, then raw URL
    if _OPEN_TRIGGER.search(t):
        for site, url in _s.items():
            if site in t:
                return f"Otevírám {site.capitalize()}.", {
                    "action": "open_url", "params": {"url": url}}
        for name, cmd in _APPS.items():
            if _norm(name) in t:
                return f"Spouštím {name}.", {
                    "action": "open_app", "params": {"app": cmd}}
        url_m = re.search(r"(https?://\S+|\w+\.\w{2,}\S*)", text)
        if url_m:
            url = url_m.group(1)
            return f"Otevírám {url}.", {
                "action": "open_url",
                "params": {"url": url if url.startswith("http") else "https://" + url}}

    return None, None


def route_sites(text: str, t: str, sites: dict | None = None) -> tuple:
    """Handles URL navigation and website opening."""
    # URL with explicit browser intent keyword
    url_early = re.search(r"(https?://\S+|\b\w[\w.-]+\.\w{2,}\S*)", text)
    if url_early and re.search(
        r"\b(spust|otevri|naviguj|jdi\s+na|web|stranku|prohlizec|browser|chromium|firefox|chrome)\b",
        t,
    ):
        url = url_early.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        return f"Otevírám {url}.", {"action": "open_url", "params": {"url": url}}

    # Fallback: any domain-like URL in text
    url_fb = re.search(r"(https?://\S+|\b\w[\w.-]+\.(cz|com|org|net|io|sk|de|eu)\S*)", text)
    if url_fb:
        url = url_fb.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        return f"Otevírám {url}.", {"action": "open_url", "params": {"url": url}}

    return None, None
