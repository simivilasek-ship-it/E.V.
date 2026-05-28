"""
JARVIS v4.2 — LLM Engine (Ollama HTTP klient)
Lokální router je v local_router.py.
"""

import os
import re
import json
import requests
import logging
from datetime import datetime
from typing import Dict, Tuple
from collections import deque

from memory import JarvisMemory
from commands.utils import normalize_text as _norm

# Re-export router symbols for backward compatibility
from local_router import (
    LocalRouter, _router,
    _parse_args,
    _HAS_FUZZY, _FUZZY_THRESHOLD, _FUZZY_COMMANDS,
    _HOME as _HOME, _USER as _USER,
)

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

Pokud nevíš co uživatel chce (nejasný příkaz), VŽDY se zeptej upřesňující otázkou místo hádání.
Příklad: "Chceš otevřít web, spustit aplikaci, nebo něco jiného?"

Neodpovídej žádným COMMAND formátem — to zpracovává lokální systém automaticky."""


# ══════════════════════════════════════════════════════
#  LLM ENGINE
# ══════════════════════════════════════════════════════

class LLMEngine:

    def __init__(self, config: dict, memory: JarvisMemory = None):
        self.config  = config
        self.url     = config["ollama_url"]
        self.model   = config["ollama_model"]
        self.history: deque = deque(maxlen=config.get("history_size", 20))
        self.memory  = memory or JarvisMemory(config)
        self._stream_resp = None
        self._profile_context = ""   # injektovaný souhrn UserProfile

        from llm_router import LLMRouter
        self._llm_router = LLMRouter(self.url, self.model)
        logger.info(f"LLM: {self.model} @ {self.url} + Neural Memory + LLMRouter")

    def _extract_user_facts(self, text: str) -> None:
        """Zkusí extrahovat fakta o uživateli z jeho zprávy do UserProfile."""
        try:
            from user_profile import get_user_profile
            found = get_user_profile().extract_from_text(text)
            if found:
                # Aktualizuj inject po extrakci
                self.inject_profile(get_user_profile().summary())
        except Exception:
            pass

    def inject_profile(self, profile_summary: str) -> None:
        """Vloží souhrn UserProfile do systémového promptu pro každý dotaz."""
        self._profile_context = profile_summary
        logger.info(f"UserProfile injektován do LLM ({len(profile_summary)} znaků)")

    def _build_system_prompt(self) -> str:
        """Sestaví systémový prompt včetně user profilu."""
        prompt = SYSTEM_PROMPT
        if self._profile_context:
            prompt += f"\n\n{self._profile_context}"
        return prompt

    # ── QUICK MATCH (lokální router) ─────────────────

    def quick_match(self, text: str) -> tuple:
        return _router.route(text)

    # ── ASK (non-streaming) ──────────────────────────

    def ask(self, user_text: str) -> Tuple[str, Dict]:
        msg, action = self.quick_match(user_text)
        if action is not None:
            # Do LLM history ukládáme jen informační odpovědi, ne akce (otevři, zavři…)
            action_name = action.get("action", "")
            if action_name == "answer" and msg:
                self.history.append({"role": "user",     "content": user_text})
                self.history.append({"role": "assistant", "content": msg})
                self.memory.store_conversation(user_text, msg, importance=0.4)
            return msg or "", action

        self.history.append({"role": "user", "content": user_text})

        # Extrahuj fakta o uživateli z textu
        self._extract_user_facts(user_text)

        # Sestaví systémový prompt (SYSTEM_PROMPT + UserProfile + memory kontext)
        context = self.memory.recall_context(user_text, top_k=3)
        system = self._build_system_prompt()
        if context:
            system += f"\n\nRelevantní kontext z paměti:\n{context}"

        task = self._llm_router.detect_task(user_text)
        routed_model, temperature, max_tokens = self._llm_router.get_model_for_task(task)

        messages = [{"role": "system", "content": system}, *list(self.history)]
        # Odhadni spotřebované tokeny (1 token ≈ 4 znaky) a zkraťuj historii dokud
        # nezůstane alespoň 512 tokenů pro odpověď.
        MAX_CONTEXT = 3072
        while len(messages) > 2:
            used = sum(len(m.get("content", "")) for m in messages) // 4
            if used + max_tokens <= MAX_CONTEXT:
                break
            messages.pop(1)  # odstraň nejstarší user/assistant pár (index 1, za system)

        payload = {
            "model":    routed_model,
            "messages": messages,
            "stream":   False,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=60)
            resp.raise_for_status()
            raw  = resp.json().get("message", {}).get("content", "").strip()
            self.history.append({"role": "assistant", "content": raw})
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
        msg, action = self.quick_match(user_text)
        if action is not None:
            # Do LLM history ukládáme jen informační odpovědi, ne akce (otevři, zavři…)
            action_name = action.get("action", "")
            if action_name == "answer" and msg:
                self.history.append({"role": "user",     "content": user_text})
                self.history.append({"role": "assistant", "content": msg})
                self.memory.store_conversation(user_text, msg, importance=0.4)
            if msg:
                yield msg
            return

        self.history.append({"role": "user", "content": user_text})
        self._stream_resp = None

        # Extrahuj fakta o uživateli z textu
        self._extract_user_facts(user_text)

        context = self.memory.recall_context(user_text, top_k=3)
        system = self._build_system_prompt()
        if context:
            system += f"\n\nRelevantní kontext z paměti:\n{context}"

        task = self._llm_router.detect_task(user_text)
        routed_model, temperature, max_tokens = self._llm_router.get_model_for_task(task)

        messages = [{"role": "system", "content": system}, *list(self.history)]
        MAX_CONTEXT = 3072
        while len(messages) > 2:
            used = sum(len(m.get("content", "")) for m in messages) // 4
            if used + max_tokens <= MAX_CONTEXT:
                break
            messages.pop(1)

        payload = {
            "model":    routed_model,
            "messages": messages,
            "stream":   True,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
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
               ollama_url: str = None) -> str:
    """
    Pošle screenshot + otázku do multimodálního modelu (LLaVA).
    Použití: ask_vision("Co vidíš na obrazovce?", "/tmp/screen.png")
    """
    try:
        from config import CONFIG
        url = ollama_url or CONFIG.get("ollama_url", "http://localhost:11434/api/chat")

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
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "Žádná odpověď.")
    except Exception as e:
        return f"Chyba vision modelu: {e}"
