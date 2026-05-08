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
from datetime import datetime
from urllib.parse import quote
from typing import Dict, Any, Optional

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

APP_MAP = {
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

    def __init__(self, config: dict):
        self.config = config
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"

    def execute(self, action: str, params: Dict[str, Any]) -> str:
        """Vykoná příkaz a vrátí výsledek"""
        try:
            method_name = f"_cmd_{action}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                return method(**params)
            else:
                logger.warning(f"Neznámá akce: {action}")
                return f"Neznámá akce: {action}"
        except Exception as e:
            logger.error(f"Chyba při vykonávání {action}: {e}")
            return f"Chyba: {e}"

    def _cmd_open_app(self, app: str, args: Optional[list] = None) -> str:
        """Otevře aplikaci"""
        app_cmd = self._find_app(app)
        if not app_cmd:
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
        """Přehrát video na YouTube"""
        if not query:
            return self._cmd_open_url("https://www.youtube.com")
        try:
            url = f"https://www.youtube.com/results?search_query={quote(query)}"
            webbrowser.open(url)
            return "ok"
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
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            home = os.path.expanduser("~")
            desk = os.path.join(home, "Desktop")
            dest = os.path.join(desk if os.path.isdir(desk) else home, f"screenshot_{ts}.png")
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
        """Vymaže historii (implementováno v hlavním engine)"""
        return "ok"

    def _cmd_answer(self) -> str:
        """Jen odpověď bez akce"""
        return "ok"

    def _find_app(self, name: str) -> Optional[str]:
        """Najde příkaz pro aplikaci"""
        nl = name.lower().strip()
        for cmd, aliases in APP_MAP.items():
            if nl == cmd or nl in aliases or any(a in nl for a in aliases):
                return cmd
        return nl

    def _set_volume(self, level: int) -> None:
        """Nastaví hlasitost"""
        level = max(0, min(100, level))

        # Windows specifické
        if self.is_windows:
            try:
                import ctypes
                v = int(level / 100 * 0xFFFF)
                ctypes.windll.winmm.waveOutSetVolume(None, v | (v << 16))
                return
            except Exception:
                pass

        # Linux přes pactl
        if self.is_linux:
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
                    capture_output=True,
                    check=True
                )
                return
            except Exception:
                pass

        # Fallback přes pyautogui
        try:
            # Zjednodušený fallback - nefunguje přesně
            for _ in range(50):
                pyautogui.press("volumedown")
            for _ in range(level // 2):
                pyautogui.press("volumeup")
        except Exception:
            pass