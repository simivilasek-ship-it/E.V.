"""
JARVIS v2.0 — Hlasový asistent
Spuštění:  python jarvis.py
Závislosti: pip install customtkinter requests speechrecognition pyaudio pyautogui psutil pyperclip edge-tts
Volitelné:  pip install pycaw comtypes   (přesné nastavení hlasitosti Windows)
"""

import threading
import subprocess
import webbrowser
import os
import platform
import json
import asyncio
import tempfile
import time
import re
import requests
import pyautogui
import psutil
import customtkinter as ctk
from datetime import datetime
from collections import deque
from urllib.parse import quote

# ══════════════════════════════════════════════════════
#  VOLITELNÉ ZÁVISLOSTI
# ══════════════════════════════════════════════════════

try:
    import speech_recognition as sr
    _recognizer = sr.Recognizer()
    _recognizer.pause_threshold = 1.0
    _recognizer.energy_threshold = 300
    _recognizer.dynamic_energy_threshold = True
    HAS_SR = True
except ImportError:
    HAS_SR = False

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"

# ══════════════════════════════════════════════════════
#  KONFIGURACE
# ══════════════════════════════════════════════════════

_DEFAULTS = {
    "ollama_url":   "http://localhost:11434/api/chat",
    "ollama_model": "llama3.1:8b",
    "tts_enabled":  True,
    "tts_voice":    "cs-CZ-AntoninNeural",
    "history_size": 20,
    "window_size":  "600x820",
}

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
try:
    with open(_cfg_path, encoding="utf-8") as _f:
        _cfg = {**_DEFAULTS, **json.load(_f)}
except FileNotFoundError:
    _cfg = _DEFAULTS
except Exception as e:
    print(f"[config] Chyba: {e}")
    _cfg = _DEFAULTS

OLLAMA_URL   = _cfg["ollama_url"]
OLLAMA_MODEL = _cfg["ollama_model"]

# ══════════════════════════════════════════════════════
#  TTS — edge-tts (kvalitní hlas) + pyttsx3 fallback
# ══════════════════════════════════════════════════════

_tts_lock = threading.Lock()
_tts_enabled: bool = _cfg.get("tts_enabled", True)
_tts_voice: str    = _cfg.get("tts_voice", "cs-CZ-AntoninNeural")

try:
    import edge_tts as _edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

# Najdi audio přehrávač (Linux)
def _find_player() -> str | None:
    for p in ("mpg123", "ffplay", "cvlc", "mplayer"):
        if subprocess.run(["which", p], capture_output=True).returncode == 0:
            return p
    return None

_audio_player = _find_player() if IS_LINUX else None

# Fallback pyttsx3
try:
    import pyttsx3 as _pyttsx3
    _tts_engine = _pyttsx3.init()
    _tts_engine.setProperty("rate", 170)
    for _v in _tts_engine.getProperty("voices"):
        if any(x in (_v.id + _v.name).lower() for x in ("czech", "cs-cz", "zuzana", "jakub")):
            _tts_engine.setProperty("voice", _v.id)
            break
    HAS_PYTTSX3 = True
except Exception:
    HAS_PYTTSX3 = False

HAS_TTS = HAS_EDGE_TTS or HAS_PYTTSX3


async def _edge_say(text: str):
    communicate = _edge_tts.Communicate(text, _tts_voice)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = f.name
    await communicate.save(path)
    try:
        if IS_WINDOWS:
            subprocess.run(["start", "/wait", "", path], shell=True, capture_output=True)
        elif _audio_player == "ffplay":
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path])
        elif _audio_player:
            subprocess.run([_audio_player, "-q", path], capture_output=True)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def speak(text: str):
    if not _tts_enabled or not HAS_TTS:
        return

    def _run():
        with _tts_lock:
            if HAS_EDGE_TTS and (IS_WINDOWS or _audio_player):
                try:
                    asyncio.run(_edge_say(text))
                    return
                except Exception:
                    pass
            if HAS_PYTTSX3:
                try:
                    _tts_engine.say(text)
                    _tts_engine.runAndWait()
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True).start()

