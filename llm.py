"""
JARVIS v2.0 — LLM komunikace
Komunikace s Ollama API
"""

import requests
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)

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
- spotify_play  — přehraj na Spotify,    params: {"query": "název skladby nebo interpreta"}
- youtube_play  — přehraj na YouTube,     params: {"query": "search text", "audio_only": false}
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
"Přehraj/zastav"      → {"action": "media", "params": {"action": "play_pause"}, "message": "Přepínám přehrávání."}
"Přehraj v Spotify Can I" → {"action": "spotify_play", "params": {"query": "Can I Drake"}, "message": "Hledám v Spotify."}
"Přehraj YouTube video" → {"action": "youtube_play", "params": {"query": "Nights Frank Ocean"}, "message": "Otevírám YouTube."}
"Ukonči notepad"      → {"action": "kill_process", "params": {"name": "notepad.exe"}, "message": "Ukončuji Notepad."}
"Jak se jmenuješ?"    → {"action": "answer", "params": {}, "message": "Jsem JARVIS, tvůj osobní asistent."}

Odpovídej POUZE validním JSON, nic jiného."""

class LLMEngine:
    """Engine pro komunikaci s LLM"""

    def __init__(self, config: dict):
        self.config = config
        self.url = config["ollama_url"]
        self.model = config["ollama_model"]
        self.history = deque(maxlen=config.get("history_size", 20))
        logger.info(f"LLM engine inicializován: {self.model} @ {self.url}")

    def ask(self, user_text: str) -> Tuple[str, Dict[str, any]]:
        """
        Zeptá se modelu a vrátí (message, action_data)
        action_data obsahuje action a params
        """
        # Přidej uživatelskou zprávu do historie
        self.history.append({"role": "user", "content": user_text})

        # Připrav payload
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(self.history)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 300},
        }

        try:
            logger.debug(f"Odesílám dotaz na {self.url}")
            resp = requests.post(self.url, json=payload, timeout=30)
            resp.raise_for_status()

            raw_response = resp.json().get("message", {}).get("content", "").strip()
            logger.debug(f"Syrová odpověď: {raw_response[:100]}...")

            # Přidej odpověď do historie
            self.history.append({"role": "assistant", "content": raw_response})

            # Parsuj JSON
            action_data = self._parse_response(raw_response)
            message = action_data.get("message", "Nerozuměl jsem.")

            return message, action_data

        except requests.Timeout:
            logger.error("LLM timeout")
            return "Ollama nereaguje (timeout).", {"action": "answer", "params": {}}
        except requests.RequestException as e:
            logger.error(f"LLM request error: {e}")
            return f"Chyba připojení k Ollama: {e}", {"action": "answer", "params": {}}
        except Exception as e:
            logger.error(f"LLM chyba: {e}")
            return f"Chyba: {e}", {"action": "answer", "params": {}}

    def _parse_response(self, raw: str) -> Dict[str, any]:
        """Parsuje JSON odpověď z modelu"""
        # Najdi JSON v odpovědi
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Neplatný JSON v odpovědi modelu")
        else:
            logger.warning("Žádný JSON nenalezen v odpovědi modelu")

        # Fallback
        return {"action": "answer", "params": {}, "message": raw or "Nerozuměl jsem."}

    def clear_history(self) -> None:
        """Vymaže historii konverzace"""
        self.history.clear()
        logger.info("Historie konverzace vymazána")

    def is_available(self) -> bool:
        """Zkontroluje dostupnost Ollama"""
        try:
            resp = requests.get(self.url.replace("/api/chat", "/api/tags"), timeout=3)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return self.model in models
            return False
        except Exception:
            return False