"""
JARVIS Desktop Launcher
Spustí FastAPI backend a otevře React UI v prohlížeči (nebo pywebview okno).

Použití:
  python app_desktop.py            # backend + prohlížeč
  python app_desktop.py --webview  # pokusí se o nativní okno (pywebview)
  bash start_desktop.sh
"""
from __future__ import annotations

import os
import sys
import subprocess
import threading
import time
import webbrowser
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parent
WEB_DIST     = ROOT / "web_dist"
BACKEND_PORT = 8002
BACKEND_URL  = f"http://127.0.0.1:{BACKEND_PORT}"
WINDOW_TITLE = "JARVIS v4.4"
USE_WEBVIEW  = "--webview" in sys.argv


# ── Backend ───────────────────────────────────────────

def _port_busy(port: int) -> bool:
    import socket
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_backend() -> None:
    if _port_busy(BACKEND_PORT):
        logger.info("Backend už běží na portu %d", BACKEND_PORT)
        return
    try:
        import uvicorn
        from dashboard import app as dash_app
        t = threading.Thread(
            target=lambda: uvicorn.run(
                dash_app, host="127.0.0.1", port=BACKEND_PORT,
                log_level="error", access_log=False),
            daemon=True)
        t.start()
    except Exception as e:
        logger.error("Backend selhal: %s", e)


def wait_for_backend(timeout: float = 15.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BACKEND_URL}/api/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ── Spuštění okna ─────────────────────────────────────

def _setup_qt_env():
    """Nastaví Qt WebEngine proměnné PŘED importem PyQt6."""
    try:
        import importlib.util
        spec = importlib.util.find_spec("PyQt6")
        if not spec:
            return
        qt6 = os.path.join(os.path.dirname(spec.origin), "Qt6")
        res = os.path.join(qt6, "resources")
        loc = os.path.join(qt6, "translations", "qtwebengine_locales")
        if os.path.isdir(res):
            os.environ["QTWEBENGINE_RESOURCES_PATH"] = res
        if os.path.isdir(loc):
            os.environ["QTWEBENGINE_LOCALES_PATH"] = loc
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-dev-shm-usage"
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    except Exception:
        pass


def run_webview(url: str) -> bool:
    """Pokusí se o nativní pywebview okno. Vrátí False při selhání."""
    _setup_qt_env()
    try:
        import webview

        gui = None
        try:
            import gi
            gui = "gtk"
        except ImportError:
            pass

        if not gui:
            try:
                from qtpy import QtCore  # noqa
                gui = "qt"
            except ImportError:
                pass

        if not gui:
            logger.warning("Žádný GUI backend (gtk/qt) — otevírám prohlížeč")
            return False

        class JarvisAPI:
            def get_version(self): return "4.4"

        w = webview.create_window(
            WINDOW_TITLE, url,
            width=1440, height=880, min_size=(960, 620),
            resizable=True, background_color="#030810",
            js_api=JarvisAPI(),
        )
        w.events.closing += lambda: sys.exit(0)
        print(f"  Okno ({gui}) → {url}")
        webview.start(gui=gui)
        return True
    except Exception as e:
        logger.warning("pywebview selhal: %s", e)
        return False


def run_browser(url: str) -> None:
    """Otevře URL v systémovém prohlížeči a čeká."""
    print(f"  Otevírám prohlížeč → {url}")
    webbrowser.open(url)
    print("  Stiskni Ctrl+C pro ukončení backendu.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nJARVIS zastaven.")
        sys.exit(0)


# ── Main ──────────────────────────────────────────────

def main():
    print("JARVIS v4.4")

    # Sestav React pokud chybí web_dist
    if not WEB_DIST.exists():
        web_dir = ROOT / "web"
        if web_dir.exists():
            print("  Sestavuji React frontend...")
            subprocess.run(["npm", "run", "build"], cwd=web_dir,
                           capture_output=True)

    # Spusť backend
    start_backend()
    print("  Backend...", end=" ", flush=True)
    ok = wait_for_backend(timeout=15)
    print("✓" if ok else "⚠ timeout")

    url = BACKEND_URL if ok else (
        str(WEB_DIST / "index.html") if WEB_DIST.exists() else BACKEND_URL)

    # Nativní okno (volitelné)
    if USE_WEBVIEW:
        if not run_webview(url):
            run_browser(url)
    else:
        run_browser(url)


if __name__ == "__main__":
    main()