# ══════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ══════════════════════════════════════════════════════

SYSTEM_PROMPT = """Jsi JARVIS, inteligentní hlasový asistent na PC. Komunikuješ POUZE v češtině.
Jsi stručný, přesný a přátelský. Vždy vrátíš validní JSON, nic jiného.

FORMÁT ODPOVĚDI:
{
  "action": "AKCE",
  "params": {},
  "message": "Co říkáš uživateli (česky, max 1-2 věty)"
}

DOSTUPNÉ AKCE:
- open_app      — otevři aplikaci,       params: {"app": "název"}
- open_url      — otevři URL,            params: {"url": "https://..."}
- search_web    — hledej na webu,        params: {"query": "výraz"}
- write_text    — napiš text,            params: {"text": "text"}
- type_key      — stiskni klávesu,       params: {"key": "ctrl+c"} nebo {"key": "enter"}
- volume        — hlasitost,             params: {"level": 0-100} nebo {"action": "mute"/"unmute"}
- media         — přehrávač,             params: {"action": "play_pause"/"next"/"prev"/"stop"}
- screenshot    — screenshot,            params: {}
- open_file     — otevři soubor/složku, params: {"path": "cesta"}
- clipboard_set — kopíruj do schránky,  params: {"text": "text"}
- system_info   — CPU, RAM, disk,        params: {}
- get_time      — aktuální čas,          params: {}
- get_date      — aktuální datum,        params: {}
- set_timer     — timer,                 params: {"seconds": 60, "label": "popis"}
- kill_process  — ukonči proces,         params: {"name": "název.exe"}
- write_email   — otevři email,          params: {"to": "", "subject": "", "body": ""}
- shutdown      — vypni PC,              params: {"delay": 0}
- restart       — restartuj PC,          params: {"delay": 0}
- clear_history — vymaž paměť,           params: {}
- answer        — jen odpověz,           params: {}

PŘÍKLADY:
"Otevři Chrome"       → {"action": "open_app", "params": {"app": "chrome"}, "message": "Otevírám Chrome."}
"Počasí Praha"        → {"action": "search_web", "params": {"query": "počasí Praha"}, "message": "Hledám počasí."}
"Hlasitost 60"        → {"action": "volume", "params": {"level": 60}, "message": "Nastavuji hlasitost na 60%."}
"Kolik je hodin?"     → {"action": "get_time", "params": {}, "message": "Zjišťuji čas."}
"Timer 5 minut"       → {"action": "set_timer", "params": {"seconds": 300, "label": "Timer"}, "message": "Timer nastaven."}
"Jak se jmenuješ?"    → {"action": "answer", "params": {}, "message": "Jsem JARVIS, tvůj osobní asistent."}

Odpovídej POUZE validním JSON, nic jiného."""

# ══════════════════════════════════════════════════════
#  MAPA APLIKACÍ
# ══════════════════════════════════════════════════════

APP_MAP = {
    "chrome":     ["chrome", "google chrome"],
    "firefox":    ["firefox", "mozilla firefox"],
    "msedge":     ["edge", "microsoft edge"],
    "notepad":    ["notepad", "poznámkový blok"],
    "calc":       ["calc", "kalkulačka", "kalkulacka"],
    "explorer":   ["explorer", "průzkumník"],
    "spotify":    ["spotify"],
    "discord":    ["discord"],
    "code":       ["vscode", "code", "visual studio code"],
    "winword":    ["word", "microsoft word"],
    "excel":      ["excel", "microsoft excel"],
    "outlook":    ["outlook"],
    "mspaint":    ["paint", "malování"],
    "cmd":        ["cmd", "příkazový řádek"],
    "powershell": ["powershell", "ps"],
    "taskmgr":    ["taskmgr", "správce úloh"],
    "steam":      ["steam"],
    "vlc":        ["vlc"],
    "telegram":   ["telegram"],
}

