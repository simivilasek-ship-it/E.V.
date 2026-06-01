"""
JARVIS — Lokální router (regex/fuzzy bez LLM)
Zpracovává 95% příkazů lokálně.
"""

import os
import re
from datetime import datetime

_HOME = os.path.expanduser("~")
_USER = os.environ.get("USER", os.path.basename(_HOME))

from commands.utils import normalize_text as _norm

# ══════════════════════════════════════════════════════
#  KONSTANTY
# ══════════════════════════════════════════════════════

# Webové stránky
_SITES = {
    "dashboard": "http://localhost:8002",
    "youtube": "https://www.youtube.com",
    "google":  "https://www.google.com",
    "github":  "https://github.com",
    "facebook":"https://www.facebook.com",
    "instagram":"https://www.instagram.com",
    "reddit":  "https://www.reddit.com",
    "twitch":  "https://www.twitch.tv",
    "netflix": "https://www.netflix.com",
    "gmail":   "https://mail.google.com",
    "twitter": "https://www.twitter.com",
    "maps":    "https://maps.google.com",
    "moodle":  "https://moodle.sspu-opava.cz",
    "spotify": "https://open.spotify.com",
    "discord": "https://discord.com/app",
    "chatgpt": "https://chat.openai.com",
    "wikipedia":"https://cs.wikipedia.org",
}

# Aplikace
_APPS = {
    "chrome": "chrome", "chromium": "chromium", "firefox": "firefox",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vscode": "code", "code": "code", "telegram": "telegram", "vlc": "vlc",
    "kalkulačka": "calc", "calc": "calc", "notepad": "notepad",
    "průzkumník": "nautilus", "soubory": "nautilus", "nautilus": "nautilus",
    "gimp": "gimp", "inkscape": "inkscape", "blender": "blender",
    "terminal": "bash", "bash": "bash",
}

# Přeložení názvů procesů
_PROC_ALIASES = {
    "youtube": "chromium", "chrome": "chrome", "firefox": "firefox",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vs code": "code", "vscode": "code", "vlc": "vlc",
    "gimp": "gimp", "telegram": "telegram", "steam": "steam",
    "kalkulačka": "gnome-calculator",
}

# Trigger slova pro hudbu (bez diakritiky)
_MUSIC_STOP = re.compile(
    r"\b(pust|zahraj|prehraj|play|spust|dej\s+mi|chci\s+slyset"
    r"|spotif[yi]|youtube\s+music|hudbu|muziku|pisni?cku?|song|track|skladbu|zvuk)\b",
    re.IGNORECASE,
)

# Trigger slova pro zavření/ukončení (bez diakritiky)
_CLOSE_TRIGGER = re.compile(
    r"\b(zavri|ukonci|zabij|kill|stop|ukoncit|zabi|vypni\s+(?!pc|pocitac|laptop))\b",
    re.IGNORECASE,
)

# Trigger slova pro otevření (bez diakritiky)
_OPEN_TRIGGER = re.compile(
    r"\b(otevri|spust|open|start|nastartuj|otvirej)\b",
    re.IGNORECASE,
)

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_FUZZY = True
except ImportError:
    _HAS_FUZZY = False

# Fuzzy aliasy: (fráze, normalizovaný trigger, akce, params_fn)
_FUZZY_COMMANDS = [
    ("otevri chrome",    "open_app",        lambda: {"app": "chrome"}),
    ("otevri firefox",   "open_app",        lambda: {"app": "firefox"}),
    ("otevri spotify",   "open_app",        lambda: {"app": "spotify"}),
    ("otevri discord",   "open_app",        lambda: {"app": "discord"}),
    ("kolik je hodin",   "get_time",        lambda: {}),
    ("jake je datum",    "get_date",        lambda: {}),
    ("screenshot",       "screenshot",      lambda: {}),
    ("info o systemu",   "system_info",     lambda: {}),
    ("rekni komponenty", "hardware_info",   lambda: {}),
    ("jaky mas hardware","hardware_info",   lambda: {}),
    ("moje pc komponenty","hardware_info",  lambda: {}),
    ("fotbalove vysledky","sports",         lambda: {"query": "fotbal"}),
    ("sportovni vysledky","sports",         lambda: {"query": ""}),
    ("kdo hraje dnes",   "sports",         lambda: {"query": "fotbal"}),
    ("hraje dnes",       "sports",         lambda: {"query": "sport"}),
    ("dnes fotbal",      "sports",         lambda: {"query": "fotbal dnes"}),
    ("fotbal dnes",      "sports",         lambda: {"query": "fotbal dnes"}),
    ("premier league",   "sports",         lambda: {"query": "premier league"}),
    ("champions league", "sports",         lambda: {"query": "champions league"}),
    ("kolik mam mista",  "disk_space",      lambda: {"path": "/"}),
    ("kolik je mista",   "disk_space",      lambda: {"path": "/"}),
    ("misto na disku",   "disk_space",      lambda: {"path": "/"}),
    ("volne misto",      "disk_space",      lambda: {"path": "/"}),
    ("co mam na plose",  "list_directory",  lambda: {"path": "~/Plocha"}),
    ("co je na plose",   "list_directory",  lambda: {"path": "~/Plocha"}),
    ("co mam v dokumentech", "list_directory", lambda: {"path": "~/Dokumenty"}),
    ("co mam ve stazene","list_directory",  lambda: {"path": "~/Stažené"}),
    ("obsah domovske slozky","list_directory",lambda: {"path": "~"}),
    ("vypni pocitac",    "shutdown",        lambda: {"delay": 0}),
    ("restartuj pocitac","restart",         lambda: {"delay": 0}),
    # Vision — překlepy jako "popíš obrazovku", "co vidis na obrazovce"
    ("co vidis",         "screen_describe", lambda: {}),
    ("popis obrazovku",  "screen_describe", lambda: {}),
    ("precti obrazovku", "screen_ocr",      lambda: {}),
    ("zapni kameru",     "webcam_describe", lambda: {}),
]
_FUZZY_THRESHOLD = 82  # 0–100, 82 = toleruje 1–2 překlepy


