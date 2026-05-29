"""
JARVIS Desktop App
Nativní okno s React HUD UI — pywebview + FastAPI backend.

Fallback pořadí:
  1. pywebview + GTK  (nativní okno)
  2. pywebview + Qt   (pip install pyqt6)
  3. Prohlížeč        (xdg-open / webbrowser)

Spuštění:
  python app_desktop.py
  bash start_desktop.sh
"""
from __future__ import annotations

import sys
import os
import subprocess
import threading
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parent
WEB_DIST     = ROOT / "web_dist"
BACKEND_PORT = 8002
BACKEND_URL  = f"http://127.0.0.1:{BACKEND_PORT}"
WINDOW_TITLE = "JARVIS v4.3"


# ── Backend ───────────────────────────────────────────

def start_backend() -> bool:
    """Spustí FastAPI v daemon vlákně. Vrátí False pokud port obsazený."""
    import socket
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", BACKEND_PORT)) == 0:
            logger.info("Backend už běží na portu %d", BACKEND_PORT)
            return True
    try:
        import uvicorn
        from dashboard import app
        t = threading.Thread(
            target=lambda: uvicorn.run(
                app, host="127.0.0.1", port=BACKEND_PORT,
                log_level="warning", access_log=False),
            daemon=True)
        t.start()
        return True
    except Exception as e:
        logger.error("Backend selhal: %s", e)
        return False


def wait_for_backend(timeout: float = 12.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BACKEND_URL}/api/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


# ── GTK dostupnost ────────────────────────────────────

def _has_gtk() -> bool:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        return True
    except Exception:
        return False


def _has_qt() -> bool:
    try:
        import PyQt6
        return True
    except ImportError:
        try:
            import PyQt5
            return True
        except ImportError:
            return False


# ── Spuštění okna ─────────────────────────────────────

def run_webview(url: str):
    """Zkusí spustit pywebview s dostupným backendem (GTK nebo Qt)."""
    import webview

    # Vyber GUI backend
    if _has_gtk():
        gui = "gtk"
    elif _has_qt():
        gui = "qt"
    else:
        raise RuntimeError("Žádný GUI backend (gtk/qt) není dostupný")

    class JarvisAPI:
        def get_version(self):    return "4.3"
        def get_status(self):
            try:
                from config import CONFIG
                return {"model": CONFIG.get("ollama_model", "?"), "backend": BACKEND_URL}
            except Exception:
                return {}

    window = webview.create_window(
        title            = WINDOW_TITLE,
        url              = url,
        width            = 1400,
        height           = 860,
        min_size         = (900, 600),
        resizable        = True,
        background_color = "#030810",
        js_api           = JarvisAPI(),
    )
    window.events.closing += lambda: sys.exit(0)
    webview.start(gui=gui, debug="--debug" in sys.argv)


def run_browser(url: str):
    """Fallback — otevře URL v systémovém prohlížeči."""
    print(f"\n  JARVIS UI → {url}\n")
    import webbrowser
    webbrowser.open(url)
    print("  Stiskni Ctrl+C pro ukončení backendu.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nJARVIS zastaven.")
        sys.exit(0)


# ── Instalace chybějících závislostí ──────────────────

def _try_install_gtk():
    """Pokusí se nainstalovat PyGObject přes apt (bez sudo hesla pokud je dostupné)."""
    try:
        result = subprocess.run(
            ["apt-get", "install", "-y", "-qq",
             "python3-gi", "python3-gi-cairo",
             "gir1.2-gtk-3.0", "gir1.2-webkit2-4.1"],
            capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────

def main():
    print(f"JARVIS Desktop v4.3")

    # Spusť backend
    start_backend()
    print("Čekám na backend...", end=" ", flush=True)
    backend_ok = wait_for_backend(timeout=12)
    print("✓" if backend_ok else "⚠ timeout — pokračuji bez backendu")

    url = BACKEND_URL if backend_ok else str(WEB_DIST / "index.html")

    # Zkus pywebview
    try:
        import webview
    except ImportError:
        print("  pywebview není nainstalován — zkouším: pip install pywebview")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install",
                            "pywebview", "--quiet"], check=True, timeout=120)
            import webview
        except Exception:
            print("  Instalace selhala → otevírám prohlížeč")
            run_browser(url)
            return

    # Zkus GTK backend
    if not _has_gtk():
        print("  GTK není dostupné — zkouším nainstalovat python3-gi...")
        _try_install_gtk()

    if _has_gtk() or _has_qt():
        try:
            run_webview(url)
            return
        except Exception as e:
            print(f"  pywebview selhal ({e}) → otevírám prohlížeč")

    # Finální fallback — prohlížeč
    run_browser(url)


if __name__ == "__main__":
    main()
