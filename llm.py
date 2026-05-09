"""
JARVIS v3.0 — LLM + Lokální router
Lokální router zpracuje 95% příkazů bez LLM.
LLM (qwen2.5:3b) slouží pro AI konverzaci, kód, vysvětlení.
"""

import os
import re
import json
import unicodedata
import requests
import logging
from datetime import datetime
from typing import Dict, Tuple
from collections import deque

from memory import JarvisMemory

logger = logging.getLogger(__name__)

_HOME = os.path.expanduser("~")
_USER = os.environ.get("USER", os.path.basename(_HOME))


# ══════════════════════════════════════════════════════
#  SYSTÉMOVÝ PROMPT — pouze pro AI konverzaci
# ══════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""Jsi JARVIS, inteligentní osobní AI asistent. Komunikuješ česky.

O sobě: Jsi lokální AI asistent běžící na počítači uživatele {_USER}.
Ovládáš počítač, odpovídáš na otázky, píšeš kód, vysvětluješ věci.

Styl odpovědí:
- Buď stručný a přesný
- Pro kód použij markdown (```python ... ```)
- Pro faktické otázky odpověz přímo
- Pro systémové příkazy (otevřít, zavřít, nastavit) odpoví lokální systém automaticky

Umíš:
- Psát kód v Pythonu, JavaScriptu, C++, Bashi a dalších jazycích
- Vysvětlovat technické i obecné pojmy
- Pomáhat s matematikou a logikou
- Překládat texty (angličtina → čeština)
- Provádět matematické výpočty
- Ukládat a zobrazovat poznámky
- Nastavovat připomínky
- Hledat informace na Wikipedii
- Převádět měny
- Ovládat systém (aplikace, soubory, hlasitost, jas)
- Hledat na webu, přehrávat hudbu
- Získávat počasí, čas, systémové informace
- Používat neural memory pro dlouhodobé učení a kontext

Mám brain-inspired paměť, která:
- Dynamicky ukládá a vybavuje informace
- Hodnotí důležitost a časovost
- Automaticky zapomíná nepodstatné věci
- Poskytuje kontext pro lepší odpovědi

Neodpovídej žádným COMMAND formátem — to zpracovává lokální systém automaticky."""


# ══════════════════════════════════════════════════════
#  MAPOVÁNÍ ARGS → PARAMS
# ══════════════════════════════════════════════════════

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
            "youtube_play":   lambda: {"query": a, "index": 1, "audio_only": False},
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

# Webové stránky
_SITES = {
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

def _norm(text: str) -> str:
    """Odstraní diakritiku pro robustní matching (otevři == otevri)."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    )

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


def _extract_app_name(text: str) -> str:
    """Odstraní trigger slova a vrátí název aplikace/procesu."""
    t = re.sub(
        r"\b(zavri|ukonci|zabij|kill|stop|otevri|spust|open|start"
        r"|okno|aplikaci|program|proces|appku|app|web|stranku)\b",
        "", _norm(text), flags=re.IGNORECASE
    ).strip(" ,.-")
    return t