# ══════════════════════════════════════════════════════
#  POMOCNÉ FUNKCE
# ══════════════════════════════════════════════════════

def _extract_app_name(text: str) -> str:
    """Odstraní trigger slova a vrátí název aplikace/procesu."""
    t = re.sub(
        r"\b(zavri|ukonci|zabij|zabi|kill|stop|ukoncit|otevri|spust|open|start"
        r"|okno|aplikaci|program|proces|appku|app|web|stranku)\b",
        "", _norm(text), flags=re.IGNORECASE
    ).strip(" ,.-")
    return t


def _parse_args(command: str, args: str) -> dict:
    a = args.strip()
    try:
        m = {
            "open_app":       lambda: {"app": a},
            "open_url":       lambda: {"url": a if a.startswith("http") else "https://" + a},
            "search_web":     lambda: {"query": a},
            "write_text":     lambda: {"text": a},
            "type_key":       lambda: {"key": a},
            "kill_process":   lambda: {"name": a},
            "weather":        lambda: {"city": a},
            "vscode_open":    lambda: {"path": os.path.expanduser(a)},
            "open_file":      lambda: {"path": os.path.expanduser(a)},
            "create_folder":  lambda: {"path": os.path.expanduser(a)},
            "create_file":    lambda: {"path": os.path.expanduser(a)},
            "delete_file":    lambda: {"path": os.path.expanduser(a)},
            "install_app":    lambda: {"name": a},
            "uninstall_app":  lambda: {"name": a},
            "run_script":     lambda: {"path": os.path.expanduser(a)},
            "memory_recall":  lambda: {"query": a, "top_k": 5},
            "memory_store":   lambda: _parse_memory_store(a),
            "memory_stats":   lambda: {},
            "memory_maintenance": lambda: {},
            "clipboard_set":  lambda: {"text": a},
            "set_brightness": lambda: {"level": int(re.sub(r"[^\d]","",a) or "50")},
            "volume":         lambda: {"level": int(a)} if a.isdigit()
                                      else {"action": a},
            "media":          lambda: {"action": a},
            "shutdown":       lambda: {"delay": int(re.sub(r"[^\d]","",a) or "0")},
            "restart":        lambda: {"delay": int(re.sub(r"[^\d]","",a) or "0")},
            "find_files":     lambda: {"name": a, "path": _HOME},
            "set_timer":      lambda: _parse_timer(a),
            "youtube_play":     lambda: {"query": a, "index": 1, "audio_only": False},
            "youtube_download": lambda: {"query": a, "audio_only": False, "quality": "best"},
            "youtube_info":     lambda: {"query": a},
            "youtube_subtitles":lambda: {"query": a, "lang": "cs"},
            "move_file":      lambda: _parse_move(a),
            "write_email":    lambda: {"to": a, "subject": "", "body": ""},
            "calculate":      lambda: {"expression": a},
            "translate":      lambda: _parse_translate(a),
            "note_add":       lambda: {"note": a},
            "note_list":      lambda: {},
            "reminder_set":   lambda: _parse_reminder(a),
            "wiki_search":    lambda: {"query": a},
            "currency_convert": lambda: _parse_currency(a),
        }
        if command in m:
            return m[command]()
    except Exception:
        pass
    return {}


def _parse_timer(a: str) -> dict:
    parts = a.split(None, 1)
    secs  = int(parts[0]) if parts and parts[0].isdigit() else 60
    label = parts[1] if len(parts) > 1 else "Timer"
    return {"seconds": secs, "label": label}


def _parse_move(a: str) -> dict:
    for sep in (" -> ", " → ", " na ", " do "):
        if sep in a:
            src, dst = a.split(sep, 1)
            return {"src": os.path.expanduser(src.strip()),
                    "dst": os.path.expanduser(dst.strip())}
    return {"src": a, "dst": ""}


def _parse_translate(a: str) -> dict:
    # Předpokládá formát "text to lang" nebo jen "text"
    parts = a.split(" to ", 1)
    text = parts[0].strip()
    to_lang = parts[1].strip() if len(parts) > 1 else "cs"
    return {"text": text, "to_lang": to_lang}


def _parse_currency(a: str) -> dict:
    # Předpokládá "100 USD na CZK" nebo "1 EUR CZK"
    parts = a.upper().split()
    amount = 1.0
    from_curr = "USD"
    to_curr = "CZK"
    try:
        if parts and parts[0].replace(".", "").isdigit():
            amount = float(parts[0])
            parts = parts[1:]
        if parts:
            from_curr = parts[0]
        found = False
        for sep in ("NA", "TO", "IN"):
            if sep in parts:
                idx = parts.index(sep)
                to_curr = parts[idx + 1] if idx + 1 < len(parts) else to_curr
                found = True
                break
        if not found and len(parts) >= 2:
            to_curr = parts[-1]
    except (ValueError, IndexError):
        pass
    return {"amount": amount, "from_curr": from_curr, "to_curr": to_curr}


def _parse_reminder(a: str) -> dict:
    # Předpokládá "text za 5 minut"
    parts = a.split(" za ", 1)
    text = parts[0].strip()
    time_str = parts[1].strip() if len(parts) > 1 else "1 minuta"
    return {"text": text, "time_str": time_str}


def _parse_memory_store(a: str) -> dict:
    # Předpokládá "content s důležitostí 0.8" nebo jen "content"
    parts = a.split(" s důležitostí ", 1)
    content = parts[0].strip()
    importance = float(parts[1].strip()) if len(parts) > 1 else 0.5
    return {"content": content, "importance": importance}