def _find_app(name: str) -> str:
    nl = name.lower().strip()
    for cmd, aliases in APP_MAP.items():
        if nl == cmd or nl in aliases or any(a in nl for a in aliases):
            return cmd
    return nl

# ══════════════════════════════════════════════════════
#  HLASITOST
# ══════════════════════════════════════════════════════

def _set_volume(level: int):
    level = max(0, min(100, level))
    if HAS_PYCAW and IS_WINDOWS:
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return
        except Exception:
            pass
    if IS_WINDOWS:
        try:
            import ctypes
            v = int(level / 100 * 0xFFFF)
            ctypes.windll.winmm.waveOutSetVolume(None, v | (v << 16))
            return
        except Exception:
            pass
    elif IS_LINUX:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True)

def _get_volume() -> int:
    if HAS_PYCAW and IS_WINDOWS:
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            return int(vol.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            pass
    if IS_LINUX:
        try:
            out = subprocess.check_output(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"], stderr=subprocess.DEVNULL,
            ).decode()
            m = re.search(r"(\d+)%", out)
            if m:
                return int(m.group(1))
        except Exception:
            pass
    return -1

# ══════════════════════════════════════════════════════
#  AKCE
# ══════════════════════════════════════════════════════

_history: deque = deque(maxlen=_cfg["history_size"])

def execute_action(action: str, params: dict, notify=None) -> str:
    def _notify(msg, tag="info"):
        if notify:
            notify(msg, tag)

    try:
        if action == "open_app":
            app = _find_app(params.get("app", ""))
            subprocess.Popen(app, shell=True)
            return "ok"

        elif action == "open_url":
            url = params.get("url", "")
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            return "ok"

        elif action == "search_web":
            webbrowser.open(f"https://www.google.com/search?q={quote(params.get('query', ''))}")
            return "ok"

        elif action == "write_text":
            text = params.get("text", "")
            time.sleep(0.5)
            if HAS_CLIPBOARD:
                old = pyperclip.paste()
                pyperclip.copy(text)
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyperclip.copy(old)
            else:
                pyautogui.write(text, interval=0.03)
            return "ok"

        elif action == "type_key":
            key = params.get("key", "")
            if "+" in key:
                pyautogui.hotkey(*key.split("+"))
            else:
                pyautogui.press(key)
            return "ok"

        elif action == "volume":
            act   = params.get("action", "")
            level = params.get("level")
            if act in ("mute", "unmute"):
                pyautogui.press("volumemute")
            elif level is not None:
                _set_volume(int(level))
                return f"Hlasitost: {level}%"
            return "ok"

        elif action == "media":
            key_map = {"play_pause": "playpause", "next": "nexttrack", "prev": "prevtrack", "stop": "stop"}
            cmd = params.get("action", "")
            if cmd in key_map:
                pyautogui.press(key_map[cmd])
            return "ok"

        elif action == "screenshot":
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            home = os.path.expanduser("~")
            desk = os.path.join(home, "Desktop")
            dest = os.path.join(desk if os.path.isdir(desk) else home, f"screenshot_{ts}.png")
            pyautogui.screenshot().save(dest)
            return f"Uloženo: {dest}"

        elif action == "open_file":
            path = params.get("path", "")
            if IS_WINDOWS:
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
            return "ok"

        elif action == "clipboard_set":
            if HAS_CLIPBOARD:
                pyperclip.copy(params.get("text", ""))
            return "ok"

        elif action == "system_info":
            cpu  = psutil.cpu_percent(interval=0.5)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            info = (f"CPU: {cpu:.0f}%  |  "
                    f"RAM: {ram.percent:.0f}% ({ram.used//1024//1024}/{ram.total//1024//1024} MB)  |  "
                    f"Disk: {disk.percent:.0f}%")
            _notify(info, "muted")
            return info

        elif action == "get_time":
            t = datetime.now().strftime("%H:%M:%S")
            _notify(f"Čas: {t}", "accent")
            return t

        elif action == "get_date":
            fmt = "%#d. %#m. %Y" if IS_WINDOWS else "%-d. %-m. %Y"
            d = datetime.now().strftime(fmt)
            _notify(f"Datum: {d}", "accent")
            return d

        elif action == "set_timer":
            seconds = int(params.get("seconds", 60))
            label   = params.get("label", "Timer")

            def _fire():
                time.sleep(seconds)
                _notify(f"⏰ {label} — čas vypršel!", "success")
                speak(f"{label} — čas vypršel!")

            threading.Thread(target=_fire, daemon=True).start()
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            dur = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
            return f"Timer nastaven na {dur}"

        elif action == "kill_process":
            name   = params.get("name", "")
            killed = 0
            for proc in psutil.process_iter(["name"]):
                if proc.info["name"] and name.lower() in proc.info["name"].lower():
                    try:
                        proc.kill()
                        killed += 1
                    except Exception:
                        pass
            return f"Ukončeno: {killed} procesů." if killed else f"Proces '{name}' nenalezen."

        elif action == "write_email":
            to, subject, body = params.get("to",""), params.get("subject",""), params.get("body","")
            webbrowser.open(f"mailto:{to}?subject={quote(subject)}&body={quote(body)}")
            return "ok"

        elif action == "shutdown":
            delay = params.get("delay", 0)
            if IS_WINDOWS:
                subprocess.run(["shutdown", "/s", "/t", str(delay)], check=False)
            else:
                cmd = ["shutdown", "-h", f"+{delay//60}"] if delay else ["shutdown", "-h", "now"]
                subprocess.run(cmd, check=False)
            return "ok"

        elif action == "restart":
            delay = params.get("delay", 0)
            if IS_WINDOWS:
                subprocess.run(["shutdown", "/r", "/t", str(delay)], check=False)
            else:
                subprocess.run(["reboot"], check=False)
            return "ok"

        elif action == "clear_history":
            _history.clear()
            return "Historie vymazána."

        elif action == "answer":
            return "ok"

        return f"Neznámá akce: {action}"

    except Exception as e:
        return f"Chyba: {e}"

# ══════════════════════════════════════════════════════
#  OLLAMA — chat API s historií
# ══════════════════════════════════════════════════════

def ask_ollama(user_text: str) -> dict:
    _history.append({"role": "user", "content": user_text})

    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *list(_history)],
        "stream":   False,
        "options":  {"temperature": 0.1, "num_predict": 300},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "").strip()
        print(f"[OLLAMA] {raw[:200]}")  # debug do terminálu

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                _history.append({"role": "assistant", "content": raw})
                return result
            except json.JSONDecodeError:
                pass

        # Model nevrátil JSON — zobraz co řekl jako odpověď
        _history.append({"role": "assistant", "content": raw})
        clean = re.sub(r"[{}\[\]\"']", "", raw).strip()[:200]
        return {"action": "answer", "params": {}, "message": clean or "Nerozuměl jsem."}

    except requests.Timeout:
        _history.pop()
        return {"action": "answer", "params": {}, "message": "Ollama nereaguje (timeout 30s)."}
    except Exception as e:
        _history.pop()
        return {"action": "answer", "params": {}, "message": f"Chyba spojení: {e}"}

