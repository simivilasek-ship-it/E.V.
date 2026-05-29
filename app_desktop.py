"""
JARVIS Desktop App
Nativní okno s React HUD UI — pywebview + FastAPI backend.

Spuštění:
  python app_desktop.py

Nebo přes start_jarvis.sh (automaticky detekuje desktop vs headless).
"""
from __future__ import annotations

import sys
import os
import threading
import time
import signal
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Cesty ────────────────────────────────────────────
ROOT       = Path(__file__).parent
WEB_DIST   = ROOT / "web_dist"
BACKEND_PORT = 8002
WINDOW_TITLE = "JARVIS v4.3"

# ── Spuštění FastAPI backendu ─────────────────────────

def start_backend():
    """Spustí dashboard FastAPI server v daemon vlákně."""
    try:
        import uvicorn
        from dashboard import app
        uvicorn.run(app, host="127.0.0.1", port=BACKEND_PORT,
                    log_level="warning", access_log=False)
    except Exception as e:
        logger.error(f"Backend selhal: {e}")


def wait_for_backend(timeout: float = 10.0) -> bool:
    """Čeká dokud backend nezačne odpovídat na /health."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


# ── API pro JavaScript ────────────────────────────────

class JarvisAPI:
    """
    Python ↔ JavaScript bridge.
    Metody jsou volatelné z JS: window.pywebview.api.metoda()
    """

    def get_version(self):
        return "4.3"

    def get_status(self):
        try:
            from config import CONFIG
            return {
                "model":   CONFIG.get("ollama_model", "?"),
                "backend": f"http://127.0.0.1:{BACKEND_PORT}",
            }
        except Exception:
            return {}

    def open_settings(self):
        """Otevře nastavení — GUI dialog nebo web endpoint."""
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{BACKEND_PORT}/api/config")
        except Exception:
            pass

    def minimize(self, window_id=None):
        pass  # pywebview handles this natively


# ── Hlavní funkce ─────────────────────────────────────

def main():
    try:
        import webview
    except ImportError:
        print("pywebview není nainstalován: pip install pywebview")
        sys.exit(1)

    # Spusť backend v pozadí
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    print("Spouštím JARVIS backend...", end=" ", flush=True)
    if wait_for_backend(timeout=12):
        print("✓")
    else:
        print("⚠ backend neodpovídá — spouštím UI bez backendu")

    url = f"http://127.0.0.1:{BACKEND_PORT}"

    # Fallback na lokální soubory pokud backend neodpovídá
    if not wait_for_backend(timeout=1) and WEB_DIST.exists():
        url = str(WEB_DIST / "index.html")
        print(f"Fallback na lokální soubory: {url}")

    api = JarvisAPI()

    window = webview.create_window(
        title       = WINDOW_TITLE,
        url         = url,
        width       = 1400,
        height      = 860,
        min_size    = (900, 600),
        resizable   = True,
        frameless   = False,
        easy_drag   = False,
        background_color = "#030810",
        js_api      = api,
    )

    def on_closing():
        logger.info("JARVIS Desktop: zavírám")
        sys.exit(0)

    window.events.closing += on_closing

    # Spusť webview (blokující)
    webview.start(
        debug       = "--debug" in sys.argv,
        http_server = False,  # backend běží samostatně
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
