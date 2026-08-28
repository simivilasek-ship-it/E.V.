"""Souborové operace: vytvoření, smazání, přesun, hledání."""

import logging
import os
import platform
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote

from .utils import safe_run, validate_path

logger = logging.getLogger(__name__)

_HOME = str(Path.home())

_WEB_TLDS = (
    "cz", "com", "org", "net", "io", "sk", "de", "eu", "uk", "app",
    "dev", "ai", "info", "tv", "me", "co", "xyz", "gg", "to", "cc",
    "online", "site", "store", "cloud", "tech", "blog", "news",
)
_TLD_RE = "|".join(_WEB_TLDS)
_SPOKEN_DOT_RE = re.compile(
    r"\s+(tečka|tečku|tečkou|tecka|tecku|teckou|dot)\s+",
    re.IGNORECASE,
)


def spoken_domain_text(text: str) -> str:
    """Převede mluvené ‚hellspy tečka cz' na hellspy.cz."""
    raw = _SPOKEN_DOT_RE.sub(".", text or "")
    return re.sub(r"\.\s+", ".", raw)


def normalize_web_url(url: str) -> str:
    """Doplní https://, když chybí. Prázdný vstup → prázdný řetězec."""
    u = (url or "").strip().strip(".,;:!?")
    u = u.strip("()[]<>\"'")
    if not u or " " in u:
        return ""
    if u.lower().startswith(("http://", "https://")):
        return u
    if u.lower().startswith("www."):
        return "https://" + u
    return "https://" + u


def extract_web_url(text: str) -> str:
    """Najde webovou adresu v textu, i bez https:// a s mluvenou tečkou."""
    raw = spoken_domain_text(text)
    m = re.search(r"https?://[^\s<>\"']+", raw, re.IGNORECASE)
    if m:
        return normalize_web_url(m.group(0))
    m = re.search(r"\bwww\.[^\s<>\"']+", raw, re.IGNORECASE)
    if m:
        return normalize_web_url(m.group(0))
    m = re.search(
        rf"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:{_TLD_RE}))(?:/[^\s]*)?",
        raw,
        re.IGNORECASE,
    )
    if m:
        return normalize_web_url(m.group(0))
    return ""


def announce_open_url(url: str) -> str:
    host = (normalize_web_url(url) or url).split("://", 1)[-1].split("/", 1)[0]
    host = host or url
    return (
        f"Jasně, otevírám {host} v prohlížeči. "
        "Mělo by to vyskočit v novém panelu. Když to nevidíš, řekni."
    )


def announce_open_app(name: str) -> str:
    return (
        f"Spouštím {name}. Mělo by se to objevit za okamžik. "
        "Když okno neskáče, řekni a zkusím to znovu."
    )


def _gui_env() -> dict:
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    runtime = env.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
    env.setdefault("XDG_RUNTIME_DIR", runtime)
    bus = Path(runtime) / "bus"
    if not env.get("DBUS_SESSION_BUS_ADDRESS") and bus.exists():
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"
    return env


def open_in_browser(url: str) -> bool:
    """Otevře URL v systémovém prohlížeči (xdg-open, jinak Chromium/Firefox)."""
    url = normalize_web_url(url)
    if not url:
        return False
    env = _gui_env()
    candidates = (
        ["xdg-open", url],
        ["gio", "open", url],
        ["chromium-browser", "--new-tab", url],
        ["chromium", "--new-tab", url],
        ["google-chrome", "--new-tab", url],
        ["firefox", "--new-tab", url],
        ["sensible-browser", url],
    )
    for cmd in candidates:
        exe = shutil.which(cmd[0])
        if not exe:
            continue
        try:
            subprocess.Popen(
                [exe, *cmd[1:]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                start_new_session=True,
            )
            logger.info("Otevírám prohlížeč: %s", url)
            return True
        except Exception as e:
            logger.debug("open_in_browser %s: %s", cmd[0], e)
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception as e:
        logger.warning("webbrowser.open selhal: %s", e)
        return False


def cmd_open_url(url: str) -> str:
    url = normalize_web_url(url)
    if not url:
        return "Chybí adresa stránky."
    if open_in_browser(url):
        return "ok"
    return f"Nepodařilo se otevřít {url}. Zkus to ještě jednou."


def cmd_search_web(query: str) -> str:
    if open_in_browser(f"https://www.google.com/search?q={quote(query)}"):
        return "ok"
    return "Nepodařilo se otevřít vyhledávání."


def cmd_open_file(path: str) -> str:
    try:
        p = validate_path(path, must_exist=True)
    except ValueError as e:
        return f"Chyba: {e}"
    if platform.system() == "Windows":
        os.startfile(str(p))
    else:
        safe_run(["xdg-open", str(p)], bg=True)
    return "ok"


def cmd_create_folder(path: str = "") -> str:
    try:
        p = validate_path(path)
    except ValueError as e:
        return f"Chyba: {e}"
    p.mkdir(parents=True, exist_ok=True)
    return f"Složka vytvořena: {p}"


def cmd_create_file(path: str = "") -> str:
    try:
        p = validate_path(path)
    except ValueError as e:
        return f"Chyba: {e}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return f"Soubor vytvořen: {p}"


def cmd_delete_file(path: str = "") -> str:
    try:
        p = validate_path(path, must_exist=True)
    except ValueError as e:
        return f"Chyba: {e}"
    result = safe_run(["gio", "trash", str(p)], timeout=5.0)
    if result["rc"] == 0:
        return f"Přesunuto do koše: {p}"
    try:
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        return f"Smazáno: {p}"
    except Exception as e:
        return f"Chyba mazání: {e}"


def cmd_move_file(src: str = "", dst: str = "") -> str:
    try:
        src_p = validate_path(src, must_exist=True)
        dst_p = validate_path(dst)
    except ValueError as e:
        return f"Chyba: {e}"
    try:
        shutil.move(str(src_p), str(dst_p))
        return f"Přesunuto: {src_p} → {dst_p}"
    except Exception as e:
        return f"Chyba přesunu: {e}"


def cmd_find_files(name: str = "", path: str = "~") -> str:
    search_path = str(Path(path).expanduser())
    result = safe_run(
        ["find", search_path, "-iname", f"*{name}*", "-maxdepth", "6"],
        timeout=10.0,
    )
    if result["timeout"]:
        return "Hledání trvalo příliš dlouho."
    files = [f for f in result["stdout"].strip().split("\n") if f][:10]
    return "\n".join(files) if files else "Nic nenalezeno."


def cmd_clipboard_set(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "ok"
    except ImportError:
        return "pyperclip není nainstalován"