# ══════════════════════════════════════════════════════
#  ROZPOZNÁVÁNÍ ŘEČI
# ══════════════════════════════════════════════════════

def listen_microphone() -> str:
    if not HAS_SR:
        return ""
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = _recognizer.listen(source, timeout=10, phrase_time_limit=15)
    try:
        return _recognizer.recognize_google(audio, language="cs-CZ")
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        try:
            return _recognizer.recognize_sphinx(audio, language="cs-CZ")
        except Exception:
            return ""

# ══════════════════════════════════════════════════════
#  GUI — Chat rozhraní
# ══════════════════════════════════════════════════════

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

GOLD  = "#b06d00"
GOLDH = "#c87f10"
BG    = "#0d0b09"
BG2   = "#181310"
BG3   = "#221d16"
FG    = "#f0ead8"
MUTED = "#777777"
GREEN = "#4caf50"
RED   = "#e53935"
BLUE  = "#64b5f6"


class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS")
        self.geometry(_cfg["window_size"])
        self.minsize(440, 600)
        self.configure(fg_color=BG)
        self._is_listening = False
        self._thinking_job = None
        self._build_ui()
        self.after(300, self._check_ollama)

    # ── BUILD UI ──────────────────────────────────────

    def _build_ui(self):
        # ── Header ──
        hdr = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="J A R V I S",
            font=("Georgia", 24), text_color=GOLD,
        ).pack(side="left", padx=20)

        right = ctk.CTkFrame(hdr, fg_color=BG2, corner_radius=0)
        right.pack(side="right", padx=14, pady=6)

        self._clock_lbl = ctk.CTkLabel(right, text="", font=("DM Sans", 13), text_color=FG)
        self._clock_lbl.pack(anchor="e")

        self.status_lbl = ctk.CTkLabel(
            right, text="● Inicializace", font=("DM Sans", 10), text_color=MUTED,
        )
        self.status_lbl.pack(anchor="e")

        # ── Toolbar ──
        tb = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=36)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        _tts_on = HAS_TTS and _tts_enabled
        tts_label = "🔊 Hlas: ZAP" if _tts_on else ("🔇 Hlas: VYP" if HAS_TTS else "🔇 Hlas: N/A")
        self._tts_btn = ctk.CTkButton(
            tb, text=tts_label,
            font=("DM Sans", 11),
            fg_color=(GOLD if _tts_on else "#3a3a3a"), hover_color=GOLDH,
            text_color=(BG if _tts_on else FG),
            corner_radius=4, height=24, width=120,
            command=self._toggle_tts,
        )
        self._tts_btn.pack(side="left", padx=8, pady=5)

        for lbl, cmd in [("🗑 Log", self._clear_log), ("🧠 Paměť", self._clear_memory)]:
            ctk.CTkButton(
                tb, text=lbl,
                font=("DM Sans", 11), fg_color="#2a2a2a", hover_color="#444",
                text_color=MUTED, corner_radius=4, height=24, width=90,
                command=cmd,
            ).pack(side="left", padx=2, pady=5)

        self._vol_lbl = ctk.CTkLabel(tb, text="", font=("DM Sans", 11), text_color=MUTED)
        self._vol_lbl.pack(side="right", padx=12)

        # ── Divider ──
        ctk.CTkFrame(self, fg_color=GOLD, height=1, corner_radius=0).pack(fill="x")

        # ── Chat oblast ──
        self.chat = ctk.CTkTextbox(
            self,
            font=("Segoe UI", 13) if IS_WINDOWS else ("Ubuntu", 13),
            fg_color=BG, text_color=FG,
            border_width=0, wrap="word",
            state="disabled",
            spacing1=4, spacing3=4,
        )
        self.chat.pack(fill="both", expand=True, padx=0, pady=0)

        self.chat._textbox.tag_config("ts",      foreground=MUTED,  font=("Consolas", 10))
        self.chat._textbox.tag_config("user_lbl", foreground="#aaaaaa", font=("DM Sans", 10, "bold"))
        self.chat._textbox.tag_config("user_msg", foreground=FG)
        self.chat._textbox.tag_config("jarvis_lbl", foreground=GOLD, font=("DM Sans", 10, "bold"))
        self.chat._textbox.tag_config("jarvis_msg", foreground="#ffe0a0")
        self.chat._textbox.tag_config("info",    foreground=BLUE)
        self.chat._textbox.tag_config("success", foreground=GREEN)
        self.chat._textbox.tag_config("error",   foreground=RED)
        self.chat._textbox.tag_config("muted",   foreground=MUTED)
        self.chat._textbox.tag_config("accent",  foreground=GOLD)

        # ── Divider ──
        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

        # ── Input bar (text + mic v jednom řádku) ──
        inp = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=68)
        inp.pack(fill="x")
        inp.pack_propagate(False)

        # Mic tlačítko (vlevo)
        self.mic_btn = ctk.CTkButton(
            inp, text="🎤",
            font=("DM Sans", 18),
            fg_color="#2a2a2a", hover_color=GOLD,
            text_color=FG, corner_radius=6,
            width=48, height=44,
            command=self._on_mic_click,
        )
        self.mic_btn.place(x=12, rely=0.5, anchor="w")
        if not HAS_SR:
            self.mic_btn.configure(state="disabled", text_color=MUTED,
                                   fg_color="#1a1a1a", hover_color="#1a1a1a")

        # Text vstup
        self.text_input = ctk.CTkEntry(
            inp,
            placeholder_text="Napiš příkaz pro JARVIS...",
            font=("DM Sans", 14),
            fg_color=BG3, text_color=FG,
            border_color=GOLD, border_width=1,
            corner_radius=6, height=44,
        )
        self.text_input.place(x=70, rely=0.5, anchor="w", relwidth=0.76)
        self.text_input.bind("<Return>", self._on_text_enter)
        self.text_input.focus()

        # Odeslat tlačítko (vpravo)
        ctk.CTkButton(
            inp, text="↵",
            font=("Georgia", 20),
            fg_color=GOLD, hover_color=GOLDH, text_color=BG,
            corner_radius=6, width=50, height=44,
            command=self._on_text_enter,
        ).place(relx=0.985, rely=0.5, anchor="e")

        # Init
        self._chat_system("JARVIS v2.0 spuštěn. Napiš příkaz nebo mluv.")
        self._tick_clock()
        self._refresh_vol()

    # ── CHAT HELPERS ──────────────────────────────────

    def _chat_append(self, *parts):
        """parts = list of (text, tag) tuples"""
        self.chat.configure(state="normal")
        for text, tag in parts:
            self.chat._textbox.insert("end", text, tag)
        self.chat.configure(state="disabled")
        self.chat._textbox.see("end")

    def _chat_user(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._chat_append(
            ("\n", "muted"),
            (f"  {ts}  ", "ts"),
            ("TY\n", "user_lbl"),
            (f"  {text}\n", "user_msg"),
        )

    def _chat_jarvis(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._chat_append(
            ("\n", "muted"),
            (f"  {ts}  ", "ts"),
            ("JARVIS\n", "jarvis_lbl"),
            (f"  {text}\n", "jarvis_msg"),
        )

    def _chat_info(self, text: str, tag: str = "info"):
        self._chat_append((f"  ↳ {text}\n", tag))

    def _chat_system(self, text: str):
        self._chat_append((f"\n  {text}\n", "muted"))

    def _clear_log(self):
        self.chat.configure(state="normal")
        self.chat._textbox.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._chat_system("Log vymazán.")

    def _clear_memory(self):
        _history.clear()
        self._chat_system("Paměť rozhovoru vymazána.")

    # ── STATUS / CLOCK / VOL ──────────────────────────

    def _tick_clock(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _refresh_vol(self):
        v = _get_volume()
        if v >= 0:
            self._vol_lbl.configure(text=f"🔊 {v}%")
        self.after(5000, self._refresh_vol)

    def _set_status(self, text: str, color: str = MUTED):
        self.status_lbl.configure(text=text, text_color=color)

    def _toggle_tts(self):
        global _tts_enabled
        if not HAS_TTS:
            self._chat_system("TTS není dostupné: pip install edge-tts")
            return
        _tts_enabled = not _tts_enabled
        if _tts_enabled:
            self._tts_btn.configure(text="🔊 Hlas: ZAP", fg_color=GOLD, text_color=BG)
        else:
            self._tts_btn.configure(text="🔇 Hlas: VYP", fg_color="#3a3a3a", text_color=FG)

    # ── OLLAMA CHECK ──────────────────────────────────

    def _check_ollama(self):
        def _check():
            try:
                base = OLLAMA_URL.split("/api/")[0]
                r = requests.get(f"{base}/api/tags", timeout=4)
                if r.status_code != 200:
                    raise ConnectionError()
                models = [m["name"] for m in r.json().get("models", [])]
                if any(OLLAMA_MODEL in m for m in models):
                    self.after(0, lambda: self._set_status("● Online", GREEN))
                    self.after(0, lambda: self._chat_system(f"Ollama [{OLLAMA_MODEL}] připojena ✓"))
                else:
                    self.after(0, lambda: self._set_status("● Model chybí", "#ff9800"))
                    self.after(0, lambda: self._chat_info(
                        f"Model '{OLLAMA_MODEL}' chybí — spusť: ollama pull {OLLAMA_MODEL}", "error"))
            except Exception:
                self.after(0, lambda: self._set_status("● Offline", RED))
                self.after(0, lambda: self._chat_info("Ollama není dostupná — spusť: ollama serve", "error"))
        threading.Thread(target=_check, daemon=True).start()

    # ── THINKING ANIMATION ────────────────────────────

    def _start_thinking(self):
        self._dots = 0
        def _tick():
            self._dots = (self._dots + 1) % 4
            self._set_status("● Přemýšlím" + "." * self._dots, GOLD)
            self._thinking_job = self.after(400, _tick)
        _tick()

    def _stop_thinking(self):
        if self._thinking_job:
            self.after_cancel(self._thinking_job)
            self._thinking_job = None

    # ── MICROPHONE ────────────────────────────────────

    def _on_mic_click(self):
        if self._is_listening or not HAS_SR:
            return
        threading.Thread(target=self._listen_and_process, daemon=True).start()

    def _listen_and_process(self):
        self._is_listening = True
        self.after(0, lambda: self.mic_btn.configure(
            text="⏹", fg_color=RED, hover_color=RED,
        ))
        self.after(0, lambda: self._chat_system("Poslouchám..."))

        try:
            text = listen_microphone()
        except Exception as e:
            if "timed out" in str(e).lower() or "WaitTimeoutError" in type(e).__name__:
                text = ""
            else:
                self.after(0, lambda: self._chat_info(f"Chyba mikrofonu: {e}", "error"))
                text = ""
        finally:
            self._is_listening = False
            self.after(0, lambda: self.mic_btn.configure(
                text="🎤", fg_color="#2a2a2a", hover_color=GOLD,
            ))

        if text:
            self._process_command(text)
        else:
            self.after(0, lambda: self._chat_system("Nerozuměl jsem. Zkus znovu."))

    # ── TEXT INPUT ────────────────────────────────────

    def _on_text_enter(self, event=None):
        text = self.text_input.get().strip()
        if not text:
            return
        self.text_input.delete(0, "end")
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    # ── PROCESS COMMAND ───────────────────────────────

    def _process_command(self, text: str):
        self.after(0, lambda: self._chat_user(text))
        self.after(0, self._start_thinking)

        result  = ask_ollama(text)
        action  = result.get("action", "answer")
        params  = result.get("params", {})
        message = result.get("message", "")

        self.after(0, self._stop_thinking)

        if message:
            self.after(0, lambda: self._chat_jarvis(message))
            speak(message)

        if action != "answer":
            self.after(0, lambda: self._chat_info(f"akce: {action} {params}", "muted"))

            def _notify(msg, tag="info"):
                self.after(0, lambda: self._chat_info(msg, tag))

            outcome = execute_action(action, params, notify=_notify)
            if outcome and outcome != "ok":
                self.after(0, lambda: self._chat_info(outcome, "info"))

        self.after(0, lambda: self._set_status("● Online", GREEN))
        self.after(0, self._refresh_vol)


# ══════════════════════════════════════════════════════
#  SPUŠTĚNÍ
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()
