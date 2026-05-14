"""Mediální příkazy: YouTube, přehrávání, screenshot, klávesnice."""

import logging
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False


def cmd_screenshot() -> str:
    if not HAS_PYAUTOGUI:
        return "pyautogui není nainstalován"
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    home = Path.home()
    desk = home / "Plocha"
    if not desk.is_dir():
        desk = home / "Desktop"
    dest = (desk if desk.is_dir() else home) / f"screenshot_{ts}.png"
    pyautogui.screenshot().save(dest)
    return f"Uloženo: {dest}"


def cmd_type_key(key: str) -> str:
    if not HAS_PYAUTOGUI:
        return "pyautogui není nainstalován"
    if "+" in key:
        pyautogui.hotkey(*key.split("+"))
    else:
        pyautogui.press(key)
    return "ok"


def cmd_write_text(text: str) -> str:
    if not HAS_PYAUTOGUI:
        return "pyautogui není nainstalován"
    time.sleep(0.5)
    pyautogui.write(text, interval=0.03)
    return "ok"


def cmd_media(action: str = None, url: str = None) -> str:
    if url:
        webbrowser.open(url)
        return "ok"
    if not action:
        return "ok"
    key_map = {
        "play_pause": "playpause",
        "next":       "nexttrack",
        "prev":       "prevtrack",
        "stop":       "stop",
    }
    if action in key_map:
        if HAS_PYAUTOGUI:
            pyautogui.press(key_map[action])
        return "ok"
    return f"Neznámá mediální akce: {action}"


def cmd_set_timer(seconds: int, label: str = "Timer") -> str:
    def fire():
        time.sleep(seconds)
        logger.info(f"Timer '{label}' vypršel")

    threading.Thread(target=fire, daemon=True).start()
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    dur = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
    return f"Timer nastaven na {dur}"


def cmd_youtube_play(query: str, index: int = 1, audio_only: bool = False) -> str:
    if not query:
        webbrowser.open("https://www.youtube.com")
        return "ok"

    def _play():
        try:
            import yt_dlp
            fmt = ("bestaudio/best" if audio_only
                   else "bestvideo[height<=720]+bestaudio/best[height<=720]/best")
            ydl_opts = {
                "quiet": True, "no_warnings": True, "format": fmt,
                "noplaylist": True, "default_search": f"ytsearch{index}",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info    = ydl.extract_info(query, download=False)
                entries = info.get("entries") or [info]
                entry   = entries[min(index - 1, len(entries) - 1)]
                url     = entry.get("url") or entry.get("webpage_url")
                title   = entry.get("title", query)

            logger.info(f"Přehrávám: {title}")
            player_cmd = (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", url]
                          if audio_only else ["ffplay", "-loglevel", "quiet", url])
            subprocess.Popen(player_cmd)
        except ImportError:
            webbrowser.open(f"https://www.youtube.com/results?search_query={quote(query)}")
        except Exception as e:
            logger.error(f"youtube_play chyba: {e}")

    threading.Thread(target=_play, daemon=True).start()
    return f"Přehrávám {'🎵 audio' if audio_only else '🎬 video'}: {query}"


def cmd_youtube_download(query: str, path: str = "", audio_only: bool = False,
                         quality: str = "best") -> str:
    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp není nainstalován: pip install yt-dlp"

    dest = Path(path).expanduser() if path else Path.home() / "Stažené"
    dest.mkdir(parents=True, exist_ok=True)

    def _download():
        try:
            fmt_map = {
                "best": "bestvideo+bestaudio",
                "720p": "bestvideo[height<=720]+bestaudio",
                "1080p": "bestvideo[height<=1080]+bestaudio",
                "480p": "bestvideo[height<=480]+bestaudio",
            }
            if audio_only:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": str(dest / "%(title)s.%(ext)s"),
                    "postprocessors": [{"key": "FFmpegExtractAudio",
                                        "preferredcodec": "mp3", "preferredquality": "192"}],
                    "quiet": True, "default_search": "ytsearch1",
                }
            else:
                ydl_opts = {
                    "format": fmt_map.get(quality, "bestvideo+bestaudio"),
                    "outtmpl": str(dest / "%(title)s.%(ext)s"),
                    "merge_output_format": "mp4",
                    "quiet": True, "default_search": "ytsearch1",
                }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])
            logger.info(f"Staženo do: {dest}")
        except Exception as e:
            logger.error(f"Download chyba: {e}")

    threading.Thread(target=_download, daemon=True).start()
    return f"Stahuji {'audio (MP3)' if audio_only else f'video ({quality})'}: {query} → {dest}"


def cmd_youtube_info(query: str) -> str:
    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp není nainstalován"
    try:
        ydl_opts = {"quiet": True, "no_warnings": True,
                    "extract_flat": True, "default_search": "ytsearch1"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info    = ydl.extract_info(query, download=False)
            entries = info.get("entries") or [info]
            e       = entries[0]
        dur = e.get("duration", 0)
        mins, secs = divmod(int(dur), 60)
        views = e.get("view_count", 0)
        views_str = f"{views:,}".replace(",", " ") if views else "?"
        return (f"📹 {e.get('title', '?')}\n"
                f"👤 {e.get('uploader', '?')}\n"
                f"⏱ {mins}:{secs:02d}\n"
                f"👁 {views_str} zhlédnutí")
    except Exception as e:
        return f"Chyba: {e}"


def cmd_youtube_subtitles(query: str, lang: str = "cs", path: str = "") -> str:
    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp není nainstalován"
    dest = Path(path).expanduser() if path else Path.home() / "Stažené"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        ydl_opts = {
            "writesubtitles": True, "writeautomaticsub": True,
            "subtitleslangs": [lang], "skip_download": True,
            "outtmpl": str(dest / "%(title)s.%(ext)s"),
            "quiet": True, "default_search": "ytsearch1",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        return f"Titulky ({lang}) staženy do: {dest}"
    except Exception as e:
        return f"Chyba: {e}"