# ══════════════════════════════════════════════════════
#  LOKÁLNÍ ROUTER — 95% příkazů bez LLM
# ══════════════════════════════════════════════════════

import logging
logger = logging.getLogger(__name__)

try:
    from router_dsl import RouterDSL as _RouterDSL
    _HAS_DSL = True
except ImportError:
    _HAS_DSL = False


class LocalRouter:
    """
    Zpracovává příkazy lokálně bez volání LLM.
    Vrátí (message, action_data) nebo (None, None) → jde na LLM.
    """

    def __init__(self):
        if _HAS_DSL:
            self._dsl = _RouterDSL()
            # Příklady pravidel jako DSL místo raw regex
            self._dsl.rule('nastav hlasitost na {num}', 'volume', 'level', coerce=int)
            self._dsl.rule('hlasitost {num}', 'volume', 'level', coerce=int)
            self._dsl.rule('timer {num} minut', 'set_timer', 'seconds',
                           coerce=lambda x: int(float(x)) * 60)
            self._dsl.rule('timer {num} sekund', 'set_timer', 'seconds', coerce=int)
            self._dsl.rule('otevri {app}', 'open_app', 'app')
            self._dsl.rule('spust {app}', 'open_app', 'app')
        else:
            self._dsl = None

    def route(self, text: str) -> tuple:
        # Normalizujeme diakritiku → "otevři" == "otevri", "spusť" == "spust"
        t  = _norm(text)
        dt = datetime.now()

        # ── DSL FALLBACK (nižší priorita — zkusíme po normalizaci, ale před regex) ──
        # Poznámka: DSL pravidla mají NIŽŠÍ prioritu než stávající regex bloky.
        # Proto je voláme zde jako kandidáta a použijeme jej jen pokud stávající
        # regex nic nenajde. Uložíme výsledek a vrátíme ho na konci.
        _dsl_result = (None, None)
        if self._dsl is not None:
            _dsl_action, _dsl_params = self._dsl.match(t)
            if _dsl_action is not None:
                _dsl_result = (None, {"action": _dsl_action, "params": _dsl_params})

        # ── ČAS/DATUM (před fuzzy pasem — "dnes" nesmí matchnout sports) ──────
        if re.search(r"^\s*(dnes|dneska|dnesni\s+datum)\s*$", t):
            return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": "get_date", "params": {}}

        # ── ZAVŘÍT / UKONČIT (před fuzzy pasem — jinak "zavři X" matchuje "otevři X") ──
        if _CLOSE_TRIGGER.search(t):
            app_name = _extract_app_name(text)
            if len(app_name) > 1:
                proc = app_name.lower()
                for alias, real in _PROC_ALIASES.items():
                    if _norm(alias) in proc:
                        proc = real
                        break
                return f"Ukončuji {app_name}.", {
                    "action": "kill_process", "params": {"name": proc}}

        # ── VSCODE (před open_app, jinak matchuje 'otevři code') ────────
        if re.search(r"\b(otevri|open)\s+(ve?\s+)?(vscode|code|editor)\b", t):
            rest = re.sub(r"\b(otevri|open)\s+(ve?\s+)?(vscode|code|editor)\b\s*", "", text,
                          flags=re.IGNORECASE).strip()
            path = os.path.expanduser(rest) if rest else _HOME
            return f"Otevírám ve VSCode: {rest or '~'}.", {
                "action": "vscode_open", "params": {"path": path}}

        # ── SPUSŤ SKRIPT (před open_app, jinak matchuje 'spusť X') ─────
        m = re.search(r"\b(spust|spusti|spusť|run|execute)\s+(\S+\.(sh|py|bash|zsh|rb|pl))\b", t)
        if m:
            name = m.group(2).strip()
            path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
            return f"Spouštím skript {name}.", {
                "action": "run_script", "params": {"path": os.path.expanduser(path)}}
        m = re.search(r"\b(spust|spusti|spusť|run|execute|bash)\s+skript\s+(\S+)", t)
        if m:
            name = m.group(2).strip()
            path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
            return f"Spouštím skript {name}.", {
                "action": "run_script", "params": {"path": os.path.expanduser(path)}}

        # ── PŘEJMENUJ (před move_file a open_app) ───────────────────────
        m = re.search(r"\b(prejmenuj|prejmenu(j)?|rename)\s+(?:soubor\s+)?(\S+)\s+(na|to)\s+(\S+)", t)
        if m:
            src = m.group(3).strip()
            dst = m.group(5).strip()
            src_p = os.path.expanduser(src if "/" in src else os.path.join(_HOME, src))
            dst_p = os.path.expanduser(dst if "/" in dst else os.path.join(_HOME, dst))
            return f"Přejmenovávám {src} → {dst}.", {
                "action": "move_file", "params": {"src": src_p, "dst": dst_p}}

        # ── PŘESNÁ SHODA (substring) — vyšší priorita než fuzzy ────────
        for phrase, action, params_fn in _FUZZY_COMMANDS:
            if phrase in t:
                params = params_fn()
                if action == "get_time":
                    return f"Je {dt.strftime('%H:%M:%S')}.", {"action": action, "params": params}
                if action == "get_date":
                    return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": action, "params": params}
                return None, {"action": action, "params": params}

        # ── FUZZY PRE-PASS (překlepy a alternativní formulace) ───────
        if _HAS_FUZZY and len(t) < 40:
            for phrase, action, params_fn in _FUZZY_COMMANDS:
                score = _fuzz.partial_ratio(t, phrase)
                if score >= _FUZZY_THRESHOLD:
                    logger.debug(f"Fuzzy match: '{t}' → '{phrase}' ({score})")
                    params = params_fn()
                    # Akce vracející zprávu generujeme zde přímo
                    if action == "get_time":
                        return f"Je {dt.strftime('%H:%M:%S')}.", {"action": action, "params": params}
                    if action == "get_date":
                        return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": action, "params": params}
                    return None, {"action": action, "params": params}

        # ── VISION ───────────────────────────────────
        if t in ("co vidis", "popis obrazovky", "co je na obrazovce") or \
           re.search(r"\b(popís|popis|describe)\s+(obrazovku|screen)\b", text, re.I):
            return "Popisuji obrazovku.", {"action": "screen_describe", "params": {}}

        if re.search(r"\b(precti|prečti)\s+(text|obrazovku)|ocr\b", t, re.I):
            return "Čtu text z obrazovky.", {"action": "screen_ocr", "params": {}}

        if re.search(r"\b(kamera|webcam|co\s+vidi\s+kamera|koukni\s+kamerou)\b", t, re.I):
            return "Dívám se kamerou.", {"action": "webcam_describe", "params": {}}

        # ── ČAS ──────────────────────────────────────
        if re.search(r"\b(kolik je|jaky je|cas|hodin|time)\b", t) and \
           not re.search(r"\b(pracovni|volny|cas na)\b", t):
            return f"Je {dt.strftime('%H:%M:%S')}.", {"action": "get_time", "params": {}}

        # ── DATUM ─────────────────────────────────────
        if re.search(r"\b(datum|dnes|jaky den|ktery den|date)\b", t):
            return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": "get_date", "params": {}}

        # ── SCREENSHOT ────────────────────────────────
        if re.search(r"\b(screenshot|sniiek\s+obrazovky|printscreen|screenshoot|snimek)\b", t):
            return "Pořizuji screenshot.", {"action": "screenshot", "params": {}}

        # ── UNDO ──────────────────────────────────────
        if re.search(r"\b(vrat|undo|zpet\s+akci|zrus\s+posledni|obnov\s+posledni)\b", t):
            return "Vracím poslední akci.", {"action": "undo", "params": {}}
        if re.search(r"\b(undo\s+history|historie\s+akci|co\s+mohu\s+vratit)\b", t):
            return "Historie vrátitelných akcí:", {"action": "undo_history", "params": {}}

        # ── HARDWARE INFO ─────────────────────────────
        if re.search(
            r"\b(hardware|komponenty|komponenta|procesoru?|grafick|grafika|gpu|cpu\s+model"
            r"|zakladni\s+deska|ram\s+typ|jaka\s+mas|jaky\s+mas|moje\s+pc|muj\s+pocitac"
            r"|rekni.*komponenty|zjisti.*hardware|co\s+mas\s+za\s+pc|spec(ifikace)?)\b", t):
            return "Zjišťuji hardwarové komponenty...", {"action": "hardware_info", "params": {}}

        # ── DISK SPACE ───────────────────────────────────
        m = re.search(
            r"\b(kolik\s+(mam|je)\s+(misto|volno|volne|gb|space)|misto\s+na\s+disku"
            r"|volne\s+misto|disk\s+space|free\s+space|jak\s+plny|obsazeni\s+disku"
            r"|kapacita\s+disku)\b", t)
        if m:
            # Pokud obsahuje cestu, předej ji
            path_m = re.search(r"(/\S+|~/\S*)", text)
            path = path_m.group(1) if path_m else "/"
            return "Zjišťuji místo na disku...", {"action": "disk_space", "params": {"path": path}}

        # ── LIST DIRECTORY ────────────────────────────
        m = re.search(
            r"\b(co\s+(mam|je)\s+v\s+|obsah\s+(slozky|adresare|zlozky)|vypis\s+slozky"
            r"|seznam\s+souboru|ls\s+|dir\s+|browse\s+|procházej?\s+|what.s\s+in)\b", t)
        if m:
            path_m = re.search(r"(/\S+|~/\S*|(?:plocha|dokumenty|stazene|desktop|downloads)\b)", text, re.I)
            if path_m:
                raw = path_m.group(1)
                # Mapování českých názvů
                folder_map = {
                    "plocha": "~/Plocha", "desktop": "~/Desktop",
                    "dokumenty": "~/Dokumenty", "documents": "~/Documents",
                    "stazene": "~/Stažené", "downloads": "~/Downloads",
                }
                path = folder_map.get(raw.lower(), raw)
            else:
                path = "~"
            return f"Prohlížím složku {path}...", {"action": "list_directory", "params": {"path": path}}

        # Přímé příkazy pro složky
        for keyword, path in [
            ("obsah plochy", "~/Plocha"), ("co mam na plose", "~/Plocha"),
            ("co mam na ploche", "~/Plocha"), ("obsah dokumentu", "~/Dokumenty"),
            ("obsah stazene", "~/Stažené"), ("domovsky adresar", "~"),
            ("home folder", "~"), ("what.*desktop", "~/Desktop"),
        ]:
            if keyword in t or re.search(keyword, t):
                return f"Prohlížím složku {path}...", {"action": "list_directory", "params": {"path": path}}

        # ── FILE INFO ────────────────────────────────
        m = re.search(
            r"\b(info\s+o\s+souboru|detail.*soubor|jak\s+velky|velikost\s+souboru"
            r"|file\s+info|stat\s+souboru)\b", t)
        if m:
            path_m = re.search(r"(/\S+|~/\S+)", text)
            path = path_m.group(1) if path_m else ""
            return "Zjišťuji info o souboru...", {"action": "file_info", "params": {"path": path}}

        # ── SYSTEM INFO ───────────────────────────────
        if re.search(r"\b(využití\s+(cpu|ram|disk)|system\s+info|stav\s+systému|kolik\s+ram)\b", t):
            return None, {"action": "system_info", "params": {}}

        # ── VYPNOUT ───────────────────────────────────
        if re.search(r"\b(vypni\s+(pc|pocitac|laptop|komputer)|shutdown)\b", t):
            return "Vypínám počítač.", {"action": "shutdown", "params": {"delay": 0}}

        # ── RESTART ───────────────────────────────────
        if re.search(r"\b(restartuj|restart\s+(pc|pocitac))\b", t):
            return "Restartuji počítač.", {"action": "restart", "params": {"delay": 0}}

        # ── USPAT ─────────────────────────────────────
        if re.search(r"\b(uspi\s+(pc|pocitac)|sleep\s+pc|spanek\s+pc)\b", t):
            return "Uspávám počítač.", {"action": "sleep_pc", "params": {}}

        # ── AKTUALIZACE ───────────────────────────────
        if re.search(r"\b(aktualizuj\s+system|apt\s+upgrade|update\s+system)\b", t):
            return "Spouštím aktualizaci.", {"action": "update_system", "params": {}}

        # ── HLASITOST ─────────────────────────────────
        vol = re.search(r"\b(hlasitost|volume|zvuk)\s*(na|:)?\s*(\d+)", t)
        if vol:
            lvl = min(100, max(0, int(vol.group(3))))
            return f"Hlasitost: {lvl}%.", {"action": "volume", "params": {"level": lvl}}
        if re.search(r"\b(ztlum|mute|umlc)\b", t):
            return "Ztlumeno.", {"action": "volume", "params": {"action": "mute"}}
        if re.search(r"\b(odtlum|unmute|zesil\s+zvuk)\b", t):
            return "Odtlumeno.", {"action": "volume", "params": {"action": "unmute"}}
        vol2 = re.search(r"\b(zvys|sniz|zesil|ztlum)\s+zvuk\s+na\s*(\d+)", t)
        if vol2:
            lvl = min(100, max(0, int(vol2.group(2))))
            return f"Hlasitost: {lvl}%.", {"action": "volume", "params": {"level": lvl}}

        # ── JAS ───────────────────────────────────────
        jas = re.search(r"\b(jas|brightness)\s*(na|:)?\s*(\d+)", t)
        if jas:
            lvl = min(100, max(1, int(jas.group(3))))
            return f"Jas: {lvl}%.", {"action": "set_brightness", "params": {"level": lvl}}

        # ── MEDIA ─────────────────────────────────────
        if re.search(r"\b(pozastav|pauza|pause)\b", t):
            return "Pozastavuji.", {"action": "media", "params": {"action": "play_pause"}}
        if re.search(r"\b(preskocit|dalsi\s+skladb|next\s+track)\b", t):
            return "Další skladba.", {"action": "media", "params": {"action": "next"}}
        if re.search(r"\b(predchozi\s+skladb|zpet\s+skladb)\b", t):
            return "Předchozí.", {"action": "media", "params": {"action": "prev"}}

        # ── YT-DLP: STÁHNOUT ──────────────────────────
        if re.search(r"\b(stahni|download|stahnout|uloz\s+video|uloz\s+audio)\b", t):
            audio = bool(re.search(r"\b(audio|mp3|hudbu|zvuk)\b", t))
            quality = "720p" if "720" in t else "1080p" if "1080" in t else "480p" if "480" in t else "best"
            query = re.sub(r"\b(stahni|download|stahnout|uloz|video|audio|mp3|hudbu|zvuk|z\s+youtube)\b",
                           "", text, flags=re.IGNORECASE).strip(" ,.-")
            if query:
                mode = "audio MP3" if audio else f"video {quality}"
                return f"Stahuji {mode}: {query}", {
                    "action": "youtube_download",
                    "params": {"query": query, "audio_only": audio, "quality": quality}}

        # ── YT-DLP: INFO O VIDEU ──────────────────────
        if re.search(r"\b(info\s+o\s+videu|informace\s+o\s+videu|jak\s+dlouhe|delka\s+videa)\b", t):
            query = re.sub(r"\b(info|informace|o\s+videu|jak\s+dlouhe|delka)\b",
                           "", text, flags=re.IGNORECASE).strip(" ,.-")
            if query:
                return f"Zjišťuji info: {query}", {
                    "action": "youtube_info", "params": {"query": query}}

        # ── URL v textu → vždy otevři prohlížeč (před hudbou!) ──────
        url_early = re.search(r"(https?://\S+|\b\w[\w.-]+\.\w{2,}\S*)", text)
        if url_early and re.search(r"\b(spust|otevri|naviguj|jdi\s+na|web|stranku|prohlizec|browser|chromium|firefox|chrome)\b", t):
            url = url_early.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return f"Otevírám {url}.", {
                "action": "open_url", "params": {"url": url}}

        # ── HUDBA ─────────────────────────────────────
        if re.search(r"\b(pust|zahraj|prehraj|spust|play)\b", t):
            audio_only = bool(re.search(r"\b(jen\s+zvuk|audio|mp3|poslouchat)\b", t))
            # Pokud query odpovídá známé aplikaci → otevři ji, nehraj hudbu
            for app_name, app_cmd in _APPS.items():
                if _norm(app_name) in t.split():
                    return f"Spouštím {app_name}.", {
                        "action": "open_app", "params": {"app": app_cmd}}
            for site, url in _SITES.items():
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

        # ── SPORT ─────────────────────────────────────
        if re.search(
            r"\b(sport|fotbal|hokej|nhl|nba|nfl|mlb|basket"
            r"|premier\s*league|champions\s*league|liga\s*mistr"
            r"|la\s*liga|serie\s*a|bundesliga|ligue\s*1|fortuna\s*liga"
            r"|zapas|zapasy|vysledky|skore|live\s*score"
            r"|hraje\s+dnes|kdo\s+hraje|co\s+se\s+hraje|novinky\s+sport)\b", t) \
                and not re.search(r"^\s*dnes\s*$", t):
            # Vezmi celý dotaz jako query — ESPN API si s tím poradí
            query = re.sub(
                r"\b(rekni|rici|zjisti|ukazmi|jak\s+to\s+dopadlo|co\s+je|jake\s+jsou)\b",
                "", text, flags=re.IGNORECASE).strip()
            return "Načítám sportovní výsledky...", {"action": "sports", "params": {"query": query}}

        # ── POČASÍ ────────────────────────────────────
        if re.search(r"\b(pocasi|weather|bude\s+prset|teplota\s+v)\b", t):
            # "pocasi Praha" nebo "Praha pocasi" nebo "pocasi v Praze"
            m = re.search(r"\b(pocasi|weather)\b\s+(?:v\s+)?(\w+)", t)
            if not m:
                # Město PŘED slovem počasí: "Ostrava pocasi"
                m = re.search(r"\b(\w+)\s+(?:pocasi|weather)\b", t)
            city = m.group(2 if m and m.lastindex >= 2 else 1).capitalize() if m else ""
            # Ignoruj stopslova jako trigger slova
            if city.lower() in ("pocasi", "weather", "dnes", "zitra", "bude"):
                city = ""
            return f"Počasí{' — ' + city if city else ''}:", {
                "action": "weather", "params": {"city": city}}

        # ── TIMER ─────────────────────────────────────
        if re.search(r"\b(timer|casovac|pripominka|upozorni\s+za|za\s+\d+\s+minut)\b", t):
            m = re.search(r"(\d+)\s*(minut|sekund|hodin)", t)
            if m:
                n, unit = int(m.group(1)), m.group(2)
                secs = n * (3600 if unit.startswith("hodin") else
                            60   if unit.startswith("minut") else 1)
                return f"Timer {n} {unit}.", {
                    "action": "set_timer", "params": {"seconds": secs, "label": "Timer"}}

        # ── OTEVŘÍT WEB / APLIKACI ────────────────────
        if _OPEN_TRIGGER.search(t):
            for site, url in _SITES.items():
                if site in t:
                    return f"Otevírám {site.capitalize()}.", {
                        "action": "open_url", "params": {"url": url}}
            for name, cmd in _APPS.items():
                if _norm(name) in t:
                    return f"Spouštím {name}.", {
                        "action": "open_app", "params": {"app": cmd}}
            url_m = re.search(r"(https?://\S+|\w+\.\w{2,}\S*)", text)
            if url_m:
                url = url_m.group(1)
                return f"Otevírám {url}.", {
                    "action": "open_url",
                    "params": {"url": url if url.startswith("http") else "https://"+url}}

        # ── SPORT & AKTUÁLNÍ ZPRÁVY → automatický web search ────
        # Zápasy, výsledky, novinky — JARVIS nemá realtime data, vyhledá za uživatele
        sport_m = re.search(
            r"\b(vs\.?|versus|proti|zapas|zápas|vysledek|výsledek|skore|skóre"
            r"|goal|gol|liga|champions|premier|bundesliga|serie\s*a|laliga"
            r"|nba|nhl|nfl|mlb|f1|formula|mma|ufc|wta|atp|tenis|golf"
            r"|ko\s+\d|\d+:\d+|final[ae]?|semifinal[ae]?"
            r"|paris|arsenal|chelsea|manchester|real\s+madrid|barcelona"
            r"|liverpool|inter|juventus|milan|dortmund)\b", t, re.IGNORECASE)
        if sport_m:
            # Vyhledej přímo v chatu přes DuckDuckGo (ne otevírat prohlížeč)
            try:
                from plugins.custom.mcp_fetch.skill import _ddg_search
                result = _ddg_search(text, max_chars=1200)
                if result and len(result) > 50:
                    return result, {"action": "answer", "params": {}}
            except Exception:
                pass
            # Fallback: otevři prohlížeč
            return f"Hledám na googlu: {text}.", {
                "action": "search_web", "params": {"query": text}}

        # Novinky, kurzy, krypto
        news_m = re.search(
            r"\b(novinky|aktualni|trending|co\s+se\s+deje"
            r"|kurz\s+(eura|dolaru|btc|koruny)|cena\s+(akcie|bitcoinu|bitcoin|zlata|ropy|btc)"
            r"|kdo\s+vyhral|kdo\s+postoupil|vysledky\s+dnes|zapasy\s+dnes|dnesni\s+zapasy"
            r"|tabulka\s+(ligy|standings)|kam\s+postoupil|kdo\s+sestoupil"
            r"|bitcoin|ethereum|krypto)\b", t, re.IGNORECASE)
        if news_m:
            try:
                from plugins.custom.mcp_fetch.skill import _ddg_search
                result = _ddg_search(text, max_chars=1200)
                if result and len(result) > 50:
                    return result, {"action": "answer", "params": {}}
            except Exception:
                pass
            return f"Hledám: {text}.", {
                "action": "search_web", "params": {"query": text}}

        # ── HLEDÁNÍ ───────────────────────────────────
        if re.search(r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b", t):
            query = re.sub(r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b\s*",
                           "", text, flags=re.IGNORECASE).strip()
            if query:
                return f"Hledám: {query}.", {
                    "action": "search_web", "params": {"query": query}}

        # ── VSCODE ────────────────────────────────────
        # VSCode trigger je výše (řádky ~325)

        # ── VYTVOŘ SLOŽKU ─────────────────────────────
        m = re.search(r"\b(vytvor|vytvorit|mkdir)\s+slozku\s+(.+)", t)
        if m:
            name = m.group(2).strip()
            path = os.path.join(_HOME, name)
            return f"Vytvářím složku {name}.", {
                "action": "create_folder", "params": {"path": path}}

        # ── VYTVOŘ SOUBOR ─────────────────────────────
        m = re.search(r"\b(vytvor|vytvorit|touch|new)\s+soubor\s+(\S+)", t)
        if m:
            name = m.group(2).strip()
            path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
            return f"Vytvářím soubor {name}.", {
                "action": "create_file", "params": {"path": os.path.expanduser(path)}}

        # ── SMAŽ / ODSTRAŇ SOUBOR ─────────────────────
        m = re.search(r"\b(smaz|smazat|odstra(n|ň)|delete|rm)\s+soubor\s+(\S+)", t)
        if not m:
            m = re.search(r"\b(smaz|smazat|odstra(n|ň)|delete)\s+(\S+\.\w+)\b", t)
        if m:
            # Vezmi poslední skupinu — samotný název souboru
            name = m.group(m.lastindex).strip()
            path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
            return f"Mažu soubor {name}.", {
                "action": "delete_file", "params": {"path": os.path.expanduser(path)}}

        # ── PŘESUŇ / PŘEJMENUJ SOUBOR ──────────────────
        m = re.search(r"\b(presun|přesuň|presuv|přejmenuj|mv|rename)\s+(.+?)\s+(do|na|->|→|to)\s+(.+)", t)
        if m:
            src = m.group(2).strip()
            dst = m.group(4).strip()
            src_p = src if src.startswith("/") or src.startswith("~") else os.path.join(_HOME, src)
            dst_p = dst if dst.startswith("/") or dst.startswith("~") else os.path.join(_HOME, dst)
            return f"Přesouvám {src} → {dst}.", {
                "action": "move_file", "params": {
                    "src": os.path.expanduser(src_p),
                    "dst": os.path.expanduser(dst_p)}}

        # ── SPUSŤ SKRIPT ────────────────────────────────
        m = re.search(r"\b(spust|spusti|spusť|run|execute|bash|sh)\s+skript\s+(\S+)", t)
        if not m:
            m = re.search(r"\b(spust|spusti|spusť|run)\s+(\S+\.(sh|py|bash))\b", t)
        if m:
            name = m.group(m.lastindex).strip()
            path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
            return f"Spouštím skript {name}.", {
                "action": "run_script", "params": {"path": os.path.expanduser(path)}}

        # ── OTEVŘI VE VSCODE ────────────────────────────
        m = re.search(r"\b(otevri|open)\s+(ve?\s+)?(vscode|code|editor)\s*(.+)?", t)
        if m:
            path_raw = (m.group(4) or "").strip()
            path = os.path.expanduser(path_raw) if path_raw else _HOME
            return f"Otevírám ve VSCode: {path_raw or '~'}.", {
                "action": "vscode_open", "params": {"path": path}}

        # ── NAJDI SOUBOR ──────────────────────────────
        m = re.search(r"\b(najdi|hledej)\s+soubor\s+(.+)", t)
        if m:
            name = m.group(2).strip()
            return f"Hledám soubor: {name}.", {
                "action": "find_files", "params": {"name": name, "path": _HOME}}

        # ── SCHRÁNKA ──────────────────────────────────
        m = re.search(r"\b(zkopíruj|kopíruj|dej\s+do\s+schránky)\s+(.+)", text,
                      re.IGNORECASE)
        if m:
            txt = m.group(2).strip()
            return f"Zkopírováno: {txt}", {
                "action": "clipboard_set", "params": {"text": txt}}

        # ── NAPSÁNÍ TEXTU ─────────────────────────────
        m = re.search(r"\b(napiš|napsat|typ(uj)?)\s+(.+)", text, re.IGNORECASE)
        if m:
            txt = m.group(3).strip()
            return f"Píšu: {txt}", {
                "action": "write_text", "params": {"text": txt}}

        # ── KALKULAČKA ───────────────────────────────
        if re.search(r"\b(vypočítej|spočítej|kolik\s+je|calculate)\b", t):
            expr = re.sub(r"\b(vypočítej|spočítej|kolik\s+je|calculate)\b\s*",
                          "", text, flags=re.IGNORECASE).strip()
            if expr:
                return f"Vypočítávám: {expr}", {
                    "action": "calculate", "params": {"expression": expr}}

        # ── PŘEKLAD ──────────────────────────────────
        if re.search(r"\b(přelož|překlad|translate)\b", t):
            txt = re.sub(r"\b(přelož|překlad|translate)\b\s*", "", text,
                         flags=re.IGNORECASE).strip()
            if txt:
                return f"Překládám: {txt}", {
                    "action": "translate", "params": {"text": txt}}

        # ── POZNÁMKY ─────────────────────────────────
        if re.search(r"\b(přidej\s+poznámku|ulož\s+poznámku|note\s+add)\b", t):
            note = re.sub(r"\b(přidej\s+poznámku|ulož\s+poznámku|note\s+add)\b\s*",
                          "", text, flags=re.IGNORECASE).strip()
            if note:
                return "Přidávám poznámku.", {
                    "action": "note_add", "params": {"note": note}}
        if re.search(r"\b(zobraz\s+poznámky|ukáž\s+poznámky|note\s+list)\b", t):
            return "Poznámky:", {
                "action": "note_list", "params": {}}

        # ── PŘIPOMÍNKA ────────────────────────────────
        if re.search(r"\b(připomeň|reminder|upozorni)\b", t):
            reminder = re.sub(r"\b(připomeň|reminder|upozorni)\b\s*", "", text,
                              flags=re.IGNORECASE).strip()
            if reminder:
                return "Nastavuji připomínku.", {
                    "action": "reminder_set", "params": {"text": reminder, "time_str": "1 minuta"}}

        # ── YOUTUBE TITULKY (MCP) ────────────────────
        if re.search(r"\b(titulky|subtitles?|transcript|prepis\s+videa|titulky\s+z)\b", t):
            query = re.sub(r"\b(titulky|subtitles?|transcript|prepis\s+videa|titulky\s+z)\b\s*",
                           "", text, flags=re.IGNORECASE).strip()
            if query:
                return f"Načítám titulky: {query}", {
                    "action": "mcp_tool",
                    "params": {"server": "youtube-transcript", "tool": "get_transcript", "arguments": {"url": query}}}

        # ── GITHUB (MCP) ──────────────────────────────
        if re.search(r"\b(github|issue|pull\s*request|pr\b|commit|repo\b)\b", t) and \
           re.search(r"\b(vytvor|otevri|zobraz|najdi|seznam|search|create|list|get)\b", t):
            query = re.sub(r"\b(github|issue|pull\s*request|pr|commit|repo)\b\s*", "", text,
                           flags=re.IGNORECASE).strip()
            return f"GitHub: {text}", {
                "action": "mcp_tool",
                "params": {"server": "github", "tool": "search_issues",
                           "arguments": {"query": query or text}}}

        # ── GOOGLE MAPS (MCP) ─────────────────────────
        if re.search(r"\b(naviguj|trasa|vzdalenost|jak\s+se\s+dostat|kde\s+je|mapa|maps)\b", t):
            query = re.sub(r"\b(naviguj|trasa|vzdalenost|jak\s+se\s+dostat|kde\s+je|mapa|maps)\b\s*",
                           "", text, flags=re.IGNORECASE).strip()
            if query:
                return f"Google Maps: {query}", {
                    "action": "mcp_tool",
                    "params": {"server": "google-maps", "tool": "geocode",
                               "arguments": {"address": query}}}

        # ── WIKIPEDIE ────────────────────────────────
        if re.search(r"\b(wiki|wikipedia|co\s+je)\b", t):
            query = re.sub(r"\b(wiki|wikipedia|co\s+je)\b\s*", "", text,
                           flags=re.IGNORECASE).strip()
            if query:
                return f"Hledám na Wikipedii: {query}", {
                    "action": "wiki_search", "params": {"query": query}}

        # ── MĚNA ─────────────────────────────────────
        # Trigger hledá v normalizovaném textu (bez diakritiky)
        if re.search(r"\b(prevod|prevest|zmen|konvertuj|convert)\b.{0,20}\b(meny|mena|currency|usd|eur|czk|gbp)\b", t) \
                or re.search(r"\b\d+\s*(usd|eur|czk|gbp|jpy|pln|chf)\b.{0,20}\b(na|to|in)\b", t):
            curr = re.sub(r"\b(prevod|prevest|zmen|konvertuj|convert)\s*(meny|mena|currency)?\s*",
                          "", t, flags=re.IGNORECASE).strip()
            if curr:
                return f"Převádím měnu: {curr}", {
                    "action": "currency_convert", "params": _parse_currency(curr)}

        # ── PARALELNÍ AGENTI ─────────────────────────
        if re.search(
            r"\b(paraleln[eě]|soubehn[eě]|vsechny\s+agenty|spust\s+agenty"
            r"|multi.?agent|vice\s+agentu?|parallel\s+agent)\b", t):
            task = re.sub(
                r"\b(paraleln[eě]|soubehn[eě]|vsechny\s+agenty|spust\s+agenty"
                r"|multi.?agent|vice\s+agentu?|parallel\s+agent)\b\s*",
                "", text, flags=re.IGNORECASE).strip()
            if task:
                return f"Spouštím paralelní agenty: {task}", {
                    "action": "agent_parallel_task", "params": {"task": task}}

        # ── NEURAL MEMORY ────────────────────────────
        if re.search(r"\b(vyhledej\s+v\s+paměti|recall\s+memory|co\s+si\s+pamatuješ)\b", t):
            query = re.sub(r"\b(vyhledej\s+v\s+paměti|recall\s+memory|co\s+si\s+pamatuješ)\b\s*",
                           "", text, flags=re.IGNORECASE).strip()
            return f"Hledám v paměti: {query}", {
                "action": "memory_recall", "params": {"query": query}}
        if re.search(r"\b(zapamatuj\s+si|ulož\s+do\s+paměti|store\s+memory)\b", t):
            content = re.sub(r"\b(zapamatuj\s+si|ulož\s+do\s+paměti|store\s+memory)\b\s*",
                             "", text, flags=re.IGNORECASE).strip()
            if content:
                return f"Ukládám do paměti: {content}", {
                    "action": "memory_store", "params": {"content": content}}
        if re.search(r"\b(statistiky\s+paměti|memory\s+stats)\b", t):
            return "Statistiky paměti:", {
                "action": "memory_stats", "params": {}}
        if re.search(r"\b(údržba\s+paměti|memory\s+maintenance)\b", t):
            return "Spouštím údržbu paměti.", {
                "action": "memory_maintenance", "params": {}}

        # ── FALLBACK: jakákoliv URL v textu → otevři ─────────
        url_fb = re.search(r"(https?://\S+|\b\w[\w.-]+\.(cz|com|org|net|io|sk|de|eu)\S*)", text)
        if url_fb:
            url = url_fb.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return f"Otevírám {url}.", {
                "action": "open_url", "params": {"url": url}}

        # ── DSL pravidla (fallback — nižší priorita než stávající regex) ───────
        if _dsl_result != (None, None):
            logger.debug(f"DSL match: '{t}' → {_dsl_result[1]}")
            return _dsl_result

        # Nerozpoznáno → LLM
        return None, None


# Singleton
_router = LocalRouter()
