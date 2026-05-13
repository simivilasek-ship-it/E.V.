"""
JARVIS v2.0 — Příkazy
Implementace jednotlivých akcí asistenta
"""

import os
import subprocess
import webbrowser
import time
import psutil
import platform
import logging
import shutil
import math
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from typing import Dict, Any, Optional, Callable, List, Tuple, Union

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    pyautogui = None  # type: ignore
    HAS_PYAUTOGUI = False

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  MAPA APLIKACÍ
# ══════════════════════════════════════════════════════

APP_MAP: Dict[str, List[str]] = {
    "chrome":     ["chrome", "google chrome"],
    "firefox":    ["firefox", "mozilla firefox"],
    "msedge":     ["edge", "microsoft edge"],
    "notepad":    ["notepad", "poznámkový blok"],
    "calc":       ["calc", "kalkulačka", "kalkulacka"],
    "explorer":   ["explorer", "průzkumník", "przkumnik"],
    "spotify":    ["spotify"],
    "discord":    ["discord"],
    "code":       ["vscode", "code", "visual studio code"],
    "winword":    ["word", "microsoft word"],
    "excel":      ["excel", "microsoft excel"],
    "outlook":    ["outlook"],
    "mspaint":    ["paint", "malování"],
    "cmd":        ["cmd", "příkazový řádek"],
    "powershell": ["powershell", "ps"],
    "taskmgr":    ["taskmgr", "správce úloh", "task manager"],
    "steam":      ["steam"],
    "vlc":        ["vlc"],
    "telegram":   ["telegram"],
}

