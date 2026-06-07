#!/usr/bin/env python3
"""Generate README demo GIF (terminal-style animation)."""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("pip install Pillow")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo.gif"

FRAMES = [
    ("JARVIS v5.4 — Copilot · Agent · PC", [
        "You:  přehled o PC",
        "JARVIS: 🖥️ CPU 12% | RAM 32% | Cursor aktivní",
    ]),
    ("", [
        "You:  co mám na obrazovce?",
        "JARVIS: V popředí Cursor — Firefox otevřený",
    ]),
    ("", [
        "You:  jaké je počasí v Praze?",
        "JARVIS: ⛅ Praha: Polojasno, 21°C",
    ]),
    ("", [
        "You:  najdi async knihovny a ulož poznámku",
        "Agent: 🤖 Plán → vyhledám → shrnu → uložím",
        "JARVIS: Hotovo. Poznámka uložena.",
    ]),
]

W, H = 720, 280
BG = (12, 18, 32)
CYAN = (0, 210, 255)
TEXT = (220, 230, 245)
MUTED = (120, 140, 170)


def _font(size: int):
    for name in ("DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", "FreeMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_frame(title: str, lines: list[str]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(18)
    body_f = _font(15)
    draw.rectangle([(0, 0), (W, 44)], fill=(20, 30, 55))
    draw.text((16, 12), title or "JARVIS — Local AI OS", fill=CYAN, font=title_f)
    y = 58
    for i, line in enumerate(lines):
        color = CYAN if line.startswith("You:") else TEXT if line.startswith("JARVIS:") else MUTED
        if line.startswith("Agent:"):
            color = (180, 120, 255)
        draw.text((20, y), line, fill=color, font=body_f)
        y += 28
    draw.rectangle([(0, H - 3), (W, H)], fill=CYAN)
    return img


def main() -> None:
    images = []
    for title, lines in FRAMES:
        for _ in range(12):
            images.append(render_frame(title, lines))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        OUT,
        save_all=True,
        append_images=images[1:],
        duration=350,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUT} ({len(images)} frames)")


if __name__ == "__main__":
    main()
