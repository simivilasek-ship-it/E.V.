"""
JARVIS v4.4 — LLM Engine (Ollama HTTP klient)
Lokální router je v local_router.py.

OllamaClient — sdílený HTTP klient pro agenty (agent_graph, agent_react).
"""

import re
import json
import requests
import logging
from typing import Dict, Tuple
from collections import deque

from memory import JarvisMemory

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

DŮLEŽITÉ — AKTUÁLNÍ DATA:
- Nemáš přístup k internetu ani realtime datům (výsledky zápasů, kurzy, počasí, zprávy).
- Pokud se tě ptají na aktuální výsledky sportovních zápasů, ceny, novinky nebo kurzy:
  → Řekni co víš ze svého tréninku (může být zastaralé), ale doporuč: „Řekni mi 'vyhledej [dotaz]' a podívám se online."
  → NIKDY nevymýšlej aktuální výsledky ani data, která nemůžeš znát.
  → NIKDY nepiš kód pro scraping místo přímé odpovědi.

FORMÁT:
- Stručné a přesné odpovědi
- Kód vždy v markdown: ```python ... ```
- Pro sport/novinky: stručná odpověď + tip na hledání

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

    def call_json(self, messages: list, schema: dict = None,
                  temperature: float = 0.0, max_tokens: int = 500,
                  timeout: int = 60) -> dict:
        """Vynutí JSON výstup přes Ollama format:'json'. Vrátí dict nebo {} při chybě.

        schema — volitelný příklad/popis struktury přidaný do system promptu.
        """
        if schema:
            hint = f"\n\nOdpověz VÝHRADNĚ platným JSON objektem se strukturou: {json.dumps(schema, ensure_ascii=False)}"
            msgs = list(messages)
            if msgs and msgs[0]["role"] == "system":
                msgs[0] = {**msgs[0], "content": msgs[0]["content"] + hint}
            else:
                msgs.insert(0, {"role": "system", "content": hint.lstrip()})
        else:
            msgs = messages

        payload = {
            "model":    self.model,
            "messages": msgs,
            "stream":   False,
            "format":   "json",
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content", "").strip()
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"OllamaClient.call_json: JSON parse error: {e} — raw: {raw[:120]}")
            return {}
        except Exception as e:
            logger.error(f"OllamaClient.call_json chyba: {e}")
            return {}


# ══════════════════════════════════════════════════════
#  LLM ENGINE
# ══════════════════════════════════════════════════════

class _LLMCache:
    """LRU cache pro LLM odpovědi — opakované dotazy nevytěžují Ollama.

    Cache key = (model, normalized_text). TTL 10 minut, max 200 záznamů.
    Vyřazuje faktické/real-time dotazy (počasí, čas, sport).
    """
    _NO_CACHE = re.compile(
        r"\b(pocasi|weather|cas|hodin|sport|zapas|live|dnes|ted|nyni"
        r"|aktualni|kurz|bitcoin|ethereum|cena\s+\w+)\b", re.I)

    def __init__(self, maxsize: int = 200, ttl: int = 600):
        self._store: dict = {}   # key → (response, action, timestamp)
        self._maxsize = maxsize
        self._ttl     = ttl

    def _key(self, model: str, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return f"{model}::{normalized}"

    def get(self, model: str, text: str):
        if self._NO_CACHE.search(text):
            return None
        k = self._key(model, text)
        entry = self._store.get(k)
        if entry and (time.time() - entry[2]) < self._ttl:
            logger.debug(f"LLM cache hit: {text[:50]}")
            return entry[0], entry[1]
        if entry:
            del self._store[k]
        return None

    def set(self, model: str, text: str, response: str, action: dict):
        if self._NO_CACHE.search(text):
            return
        if len(self._store) >= self._maxsize:
            # Vyhoď nejstarší
            oldest = min(self._store, key=lambda k: self._store[k][2])
            del self._store[oldest]
        self._store[self._key(model, text)] = (response, action, time.time())

    def clear(self):
        self._store.clear()

    def stats(self) -> dict:
        import time as _t
        now = _t.time()
        valid = sum(1 for v in self._store.values() if now - v[2] < self._ttl)
        return {"total": len(self._store), "valid": valid, "ttl": self._ttl}


# Globální cache sdílená napříč instancemi LLMEngine
_llm_cache = _LLMCache()


class LLMEngine:

    def __init__(self, config: dict, memory: JarvisMemory = None):
        self.config  = config
        self.url     = config["ollama_url"]
        self.model   = config["ollama_model"]
        self.history: deque = deque(maxlen=config.get("history_size", 20))
        self.memory  = memory or JarvisMemory(config)
        self._stream_resp = None
        self._profile_context = ""   # injektovaný souhrn UserProfile
        self._cache  = _llm_cache    # sdílená instance

        from llm_router import LLMRouter
        self._llm_router = LLMRouter(self.url, self.model)
        logger.info(f"LLM: {self.model} @ {self.url} + Neural Memory + LLMRouter + Cache")

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

        # Cache hit — vrátí okamžitě bez Ollama
        cached = self._cache.get(self.model, user_text)
        if cached:
            raw, action = cached
            self.history.append({"role": "user",      "content": user_text})
            self.history.append({"role": "assistant",  "content": raw})
            return raw, action

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
            # Ulož do cache (faktické dotazy se nevyřadí automaticky uvnitř .set())
            answer_action = {"action": "answer", "params": {}}
            self._cache.set(self.model, user_text, raw, answer_action)
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
