"""
JARVIS v4.2 — LLM Engine (Ollama HTTP klient)
Lokální router je v local_router.py.

OllamaClient — sdílený HTTP klient pro agenty (agent_graph, agent_react).
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
    _HOME, _USER,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  SYSTÉMOVÝ PROMPT — pouze pro AI konverzaci
# ══════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""Jsi JARVIS — lokální AI asistent uživatele {_USER}. Komunikuješ česky.

TVOJE ROLE:
Odpovídáš na otázky, píšeš kód, vysvětluješ pojmy, překládáš, počítáš, pomáháš s analýzou.
Systémové příkazy (otevři aplikaci, změň hlasitost, udělej screenshot…) zpracovává lokální router — ty se jimi nezabývej.

FORMÁT:
- Stručné a přesné odpovědi
- Kód vždy v markdown: ```python ... ```
- Pokud je otázka nejasná, zeptej se na upřesnění

PAMĚŤ:
Máš přístup k relevantnímu kontextu z předchozích konverzací (viz sekce "Relevantní kontext" níže).
Využij ho pro osobnější a přesnější odpovědi."""


# ══════════════════════════════════════════════════════
#  OLLAMA CLIENT — sdílený HTTP klient pro agenty
# ══════════════════════════════════════════════════════

class OllamaClient:
    """Jednoduchý synchronní HTTP klient pro Ollama /api/chat.

    Používají ho agent_graph.py a agent_react.py místo duplicitní _llm() metody.
    Při chybě vrátí prázdný string (agenti musí ošetřit sami).
    """

    def __init__(self, url: str, model: str):
        self.url   = url
        self.model = model

    def call(self, messages: list, temperature: float = 0.1,
             max_tokens: int = 500, timeout: int = 60) -> str:
        payload = {
            "model":    self.model,
            "messages": messages,
            "stream":   False,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"OllamaClient chyba: {e}")
            return ""


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

    # ── SHARED: sestavení messages pro LLM ───────────

    def _build_messages(self, user_text: str) -> tuple:
        """Vrátí (messages, routed_model, temperature, max_tokens) pro LLM volání."""
        self._extract_user_facts(user_text)

        context = self.memory.recall_context(user_text, top_k=3)
        system = self._build_system_prompt()
        if context:
            system += f"\n\nRelevantní kontext z paměti:\n{context}"

        # Přidej kontext prostředí do system promptu
        try:
            from context_orchestrator import get_context_orchestrator
            ctx = get_context_orchestrator().get_context()
            if ctx:
                system += f"\n\nKontext prostředí:\n{ctx}"
        except Exception:
            pass

        task = self._llm_router.detect_task(user_text)
        routed_model, temperature, max_tokens = self._llm_router.get_model_for_task(task)

        messages = [{"role": "system", "content": system}, *list(self.history)]
        MAX_CONTEXT = 3072
        while len(messages) > 2:
            used = sum(len(m.get("content", "")) for m in messages) // 4
            if used + max_tokens <= MAX_CONTEXT:
                break
            messages.pop(1)

        return messages, routed_model, temperature, max_tokens

    # ── ASK (non-streaming) ──────────────────────────

    def ask(self, user_text: str) -> Tuple[str, Dict]:
        msg, action = self.quick_match(user_text)
        if action is not None:
            # Do LLM history ukládáme jen informační odpovědi, ne akce (otevři, zavři…)
            if action.get("action") == "answer" and msg:
                self.history.append({"role": "user",     "content": user_text})
                self.history.append({"role": "assistant", "content": msg})
                try:
                    self.memory.store_conversation(user_text, msg, importance=0.4)
                except Exception as _mem_err:
                    logger.warning(f"Memory store selhalo (ignorováno): {_mem_err}")
            return msg or "", action

        self.history.append({"role": "user", "content": user_text})
        messages, routed_model, temperature, max_tokens = self._build_messages(user_text)
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
            try:
                self.memory.store_conversation(user_text, raw, importance=0.6)
            except Exception as _me:
                logger.warning(f"Memory store chyba (ignorováno): {_me}")
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
            if action.get("action") == "answer" and msg:
                self.history.append({"role": "user",     "content": user_text})
                self.history.append({"role": "assistant", "content": msg})
                try:
                    self.memory.store_conversation(user_text, msg, importance=0.4)
                except Exception as _mem_err:
                    logger.warning(f"Memory store selhalo (ignorováno): {_mem_err}")
            # Vždy yield string — nikdy nekončit generátor bez yield (frontend by dostal prázdný stream)
            yield msg or ""
            return

        self.history.append({"role": "user", "content": user_text})
        self._stream_resp = None
        messages, routed_model, temperature, max_tokens = self._build_messages(user_text)
        payload = {
            "model":    routed_model,
            "messages": messages,
            "stream":   True,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        full_response = ""
        try:
            self._stream_resp = requests.post(
                self.url, json=payload, stream=True, timeout=60)
            self._stream_resp.raise_for_status()
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

            if full_response.strip():
                try:
                    self.memory.store_conversation(user_text, full_response.strip(), importance=0.6)
                except Exception as _me:
                    logger.warning(f"Memory store chyba (ignorováno): {_me}")

        except Exception as e:
            logger.error(f"Stream chyba: {e}")
            self.history.pop()
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
