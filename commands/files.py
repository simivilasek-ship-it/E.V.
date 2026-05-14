"""Souborové operace: vytvoření, smazání, přesun, hledání."""

import logging
import os
import platform
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import quote

from .utils import safe_run

logger = logging.getLogger(__name__)

_HOME = str(Path.home())


def cmd_open_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return "ok"


def cmd_search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote(query)}")
    return "ok"


def cmd_open_file(path: str) -> str:
    path = os.path.expanduser(path)
    if platform.system() == "Windows":
        os.startfile(path)
    else:
        safe_run(["xdg-open", path], bg=True)
    return "ok"


def cmd_create_folder(path: str = "") -> str:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return f"Složka vytvořena: {p}"


def cmd_create_file(path: str = "") -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return f"Soubor vytvořen: {p}"


def cmd_delete_file(path: str = "") -> str:
    p = Path(path).expanduser()
    result = safe_run(["gio", "trash", str(p)], timeout=5.0)
    if result["rc"] == 0:
        return f"Přesunuto do koše: {p}"
    # gio není k dispozici nebo selhalo — smaž přímo
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
        shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
        return f"Přesunuto: {src} → {dst}"
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
