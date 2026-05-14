"""Souborové operace: vytvoření, smazání, přesun, hledání."""

import logging
import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote

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
        subprocess.Popen(["xdg-open", path])
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
    result = subprocess.run(["gio", "trash", str(p)], capture_output=True)
    if result.returncode == 0:
        return f"Přesunuto do koše: {p}"
    if p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)
    return f"Smazáno: {p}"


def cmd_move_file(src: str = "", dst: str = "") -> str:
    shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
    return f"Přesunuto: {src} → {dst}"


def cmd_find_files(name: str = "", path: str = "~") -> str:
    search_path = Path(path).expanduser()
    result = subprocess.run(
        ["find", str(search_path), "-iname", f"*{name}*", "-maxdepth", "6"],
        capture_output=True, text=True, timeout=10,
    )
    files = [f for f in result.stdout.strip().split("\n") if f][:10]
    return "\n".join(files) if files else "Nic nenalezeno."


def cmd_clipboard_set(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "ok"
    except ImportError:
        return "pyperclip není nainstalován"
