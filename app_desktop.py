"""
JARVIS Desktop App
Nativní okno s React HUD UI — pywebview + FastAPI backend.

Spuštění:
  python app_desktop.py          # produkce (web_dist/)
  python app_desktop.py --dev    # dev server (localhost:3000)
  bash start_desktop.sh
"""
from __future__ import annotations

# ── Qt WebEngine env vars MUSÍ být před importem PyQt6 ──────────
import os, sys

def _setup_qt_env():
    try:
        import importlib.util
        spec = importlib.util.find_spec("PyQt6")
        if not spec:
            return
        qt6_dir = os.path.join(os.path.dirname(spec.origin), "Qt6")
        res = os.path.join(qt6_dir, "resources")
        loc = os.path.join(qt6_dir, "translations", "qtwebengine_locales")
        if os.path.isdir(res):
            os.environ["QTWEBENGINE_RESOURCES_PATH"] = res
        if os.path.isdir(loc):
            os.environ["QTWEBENGINE_LOCALES_PATH"] = loc
        # Qt WebEngine bez GPU — WebGL selhá, ale ErrorBoundary v React
        # přepne na CSS orb automaticky
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--no-sandbox --disable-dev-shm-usage --no-first-run"
        )
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    except Exception:
        pass

_setup_qt_env()  # musí být před jakýmkoliv Qt importem
# ────────────────────────────────────────────────────────────────

import subprocess
import threading
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parent
WEB_DIST     = ROOT / "web_dist"
BACKEND_PORT = 8002
BACKEND_URL  = f"http://127.0.0.1:{BACKEND_PORT}"
DEV_URL      = "http://localhost:3000"
WINDOW_TITLE = "JARVIS v4.3"
DEV_MODE     = "--dev" in sys.argv


# ── Backend ───────────────────────────────────────────

def _port_free(port: int) -> bool:
    import socket
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def start_backend():
    if not _port_free(BACKEND_PORT):
        logger.info("Backend už běží na portu %d", BACKEND_PORT)
        return
    try:
        import uvicorn
        from dashboard import app
        t = threading.Thread(
            target=lambda: uvicorn.run(
                app, host="127.0.0.1", port=BACKEND_PORT,
                log_level="error", access_log=False),
            daemon=True)
        t.start()
    except Exception as e:
        logger.error("Backend selhal: %s", e)


def wait_for_url(url: str, timeout: float = 15.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ── Webview ───────────────────────────────────────────

class JarvisAPI:
    def get_version(self): return "4.3"
    def get_status(self):
        try:
            from config import CONFIG
            return {"model": CONFIG.get("ollama_model", "?"),
                    "backend": BACKEND_URL}
        except Exception:
            return {}


def run_webview(url: str):
    import webview

    window = webview.create_window(
        title            = WINDOW_TITLE,
        url              = url,
        width            = 1440,
        height           = 880,
        min_size         = (960, 620),
        resizable        = True,
        background_color = "#030810",
        js_api           = JarvisAPI(),
    )
    window.events.closing += lambda: sys.exit(0)

    # Vyber GUI backend
    try:
        import gi
        gui = "gtk"
    except ImportError:
        gui = "qt"

    print(f"  Spouštím okno ({gui}) → {url}")
    webview.start(gui=gui)


def run_browser(url: str):
    """Fallback — otevře v systémovém prohlížeči."""
    import webbrowser
    print(f"\n  ✓ JARVIS UI → {url}")
    print("  Otevírám v prohlížeči...")
    webbrowser.open(url)
    print("  Ctrl+C pro ukončení")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nJARVIS zastaven.")
        sys.exit(0)


# ── Main ──────────────────────────────────────────────

def main():
    print(f"JARVIS Desktop v4.3")

    # Nastav React build cestu v config
    if not WEB_DIST.exists() and not DEV_MODE:
        print("  web_dist/ nenalezen — sestavuji React...")
        web_dir = ROOT / "web"
        if web_dir.exists():
            subprocess.run(
                ["npm", "run", "build"],
                cwd=web_dir, capture_output=True)

    # Spusť backend
    start_backend()

    # Zvol URL
    if DEV_MODE:
        print("  Dev mód — čekám na localhost:3000...")
        if wait_for_url(DEV_URL, timeout=30):
            url = DEV_URL
        else:
            print("  ⚠ Dev server nespuštěn — spusť: cd web && npm run dev")
            sys.exit(1)
    else:
        print("  Čekám na backend...", end=" ", flush=True)
        if wait_for_url(f"{BACKEND_URL}/api/status", timeout=12):
            url = BACKEND_URL
            print("✓")
        elif WEB_DIST.exists():
            url = str(WEB_DIST / "index.html")
            print(f"⚠ timeout — lokální soubory")
        else:
            url = BACKEND_URL
            print("⚠ timeout")

    # Spusť okno
    try:
        import webview
        run_webview(url)
    except Exception as e:
        print(f"  pywebview selhal: {e}")
        print("  → Fallback na prohlížeč")
        run_browser(url)


if __name__ == "__main__":
    main()