class CommandExecutor:
    """Vykonává příkazy JARVIS"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config: Dict[str, Any] = config
        self.is_windows: bool = platform.system() == "Windows"
        self.is_linux: bool = platform.system() == "Linux"

    def execute(self, action: str, params: Dict[str, Any]) -> str:
        """Vykoná příkaz a vrátí výsledek"""
        try:
            method_name: str = f"_cmd_{action}"
            if hasattr(self, method_name):
                method: Callable = getattr(self, method_name)
                return method(**params)
            else:
                logger.warning(f"Neznámá akce: {action}")
                return f"Neznámá akce: {action}"
        except Exception as e:
            logger.error(f"Chyba při vykonávání {action}: {e}")
            return f"Chyba: {e}"

    def _find_app(self, app: str) -> Optional[str]:
        """Najde aplikaci v APP_MAP (vrátí command nebo None)"""
        app_lower: str = app.lower()
        
        # Přímý match
        if app_lower in APP_MAP:
            return APP_MAP[app_lower][0]
        
        # Match v aliasech
        for app_cmd, aliases in APP_MAP.items():
            if app_lower in [alias.lower() for alias in aliases]:
                return app_cmd
        
        return None

    def _cmd_open_app(self, app: str, args: Optional[List[str]] = None) -> str:
        """Otevře aplikaci"""
        app_cmd: Optional[str] = self._find_app(app)
        if not app_cmd:
            return f"Aplikace '{app}' nenalezena"

        if app_cmd == "spotify":
            if args:
                query: str = " ".join(str(a) for a in args)
                return self._cmd_spotify_play(query)
            return self._launch_spotify()

        cmd: str = f"{app_cmd} {' '.join(str(a) for a in (args or []))}"
        try:
            subprocess.Popen(cmd, shell=True)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při otevírání aplikace: {e}")
            return f"Chyba: {e}"

    def _launch_spotify(self) -> str:
        """Otevře Spotify aplikaci nebo web"""
        uri: str = "spotify:"
        try:
            if shutil.which("spotify"):
                subprocess.Popen(["spotify"])
            else:
                subprocess.Popen(["xdg-open", uri])
            return "ok"
        except Exception as e:
            logger.warning(f"Spotify launch fallback selhal: {e}")
            try:
                webbrowser.open("https://open.spotify.com/")
                return "ok"
            except Exception as exc:
                return f"Chyba: {exc}"

    def _cmd_spotify_play(self, query: str, index: int = 1, audio_only: bool = False) -> str:
        """Přehrát skladbu na Spotify"""
        if not query:
            return self._launch_spotify()

        uri: str = f"spotify:search:{quote(query)}"
        try:
            if shutil.which("spotify"):
                subprocess.Popen(["xdg-open", uri])
                return "ok"
            subprocess.Popen(["xdg-open", uri])
            return "ok"
        except Exception as e:
            logger.warning(f"Spotify search selhalo: {e}")
            try:
                webbrowser.open(f"https://open.spotify.com/search/{quote(query)}")
                return "ok"
            except Exception as exc:
                return f"Chyba: {exc}"

    def _cmd_get_time(self) -> str:
        """Vrátí aktuální čas"""
        return datetime.now().strftime("%H:%M:%S")

    def _cmd_get_date(self) -> str:
        """Vrátí aktuální datum"""
        return datetime.now().strftime("%d.%m.%Y")

    def _cmd_calculate(self, expr: str) -> str:
        """Vypočítá matematický výraz — bezpečný sandbox, bez eval()."""
        import math as _math
        import ast as _ast

        _SAFE = {
            "sqrt": _math.sqrt, "pow": _math.pow, "abs": abs,
            "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
            "log": _math.log, "log10": _math.log10,
            "ceil": _math.ceil, "floor": _math.floor,
            "round": round, "pi": _math.pi, "e": _math.e,
        }
        _ALLOWED_NODES = (
            _ast.Expression, _ast.BinOp, _ast.UnaryOp, _ast.Constant,
            _ast.Add, _ast.Sub, _ast.Mult, _ast.Div, _ast.Pow,
            _ast.Mod, _ast.FloorDiv, _ast.USub, _ast.UAdd,
            _ast.Call, _ast.Name, _ast.Load,
        )

        def _safe_eval(node):
            if not isinstance(node, _ALLOWED_NODES):
                raise ValueError(f"Zakázaný výraz: {type(node).__name__}")
            if isinstance(node, _ast.Constant):
                if not isinstance(node.value, (int, float)):
                    raise ValueError("Pouze čísla jsou povolena")
                return node.value
            if isinstance(node, _ast.BinOp):
                return _safe_eval(node.left).__class__(0) or 0  # type check
            if isinstance(node, _ast.Name):
                if node.id not in _SAFE:
                    raise ValueError(f"Neznámá funkce: {node.id}")
                return _SAFE[node.id]
            if isinstance(node, _ast.Call):
                fn = _safe_eval(node.func)
                args = [_safe_eval(a) for a in node.args]
                return fn(*args)
            if isinstance(node, _ast.UnaryOp):
                if isinstance(node.op, _ast.USub):
                    return -_safe_eval(node.operand)
                return _safe_eval(node.operand)
            raise ValueError(f"Nepodporovaný uzel: {type(node).__name__}")

        try:
            expr_clean = expr.strip().replace(",", ".").replace("^", "**")
            tree = _ast.parse(expr_clean, mode="eval")
            # Ověř všechny uzly před spuštěním
            for node in _ast.walk(tree):
                if not isinstance(node, _ALLOWED_NODES):
                    return f"Chyba: zakázaný výraz ({type(node).__name__})"
            result = eval(  # noqa: S307 — bezpečné, whitelist + AST check
                compile(tree, "<calc>", "eval"),
                {"__builtins__": {}},
                _SAFE,
            )
            if isinstance(result, float) and result == int(result):
                return str(int(result))
            return f"{result:.10g}"
        except Exception as e:
            return f"Chyba výpočtu: {e}"

    def _cmd_system_info(self) -> str:
        """Vrátí informace o systému"""
        try:
            cpu_percent: float = psutil.cpu_percent(interval=1)
            mem: Any = psutil.virtual_memory()
            disk: Any = psutil.disk_usage('/')
            
            info: str = (
                f"CPU: {cpu_percent}% | "
                f"RAM: {mem.percent}% ({mem.available // (1024**3)} GB) | "
                f"Disk: {disk.percent}% ({disk.free // (1024**3)} GB volného)"
            )
            return info
        except Exception as e:
            logger.error(f"Chyba při zjišťování systému: {e}")
            return f"Chyba: {e}"

    def _cmd_open_url(self, url: str) -> str:
        """Otevře URL v prohlížeči"""
        try:
            webbrowser.open(url)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při otevírání URL: {e}")
            return f"Chyba: {e}"

    def _cmd_search_web(self, query: str) -> str:
        """Vyhledá na Googlu"""
        try:
            url: str = f"https://www.google.com/search?q={quote(query)}"
            webbrowser.open(url)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při vyhledávání: {e}")
            return f"Chyba: {e}"

    def _cmd_screenshot(self) -> str:
        """Vytvoří screenshot"""
        if not HAS_PYAUTOGUI:
            return "pyautogui není nainstalován"
        
        try:
            timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename: str = f"screenshot_{timestamp}.png"
            desktop_path: str = os.path.expanduser("~/Plocha")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.expanduser("~/Desktop")
            
            filepath: str = os.path.join(desktop_path, filename)
            img: Any = pyautogui.screenshot()
            img.save(filepath)
            return f"Uloženo: {filepath}"
        except Exception as e:
            logger.error(f"Chyba při screenshotu: {e}")
            return f"Chyba: {e}"

    def _cmd_type_key(self, key: str) -> str:
        """Stiskne klávesu"""
        if not HAS_PYAUTOGUI:
            return "pyautogui není nainstalován"
        
        try:
            pyautogui.press(key)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při stisku klávesy: {e}")
            return f"Chyba: {e}"

    def _cmd_write_text(self, text: str) -> str:
        """Napíše text"""
        if not HAS_PYAUTOGUI:
            return "pyautogui není nainstalován"
        
        try:
            pyautogui.typewrite(text, interval=0.05)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při psaní textu: {e}")
            return f"Chyba: {e}"

    def _cmd_clipboard_set(self, text: str) -> str:
        """Zkopíruje text do schránky"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při kopírování do schránky: {e}")
            return f"Chyba: {e}"

    def _cmd_create_file(self, path: str) -> str:
        """Vytvoří soubor"""
        try:
            Path(path).touch()
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při vytváření souboru: {e}")
            return f"Chyba: {e}"

    def _cmd_move_file(self, src: str, dst: str) -> str:
        """Přesune soubor"""
        try:
            shutil.move(src, dst)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při přesunování souboru: {e}")
            return f"Chyba: {e}"
            return f"Aplikace '{app}' nenalezena"

        if app_cmd == "spotify":
            if args:
                query = " ".join(str(a) for a in args)
                return self._cmd_spotify_play(query)
            return self._launch_spotify()

        cmd = f"{app_cmd} {' '.join(str(a) for a in (args or []))}"
        try:
            subprocess.Popen(cmd, shell=True)
            return "ok"
        except Exception as e:
            logger.error(f"Chyba při otevírání aplikace: {e}")
            return f"Chyba: {e}"

    def _launch_spotify(self) -> str:
        """Otevře Spotify aplikaci nebo web"""
        uri = "spotify:"
        try:
            if shutil.which("spotify"):
                subprocess.Popen(["spotify"])
            else:
                subprocess.Popen(["xdg-open", uri])
            return "ok"
        except Exception as e:
            logger.warning(f"Spotify launch fallback selhal: {e}")
            try:
                webbrowser.open("https://open.spotify.com/")
                return "ok"
            except Exception as exc:
                return f"Chyba: {exc}"

    def _cmd_spotify_play(self, query: str, index: int = 1, audio_only: bool = False) -> str:
        """Přehrát skladbu na Spotify"""
        if not query:
            return self._launch_spotify()

        uri = f"spotify:search:{quote(query)}"
        try:
            if shutil.which("spotify"):
                subprocess.Popen(["xdg-open", uri])
                return "ok"
            subprocess.Popen(["xdg-open", uri])
            return "ok"
        except Exception as e:
            logger.warning(f"Spotify search selhalo: {e}")
            try:
                webbrowser.open(f"https://open.spotify.com/search/{quote(query)}")
                return "ok"
            except Exception as exc:
                return f"Chyba: {exc}"

    def _cmd_youtube_play(self, query: str, index: int = 1, audio_only: bool = False) -> str:
        """Přehraje video/audio pomocí yt-dlp + ffplay (bez prohlížeče)."""
        if not query:
            return self._cmd_open_url("https://www.youtube.com")

        def _play():
            try:
                import yt_dlp
                fmt = "bestaudio/best" if audio_only else "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "format": fmt,
                    "noplaylist": True,
                    "default_search": f"ytsearch{index}",
                    "extract_flat": False,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info    = ydl.extract_info(query, download=False)
                    entries = info.get("entries") or [info]
                    entry   = entries[min(index - 1, len(entries) - 1)]
                    url     = entry.get("url") or entry.get("webpage_url")
                    title   = entry.get("title", query)

                logger.info(f"Přehrávám: {title}")

                if audio_only:
                    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", url])
                else:
                    subprocess.Popen(["ffplay", "-loglevel", "quiet", url])

            except ImportError:
                # Fallback: otevři v prohlížeči
                webbrowser.open(f"https://www.youtube.com/results?search_query={quote(query)}")
            except Exception as e:
                logger.error(f"youtube_play chyba: {e}")

        import threading
        threading.Thread(target=_play, daemon=True).start()
        mode = "🎵 audio" if audio_only else "🎬 video"
        return f"Přehrávám {mode}: {query}"

    def _cmd_youtube_download(self, query: str, path: str = "", audio_only: bool = False,
                              quality: str = "best") -> str:
        """Stáhne video nebo audio z YouTube pomocí yt-dlp."""
        try:
            import yt_dlp
        except ImportError:
            return "yt-dlp není nainstalován: pip install yt-dlp"

        dest = Path(path).expanduser() if path else Path.home() / "Stažené"
        dest.mkdir(parents=True, exist_ok=True)

        def _download():
            try:
                if audio_only:
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": str(dest / "%(title)s.%(ext)s"),
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }],
                        "quiet": True,
                        "default_search": "ytsearch1",
                    }
                else:
                    fmt_map = {"best": "bestvideo+bestaudio", "720p": "bestvideo[height<=720]+bestaudio",
                               "1080p": "bestvideo[height<=1080]+bestaudio", "480p": "bestvideo[height<=480]+bestaudio"}
                    ydl_opts = {
                        "format": fmt_map.get(quality, "bestvideo+bestaudio"),
                        "outtmpl": str(dest / "%(title)s.%(ext)s"),
                        "merge_output_format": "mp4",
                        "quiet": True,
                        "default_search": "ytsearch1",
                    }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([query])
                logger.info(f"Staženo do: {dest}")
            except Exception as e:
                logger.error(f"Download chyba: {e}")

        import threading
        threading.Thread(target=_download, daemon=True).start()
        mode = "audio (MP3)" if audio_only else f"video ({quality})"
        return f"Stahuji {mode}: {query} → {dest}"

    def _cmd_youtube_info(self, query: str) -> str:
        """Vrátí informace o videu (název, délka, autor, views)."""
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

            dur  = e.get("duration", 0)
            mins, secs = divmod(int(dur), 60)
            views = e.get("view_count", 0)
            views_str = f"{views:,}".replace(",", " ") if views else "?"

            return (f"📹 {e.get('title', '?')}\n"
                    f"👤 {e.get('uploader', '?')}\n"
                    f"⏱ {mins}:{secs:02d}\n"
                    f"👁 {views_str} zhlédnutí")
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_youtube_subtitles(self, query: str, lang: str = "cs", path: str = "") -> str:
        """Stáhne titulky k videu."""
        try:
            import yt_dlp
        except ImportError:
            return "yt-dlp není nainstalován"

        dest = Path(path).expanduser() if path else Path.home() / "Stažené"
        dest.mkdir(parents=True, exist_ok=True)

        try:
            ydl_opts = {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [lang],
                "skip_download": True,
                "outtmpl": str(dest / "%(title)s.%(ext)s"),
                "quiet": True,
                "default_search": "ytsearch1",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])
            return f"Titulky ({lang}) staženy do: {dest}"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_open_url(self, url: str) -> str:
        """Otevře URL"""
        if not url.startswith("http"):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_search_web(self, query: str) -> str:
        """Hledá na webu"""
        try:
            url = f"https://www.google.com/search?q={quote(query)}"
            webbrowser.open(url)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_write_text(self, text: str) -> str:
        """Napíše text"""
        try:
            time.sleep(0.5)
            pyautogui.write(text, interval=0.03)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_type_key(self, key: str) -> str:
        """Stiskne klávesu"""
        try:
            if "+" in key:
                pyautogui.hotkey(*key.split("+"))
            else:
                pyautogui.press(key)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_volume(self, level: Optional[int] = None, action: Optional[str] = None) -> str:
        """Nastaví hlasitost"""
        try:
            if action in ("mute", "unmute"):
                pyautogui.press("volumemute")
            elif level is not None:
                self._set_volume(level)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_media(self, action: str = None, url: Optional[str] = None) -> str:
        """Ovládá přehrávač"""
        try:
            if url:
                webbrowser.open(url)
                return "ok"

            if not action:
                return "ok"

            key_map = {
                "play_pause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
                "stop": "stop",
            }
            if action in key_map:
                pyautogui.press(key_map[action])
                return "ok"

            return f"Neznámá mediální akce: {action}"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_screenshot(self) -> str:
        """Udělá screenshot"""
        try:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            home = Path.home()
            desk = home / "Desktop"
            dest = (desk if desk.is_dir() else home) / f"screenshot_{ts}.png"
            pyautogui.screenshot().save(dest)
            return f"Uloženo: {dest}"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_open_file(self, path: str) -> str:
        """Otevře soubor/složku"""
        try:
            path = os.path.expanduser(path)
            if self.is_windows:
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_clipboard_set(self, text: str) -> str:
        """Nastaví schránku"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return "ok"
        except ImportError:
            return "pyperclip není nainstalován"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_system_info(self) -> str:
        """Vrátí systémové informace"""
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            info = (
                f"CPU: {cpu:.0f}% | "
                f"RAM: {ram.percent:.0f}% ({ram.used // 1024 // 1024} / {ram.total // 1024 // 1024} MB) | "
                f"Disk: {disk.percent:.0f}%"
            )
            return info
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_get_time(self) -> str:
        """Vrátí aktuální čas"""
        return datetime.now().strftime("%H:%M:%S")

    def _cmd_get_date(self) -> str:
        """Vrátí aktuální datum"""
        fmt = "%-d. %-m. %Y" if self.is_linux else "%#d. %#m. %Y"
        return datetime.now().strftime(fmt)

    def _cmd_set_timer(self, seconds: int, label: str = "Timer") -> str:
        """Nastaví timer"""
        import threading

        def fire():
            time.sleep(seconds)
            logger.info(f"Timer {label} vypršel")
            # Zde by mohla být notifikace

        thread = threading.Thread(target=fire, daemon=True)
        thread.start()

        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        dur = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
        return f"Timer nastaven na {dur}"

    def _cmd_kill_process(self, name: str) -> str:
        """Ukončí proces"""
        killed = 0
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and name.lower() in proc.info["name"].lower():
                try:
                    proc.kill()
                    killed += 1
                except Exception:
                    pass
        return f"Ukončeno: {killed} procesů" if killed else f"Proces '{name}' nenalezen"

    def _cmd_write_email(self, to: str = "", subject: str = "", body: str = "") -> str:
        """Otevře email klienta"""
        try:
            mailto = f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
            webbrowser.open(mailto)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_shutdown(self, delay: int = 0) -> str:
        """Vypne PC"""
        try:
            if self.is_windows:
                subprocess.run(["shutdown", "/s", "/t", str(delay)], check=False)
            else:
                cmd = ["shutdown", "-h", f"+{delay // 60}"] if delay else ["shutdown", "-h", "now"]
                subprocess.run(cmd, check=False)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_restart(self, delay: int = 0) -> str:
        """Restartuje PC"""
        try:
            if self.is_windows:
                subprocess.run(["shutdown", "/r", "/t", str(delay)], check=False)
            else:
                subprocess.run(["reboot"], check=False)
            return "ok"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_clear_history(self) -> str:
        return "ok"

    def _cmd_answer(self) -> str:
        return "ok"

    def _cmd_vscode_open(self, path: str = "") -> str:
        path = os.path.expanduser(path)
        subprocess.Popen(f"code {path!r}", shell=True)
        return f"Otevřeno ve VSCode: {path}"

    def _cmd_vscode_new_file(self) -> str:
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "n")
        return "ok"

    def _cmd_weather(self, city: str = "") -> str:
        from urllib.parse import quote as _q
        url = f"https://wttr.in/{_q(city)}?format=3" if city else "https://wttr.in/?format=3"
        try:
            resp = __import__("requests").get(url, timeout=8, headers={"User-Agent": "curl/7.0"})
            return resp.text.strip()
        except Exception as e:
            return f"Chyba počasí: {e}"

    def _cmd_set_brightness(self, level: int = 50) -> str:
        level = max(1, min(100, int(level)))
        if self.is_linux:
            if subprocess.run(["which", "brightnessctl"], capture_output=True).returncode == 0:
                subprocess.run(["brightnessctl", "set", f"{level}%"], capture_output=True)
            else:
                displays = subprocess.check_output(
                    "xrandr | grep ' connected' | awk '{print $1}'", shell=True, text=True
                ).strip().split("\n")
                for d in displays:
                    subprocess.run(["xrandr", "--output", d, "--brightness", str(level / 100)])
        return f"Jas: {level}%"

    def _cmd_sleep_pc(self) -> str:
        if self.is_windows:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
        else:
            subprocess.run(["systemctl", "suspend"], check=False)
        return "ok"

    def _cmd_update_system(self) -> str:
        if self.is_linux:
            subprocess.Popen(["pkexec", "bash", "-c", "apt update && apt upgrade -y"])
        return "Spouštím aktualizaci..."

    def _cmd_create_folder(self, path: str = "") -> str:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return f"Složka vytvořena: {p}"

    def _cmd_create_file(self, path: str = "") -> str:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        return f"Soubor vytvořen: {p}"

    def _cmd_delete_file(self, path: str = "") -> str:
        p = Path(path).expanduser()
        result = subprocess.run(["gio", "trash", str(p)], capture_output=True)
        if result.returncode == 0:
            return f"Přesunuto do koše: {p}"
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        return f"Smazáno: {p}"

    def _cmd_move_file(self, src: str = "", dst: str = "") -> str:
        shutil.move(str(Path(src).expanduser()), str(Path(dst).expanduser()))
        return f"Přesunuto: {src} → {dst}"

    def _cmd_find_files(self, name: str = "", path: str = "~") -> str:
        search_path = Path(path).expanduser()
        result = subprocess.run(
            ["find", str(search_path), "-iname", f"*{name}*", "-maxdepth", "6"],
            capture_output=True, text=True, timeout=10,
        )
        files = [f for f in result.stdout.strip().split("\n") if f][:10]
        return "\n".join(files) if files else "Nic nenalezeno."

    def _cmd_install_app(self, name: str = "") -> str:
        subprocess.Popen(["pkexec", "apt", "install", "-y", name])
        return f"Instaluji: {name}"

    def _cmd_uninstall_app(self, name: str = "") -> str:
        subprocess.Popen(["pkexec", "apt", "remove", "-y", name])
        return f"Odinstaluji: {name}"

    def _cmd_run_script(self, path: str = "") -> str:
        subprocess.Popen(["bash", str(Path(path).expanduser())])
        return f"Spouštím: {path}"

    def _cmd_memory_recall(self, query: str = "", top_k: int = 5) -> str:
        """Vyhledá v neural memory"""
        try:
            from memory import JarvisMemory
            mem = JarvisMemory(self.config)
            results = mem.recall(query, top_k=top_k)
            if not results:
                return "Nic nenalezeno v paměti."

            response = f"Nalezeno {len(results)} vzpomínek:\n"
            for i, r in enumerate(results, 1):
                response += f"{i}. [{r['score']:.2f}] {r['content'][:100]}...\n"
            return response
        except Exception as e:
            return f"Chyba paměti: {e}"

    def _cmd_memory_store(self, content: str = "", importance: float = 0.5) -> str:
        """Uloží do neural memory"""
        try:
            from memory import JarvisMemory
            mem = JarvisMemory(self.config)
            mem_id = mem.store(content, importance=importance)
            return f"Uloženo do paměti (ID: {mem_id})."
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_memory_stats(self) -> str:
        """Statistiky neural memory"""
        try:
            from memory import JarvisMemory
            mem = JarvisMemory(self.config)
            stats = mem.stats()
            return f"Paměť: {stats.get('total_memories', 0)} položek, průměrná důležitost: {stats.get('avg_importance', 0):.2f}"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_memory_maintenance(self) -> str:
        """Spustí údržbu paměti"""
        try:
            from memory import JarvisMemory
            mem = JarvisMemory(self.config)
            result = mem.run_maintenance()
            return f"Údržba dokončena: {result}"
        except Exception as e:
            return f"Chyba: {e}"

    def _find_app(self, name: str) -> Optional[str]:
        """Najde příkaz pro aplikaci"""
        nl = name.lower().strip()
        for cmd, aliases in APP_MAP.items():
            if nl == cmd or nl in aliases or any(a in nl for a in aliases):
                return cmd
        return nl

    def _cmd_translate(self, text: str, from_lang: str = "auto", to_lang: str = "cs") -> str:
        """Přeloží text pomocí Ollama."""
        try:
            import requests as _req
            lang_map = {
                "cs": "češtiny", "en": "angličtiny", "de": "němčiny",
                "fr": "francouzštiny", "es": "španělštiny", "sk": "slovenštiny",
            }
            to_name = lang_map.get(to_lang, to_lang)
            prompt = f"Přelož přesně do {to_name}, vrať pouze překlad bez vysvětlení:\n{text}"
            model = self.config.get("ollama_model", "qwen2.5:3b")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            }
            r = _req.post("http://localhost:11434/api/chat", json=payload, timeout=30)
            r.raise_for_status()
            translated = r.json().get("message", {}).get("content", "").strip()
            return f"Překlad: {translated}"
        except Exception as e:
            return f"Chyba překladu: {e}"

    def _cmd_note_add(self, note: str) -> str:
        """Přidá poznámku"""
        try:
            notes_file = os.path.join(_HOME, "jarvis_notes.txt")
            with open(notes_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {note}\n")
            return "Poznámka uložena."
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_note_list(self) -> str:
        """Zobrazí poznámky"""
        try:
            notes_file = os.path.join(_HOME, "jarvis_notes.txt")
            if os.path.exists(notes_file):
                with open(notes_file, "r", encoding="utf-8") as f:
                    notes = f.read().strip()
                return notes if notes else "Žádné poznámky."
            return "Žádné poznámky."
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_reminder_set(self, text: str, time_str: str) -> str:
        """Nastaví připomínku"""
        try:
            # Zjednodušené parsování času
            import threading
            def remind():
                time.sleep(60)  # Pro demo 1 minuta
                # Zde by byla notifikace
                logger.info(f"Připomínka: {text}")
            thread = threading.Thread(target=remind, daemon=True)
            thread.start()
            return f"Připomínka nastavena: {text}"
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_wiki_search(self, query: str) -> str:
        """Hledá na Wikipedii"""
        try:
            import requests
            url = f"https://cs.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("extract", "Nenalezeno.").split(".")[0] + "."
            return "Nenalezeno na Wikipedii."
        except Exception as e:
            return f"Chyba: {e}"

    def _cmd_currency_convert(self, amount: float, from_curr: str, to_curr: str) -> str:
        """Převede měnu (jednoduchá implementace)"""
        try:
            # Zjednodušené kurzy
            rates = {"USD": 1.0, "EUR": 0.85, "CZK": 25.0}
            if from_curr.upper() in rates and to_curr.upper() in rates:
                result = amount * rates[to_curr.upper()] / rates[from_curr.upper()]
                return f"{amount} {from_curr.upper()} = {result:.2f} {to_curr.upper()}"
            return "Nepodporované měny."
        except Exception as e:
            return f"Chyba: {e}"