class LocalRouter:
    """
    Zpracovává příkazy lokálně bez volání LLM.
    Vrátí (message, action_data) nebo (None, None) → jde na LLM.
    """

    def route(self, text: str) -> tuple:
        # Normalizujeme diakritiku → "otevři" == "otevri", "spusť" == "spust"
        t  = _norm(text)
        dt = datetime.now()

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

        # ── ZAVŘÍT APLIKACI ───────────────────────────
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

        # ── HUDBA ─────────────────────────────────────
        if re.search(r"\b(pust|zahraj|prehraj|spust|play)\b", t):
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
                    "params": {"query": query, "index": 1, "audio_only": False}}

        # ── POČASÍ ────────────────────────────────────
        if re.search(r"\b(pocasi|weather|bude\s+prset|teplota\s+v)\b", t):
            m = re.search(r"\b(pocasi|weather)\b\s+(?:v\s+)?(\w+)", t)
            city = m.group(2).capitalize() if m else ""
            return f"Počasí{' v ' + city if city else ''}.", {
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

        # ── HLEDÁNÍ ───────────────────────────────────
        if re.search(r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b", t):
            query = re.sub(r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b\s*",
                           "", text, flags=re.IGNORECASE).strip()
            if query:
                return f"Hledám: {query}.", {
                    "action": "search_web", "params": {"query": query}}

        # ── VSCODE ────────────────────────────────────
        if re.search(r"\b(otevři\s+ve?\s+vscode|vscode\s+open|code\s+\.)\b", t):
            path = re.sub(r"\b(otevři\s+ve?\s+vscode|vscode\s+open|code)\b", "", text,
                          flags=re.IGNORECASE).strip()
            return "Otevírám ve VSCode.", {
                "action": "vscode_open",
                "params": {"path": os.path.expanduser(path) if path else _HOME}}

        # ── VYTVOŘ SLOŽKU ─────────────────────────────
        m = re.search(r"\b(vytvoř|vytvořit|mkdir)\s+složku\s+(.+)", t)
        if m:
            name = m.group(2).strip()
            path = os.path.join(_HOME, name)
            return f"Vytvářím složku {name}.", {
                "action": "create_folder", "params": {"path": path}}

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

        # ── WIKIPEDIE ────────────────────────────────
        if re.search(r"\b(wiki|wikipedia|co\s+je)\b", t):
            query = re.sub(r"\b(wiki|wikipedia|co\s+je)\b\s*", "", text,
                           flags=re.IGNORECASE).strip()
            if query:
                return f"Hledám na Wikipedii: {query}", {
                    "action": "wiki_search", "params": {"query": query}}

        # ── MĚNA ─────────────────────────────────────
        if re.search(r"\b(převeď\s+měnu|convert\s+currency)\b", t):
            curr = re.sub(r"\b(převeď\s+měnu|convert\s+currency)\b\s*", "", text,
                          flags=re.IGNORECASE).strip()
            if curr:
                return f"Převádím měnu: {curr}", {
                    "action": "currency_convert", "params": _parse_currency(curr)}

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

        # Nerozpoznáno → LLM
        return None, None


# ══════════════════════════════════════════════════════
#  LLM ENGINE
# ══════════════════════════════════════════════════════

_router = LocalRouter()


class LLMEngine:

    def __init__(self, config: dict, memory: JarvisMemory = None):
        self.config  = config
        self.url     = config["ollama_url"]
        self.model   = config["ollama_model"]
        self.history: deque = deque(maxlen=config.get("history_size", 20))  # fallback
        self.memory  = memory or JarvisMemory(config)  # neural memory
        self._stream_resp = None
        logger.info(f"LLM: {self.model} @ {self.url} + Neural Memory")

    # ── QUICK MATCH (lokální router) ─────────────────

    def _quick_match(self, text: str) -> tuple:
        return _router.route(text)

    # ── ASK (non-streaming) ──────────────────────────

    def ask(self, user_text: str) -> Tuple[str, Dict]:
        msg, action = self._quick_match(user_text)
        if action is not None:
            self.history.append({"role": "user",      "content": user_text})
            self.history.append({"role": "assistant",  "content": msg or ""})
            # Ulož konverzaci do neural memory
            if msg:
                self.memory.store_conversation(user_text, msg or "", importance=0.3)
            return msg or "", action

        self.history.append({"role": "user", "content": user_text})

        # Získaj kontext z neural memory
        context = self.memory.recall_context(user_text, top_k=3)
        enhanced_prompt = SYSTEM_PROMPT
        if context:
            enhanced_prompt += f"\n\nRelevantní kontext z paměti:\n{context}"

        payload = {
            "model":    self.model,
            "messages": [{"role": "system", "content": enhanced_prompt},
                         *list(self.history)],
            "stream":   False,
            "options":  {"temperature": 0.3, "num_predict": 800},
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=60)
            resp.raise_for_status()
            raw  = resp.json().get("message", {}).get("content", "").strip()
            self.history.append({"role": "assistant", "content": raw})

            # Ulož konverzaci do neural memory s vyšší důležitostí pro AI odpovědi
            self.memory.store_conversation(user_text, raw, importance=0.6)

            return raw, {"action": "answer", "params": {}}
        except requests.Timeout:
            self.history.pop()
            return "Ollama nereaguje (timeout).", {"action": "answer", "params": {}}
        except Exception as e:
            self.history.pop()
            return f"Chyba: {e}", {"action": "answer", "params": {}}

    # ── STREAM ASK ───────────────────────────────────

    def stream_ask(self, user_text: str):
        msg, action = self._quick_match(user_text)
        if action is not None:
            self.history.append({"role": "user",     "content": user_text})
            self.history.append({"role": "assistant", "content": msg or ""})
            # Ulož konverzaci do neural memory
            if msg:
                self.memory.store_conversation(user_text, msg or "", importance=0.3)
            if msg:
                yield msg
            return

        self.history.append({"role": "user", "content": user_text})
        self._stream_resp = None

        # Získaj kontext z neural memory
        context = self.memory.recall_context(user_text, top_k=3)
        enhanced_prompt = SYSTEM_PROMPT
        if context:
            enhanced_prompt += f"\n\nRelevantní kontext z paměti:\n{context}"

        payload = {
            "model":    self.model,
            "messages": [{"role": "system", "content": enhanced_prompt},
                         *list(self.history)],
            "stream":   True,
            "options":  {"temperature": 0.3, "num_predict": 800},
        }
        try:
            self._stream_resp = requests.post(
                self.url, json=payload, stream=True, timeout=60)
            self._stream_resp.raise_for_status()
            full_response = ""
            for line in self._stream_resp.iter_lines():
                if not line:
                    continue
                try:
                    data  = json.loads(line.decode("utf-8"))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        full_response += chunk
                        yield chunk
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

            # Ulož konverzaci do neural memory
            if full_response.strip():
                self.memory.store_conversation(user_text, full_response.strip(), importance=0.6)

        except Exception as e:
            logger.error(f"Stream chyba: {e}")
            yield f"Chyba: {e}"
        finally:
            self._stream_resp = None

    def drain_stream(self):
        if self._stream_resp is None:
            return
        try:
            for line in self._stream_resp.iter_lines():
                if not line:
                    continue
                try:
                    data  = json.loads(line.decode("utf-8"))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        finally:
            self._stream_resp = None

    # ── PARSE RESPONSE (pouze pro LLM výstup) ────────

    def _parse_response(self, raw: str) -> Tuple[str, Dict]:
        return raw, {"action": "answer", "params": {}}

    def _default_message(self, command: str, args: str = "") -> str:
        msgs = {
            "open_app":       f"Spouštím {args}.",
            "kill_process":   f"Ukončuji {args}.",
            "open_url":       "Otevírám stránku.",
            "search_web":     f"Hledám: {args}.",
            "youtube_play":   f"Přehrávám: {args}.",
            "weather":        f"Počasí {args}.",
            "shutdown":       "Vypínám počítač.",
            "restart":        "Restartuji.",
            "sleep_pc":       "Uspávám.",
            "screenshot":     "Screenshot.",
            "system_info":    "Systémové info.",
            "set_timer":      "Timer nastaven.",
            "calculate":      f"Výpočet: {args}",
            "translate":      f"Překlad: {args}",
            "note_add":       "Poznámka uložena.",
            "note_list":      "Poznámky:",
            "reminder_set":   "Připomínka nastavena.",
            "wiki_search":    f"Wikipedia: {args}",
            "currency_convert": f"Převod měny: {args}",
            "memory_recall":  f"Vyhledávání v paměti: {args}",
            "memory_store":   "Uloženo do paměti.",
            "memory_stats":   "Statistiky paměti.",
            "memory_maintenance": "Údržba paměti dokončena.",
            "create_folder":  "Složka vytvořena.",
            "volume":         "Hlasitost nastavena.",
            "set_brightness": f"Jas: {args}%.",
        }
        return msgs.get(command, f"Akce: {command}")

    def clear_history(self):
        self.history.clear()

    def is_available(self) -> bool:
        try:
            resp = requests.get(
                self.url.replace("/api/chat", "/api/tags"), timeout=3)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════
#  MULTIMODÁLNÍ PODPORA (LLaVA / BakLLaVA)
# ══════════════════════════════════════════════════════

import base64
import tempfile

def ask_vision(prompt: str, image_path: str, model: str = "llava:7b",
               ollama_url: str = "http://localhost:11434/api/chat") -> str:
    """
    Pošle screenshot + otázku do multimodálního modelu (LLaVA).
    Použití: ask_vision("Co vidíš na obrazovce?", "/tmp/screen.png")
    """
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [img_b64],
            }],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        resp = requests.post(ollama_url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "Žádná odpověď.")
    except Exception as e:
        return f"Chyba vision modelu: {e}"
