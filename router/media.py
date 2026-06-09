"""
JARVIS router — media routing.
Handles music/Spotify/YouTube playback and screen vision commands.
"""
import re

from commands.utils import normalize_text as _norm
from .constants import _APPS, _SITES, _MUSIC_STOP


def route_music(text: str, t: str, sites: dict | None = None) -> tuple:
    """Handles music/play commands. Falls back to YouTube search."""
    _s = sites if sites is not None else _SITES

    if not re.search(r"\b(pust|zahraj|prehraj|spust|play)\b", t):
        return None, None

    audio_only = bool(re.search(r"\b(jen\s+zvuk|audio|mp3|poslouchat)\b", t))

    # If the query resolves to a known app → open the app, don't play music
    for app_name, app_cmd in _APPS.items():
        if _norm(app_name) in t.split():
            return f"Spouštím {app_name}.", {
                "action": "open_app", "params": {"app": app_cmd}}

    # If the query resolves to a known site with nothing else → open the site
    for site, url in _s.items():
        if site in t:
            rest = re.sub(rf"\b{site}\b", "", t)
            rest = _MUSIC_STOP.sub("", rest).strip()
            if len(rest) < 3:
                return f"Otevírám {site.capitalize()}.", {
                    "action": "open_url", "params": {"url": url}}

    query = _MUSIC_STOP.sub("", text).strip(" ,.-")
    if len(query) > 2:
        return f"Přehrávám: {query}.", {
            "action": "youtube_play",
            "params": {"query": query, "index": 1, "audio_only": audio_only}}

    return None, None


def route_vision(text: str, t: str) -> tuple:
    """Handles screen describe, OCR and webcam commands."""
    if (
        t in ("co vidis", "popis obrazovky", "co je na obrazovce")
        or re.search(r"\b(popís|popis|popiš|describe)\s+(obrazovku|screen|pc)\b", text, re.I)
        or re.search(r"\bco\s+(mam|máš|je)\s+na\s+obrazovce\b", t, re.I)
        or re.search(
            r"\b(co\s+(mam|máš|je|vidis|vidíš)|jaká\s+okna?)\b.*\b(obrazovk|screen|pc|počítač|pocitac)\b",
            t, re.I,
        )
        or re.search(
            r"\b(obrazovk|screen|pc|počítač|pocitac)\b.*\b(co\s+(mam|máš|je|vidis|vidíš)|otevren|otevřen)\b",
            t, re.I,
        )
        or re.search(
            r"\b(na\s+cem\s+pracuju|co\s+mam\s+(otevren|otevřen|spusten|spuštěn)|co\s+delam)\b",
            t, re.I,
        )
    ):
        return "Popisuji obrazovku.", {"action": "screen_describe", "params": {}}

    if re.search(r"\b(precti|prečti)\s+(text|obrazovku)|ocr\b", t, re.I):
        return "Čtu text z obrazovky.", {"action": "screen_ocr", "params": {}}

    if re.search(r"\b(kamera|webcam|co\s+vidi\s+kamera|koukni\s+kamerou)\b", t, re.I):
        return "Dívám se kamerou.", {"action": "webcam_describe", "params": {}}

    return None, None
