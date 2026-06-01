"""
JARVIS System Tray
Spustitelný samostatně: python -m desktop.tray
Předpokládá, že backend běží na BACKEND_URL (spusť scripts/start.sh nejdříve).
"""
from __future__ import annotations

import sys
import webbrowser

BACKEND_URL = "http://127.0.0.1:8002"

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _make_icon() -> "Image.Image":
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer glow
    draw.ellipse((2, 2, 62, 62), fill=(0, 60, 80, 80))
    # Core circle
    draw.ellipse((8, 8, 56, 56), fill=(0, 212, 255, 255))
    return img


def run_tray(backend_url: str = BACKEND_URL) -> None:
    if not HAS_TRAY:
        print("Nainstaluj: pip install pystray pillow")
        sys.exit(1)

    def open_dashboard(_icon=None, _item=None):
        webbrowser.open(backend_url)

    def quit_tray(icon, _item):
        icon.stop()
        sys.exit(0)

    icon = pystray.Icon(
        "JARVIS",
        _make_icon(),
        "JARVIS",
        menu=pystray.Menu(
            pystray.MenuItem("Otevřít dashboard", open_dashboard, default=True),
            pystray.MenuItem("Ukončit", quit_tray),
        ),
    )
    print(f"JARVIS tray aktivní ({backend_url}) — Ctrl+C nebo 'Ukončit' pro exit")
    icon.run()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else BACKEND_URL
    run_tray(url)
