"""
JARVIS v4.6 — LLM Engine (Ollama HTTP klient)
Lokální router je v local_router.py.

OllamaClient — sdílený HTTP klient pro agenty (agent_graph, agent_react).
"""

import re
import json
import time
import json as _json
import requests
import logging
from collections import deque
from collections import deque as _deque
from pathlib import Path as _Path
from threading import Lock as _Lock
from typing import Callable, Dict, Optional, Tuple

from memory import JarvisMemory

# Re-export router symbols for backward compatibility
# POZOR: záměrné re-exporty pro test_jarvis.py — nemazat!
from local_router import (  # noqa: F401
    LocalRouter, _router,
    _parse_args,
    _HAS_FUZZY, _FUZZY_THRESHOLD, _FUZZY_COMMANDS,
    _HOME, _USER,
)
# Potlač ruff F401 pro re-exporty
__all__ = [*(globals().get("__all__", [])), "LocalRouter"]

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  SYSTÉMOVÝ PROMPT — pouze pro AI konverzaci
# ══════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""Jsi JARVIS — lokální AI asistent uživatele {_USER}. Komunikuješ česky.
Funguješ jako Copilot / Gemini: chytrý konverzační parťák s plným vědomím o jeho počítači.

TŘI REŽIMY (automaticky):
1. COPILOT — konverzace, kód, vysvětlení, brainstorming. Odpovídáš ty (tady).
2. AKCE — uživatel řekne příkaz přirozeně (otevři chrome, screenshot, hlasitost 50, přehled PC…)
   → provede lokální router. Ty jen poradíš co říct, pokud se ptá.
3. AGENT — složité úkoly (najdi X a ulož, zkontroluj a pak…, analyzuj projekt…)
   → řeší agentní pipeline. Ty můžeš navrhnout formulaci úkolu.

CO VIDÍŠ (Kontext prostředí — živá data z PC):
- Aktivní okno, otevřená okna, schránka
- CPU, RAM, disk, hostname, OS, čas
Tato data JSOU přesná — používej je aktivně, nevymýšlej.
Cursor = Cursor (NE VS Code). Když kontext chybí, přiznej to.

JAK SE CHOVAT (Copilot styl):
- Odpovídej konkrétně podle toho, co uživatel právě dělá (aktivní okno).
- Navrhuj akce: „Chceš otevřít…", „Můžu udělat screenshot", „Řekni přehled o PC".
- Buď stručný, přátelský, bez „Jako AI model…" nebo „Nemám přístup k obrazovce" když kontext máš.

CO NEVIDÍŠ přímo (ale JARVIS umí na požádání):
- Live web data → uživatel: „vyhledej [dotaz]" nebo „jaké je počasí v Praze"
- Hluboký HW detail → „řekni komponenty" / „přehled o PC"

FORMÁT: markdown pro kód, jinak stručná prose.

PAMĚŤ: využij relevantní kontext z předchozích konverzací."""



# ══════════════════════════════════════════════════════
#  RATE LIMITER — ochrana před zahlcením Ollama
# ══════════════════════════════════════════════════════

class LLMRateLimiter:
    """Token bucket rate limiter — max N dotazů za minutu.

    Zabrání zahltění Ollama při rychlém opakovaném volání.
    Thread-safe pomocí Lock.
    """

    def __init__(self, max_per_minute: int = 30):
        self._max = max_per_minute
        self._times: _deque = _deque(maxlen=max_per_minute)
        self._lock = _Lock()

    def is_allowed(self) -> bool:
        """True pokud je dotaz povolen (nevyčerpal limit)."""
        with self._lock:
            now = time.monotonic()
            # Odstraň starší než 60s
            cutoff = now - 60.0
            while self._times and self._times[0] < cutoff:
                self._times.popleft()
            if len(self._times) >= self._max:
                return False
            self._times.append(now)
            return True

    def wait_if_needed(self) -> None:
        """Počká pokud je překročen limit (max 2s)."""
        if not self.is_allowed():
            logger.warning(f"LLM rate limit dosažen ({self._max}/min) — čekám 1s")
            time.sleep(1.0)
            self.is_allowed()  # Zaloguje ale pokračuje

    def stats(self) -> dict:
        with self._lock:
            return {"calls_last_minute": len(self._times), "limit": self._max}


# Globální rate limiter
_rate_limiter = LLMRateLimiter(max_per_minute=30)

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

    def call(self, messages: list[dict], temperature: float = 0.1,
             max_tokens: int = 500, timeout: int = 60) -> str:
        import json as _json
        import hashlib as _hashlib
        from cache_manager import get_cache_manager

        try:
            payload_str = _json.dumps({
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }, sort_keys=True)
            key_hash = _hashlib.md5(payload_str.encode("utf-8")).hexdigest()
            cache_key = f"ollama_client_call:{key_hash}"
            
            cache = get_cache_manager()
            cached = cache.get(cache_key, backend="memory")
            if cached is not None:
                logger.info(f"OllamaClient cache hit for model {self.model}")
                return cached
        except Exception as e:
            logger.debug(f"OllamaClient cache lookup chyba: {e}")
            cache_key = None

        payload = {
            "model":    self.model,
            "messages": messages,
            "stream":   False,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            result = r.json().get("message", {}).get("content", "").strip()
            if result and cache_key:
                try:
                    cache.set(cache_key, result, ttl=300, backend="memory")
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.error(f"OllamaClient chyba: {e}")
            return ""

    def call_json(self, messages: list[dict], schema: dict | None = None,
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

        import json as _json
        import hashlib as _hashlib
        from cache_manager import get_cache_manager
        
        try:
            payload_str = _json.dumps({
                "model": self.model,
                "messages": msgs,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "format": "json"
            }, sort_keys=True)
            key_hash = _hashlib.md5(payload_str.encode("utf-8")).hexdigest()
            cache_key = f"ollama_client_json:{key_hash}"
            
            cache = get_cache_manager()
            cached = cache.get(cache_key, backend="memory")
            if cached is not None:
                logger.info(f"OllamaClient JSON cache hit for model {self.model}")
                return cached
        except Exception as e:
            logger.debug(f"OllamaClient JSON cache lookup chyba: {e}")
            cache_key = None

        payload = {
            "model":    self.model,
            "messages": msgs,
            "stream":   False,
            "format":   "json",
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        raw = ""
        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content", "").strip()
            result = json.loads(raw)
            if result and cache_key:
                try:
                    cache.set(cache_key, result, ttl=300, backend="memory")
                except Exception:
                    pass
            return result
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
        import time as _t
        entry = self._store.get(k)
        if entry and (_t.time() - entry[2]) < self._ttl:
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
        import time as _t
        self._store[self._key(model, text)] = (response, action, _t.time())

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

        from cloud_router import get_cloud_router
        self._cloud = get_cloud_router(config)
        _cloud_tag = "✓ cloud" if self._cloud.enabled else "✗ cloud (bez API klíče)"

        from graph_extractor import get_graph_rag
        self._graph_rag = get_graph_rag(config)

        logger.info(f"LLM: {self.model} @ {self.url} + Neural Memory + GraphRAG + LLMRouter + Cache + {_cloud_tag}")

    def _extract_user_facts(self, text: str) -> None:
        """Zkusí extrahovat fakta o uživateli z jeho zprávy do UserProfile a paměti."""
        try:
            from user_profile import get_user_profile
            from commands.utils import normalize_text as _norm

            profile = get_user_profile()
            found = profile.extract_from_text(text)
            t = _norm(text)

            # Město z dotazů na počasí: "jake je pocasi v praze"
            if re.search(r"\b(pocasi|weather)\b", t):
                m = re.search(r"\b(?:v|ve)\s+([a-z]+(?:\s+[a-z]+)?)", t)
                if m:
                    city = m.group(1).strip().title()
                    if city.lower() not in (
                        "pocasi", "weather", "dnes", "zitra", "bude", "jake", "je",
                    ):
                        profile.set("město", city, confidence=0.7, source="inferred")
                        self.memory.store(
                            f"Preferované město pro počasí: {city}", importance=0.65,
                        )
                        found.append("město")

            # Explicitní preference: "preferuji X"
            m = re.search(r"\bpreferuji\s+(.{2,40}?)(?:\.|,|$)", t)
            if m:
                pref = m.group(1).strip()
                if len(pref) >= 2:
                    existing = profile.get("preference") or []
                    if not isinstance(existing, list):
                        existing = [existing] if existing else []
                    if pref not in existing:
                        existing.append(pref)
                    profile.set("preference", existing, confidence=0.7, source="extracted")
                    self.memory.store(f"Uživatel preferuje: {pref}", importance=0.6)
                    found.append("preference")

            # Oblíbené aplikace z open_app příkazů
            m = re.search(r"\b(otevri|spust|open|start)\s+(\w+)", t)
            if m:
                app = m.group(2).strip()
                if app not in ("to", "mi", "prosim", "aplikaci", "program") and len(app) >= 2:
                    favs = profile.get("oblíbené_aplikace") or []
                    if not isinstance(favs, list):
                        favs = [favs] if favs else []
                    if app not in favs:
                        favs.append(app)
                        profile.set(
                            "oblíbené_aplikace", favs, confidence=0.5, source="inferred",
                        )
                        self.memory.store(f"Často otevírá aplikaci: {app}", importance=0.4)
                        found.append("oblíbené_aplikace")

            if found:
                self.inject_profile(profile.summary())
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

        # GraphRAG — znalostní kontext z entity grafu
        try:
            graph_ctx = self._graph_rag.recall_graph_context(user_text)
            if graph_ctx:
                system += f"\n\n{graph_ctx}"
        except Exception:
            pass

        # Přidej kontext prostředí do system promptu
        try:
            from context_orchestrator import get_context_orchestrator
            ctx = get_context_orchestrator().get_context()
            if ctx:
                system += f"\n\nKontext prostředí:\n{ctx}"
        except Exception:
            pass

        # Document RAG — injektuj relevantní pasáže z nahraných dokumentů
        try:
            from doc_ingestion import query_docs, list_docs
            if list_docs():
                passages = query_docs(user_text, top_k=3, max_chars=2000)
                if passages:
                    system += f"\n\nRelevantní pasáže z dokumentů uživatele:\n{passages}"
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
        if not getattr(self, '_ollama_available', True):
            return "Ollama není dostupná. Řekni mi lokální příkaz (otevři, nastav, screenshot...).", {"action": "answer", "params": {}}
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

        # Rate limiting — pouze pro LLM volání (local router prošel výše)
        _rate_limiter.wait_if_needed()

        self.history.append({"role": "user", "content": user_text})
        messages, routed_model, temperature, max_tokens = self._build_messages(user_text)

        # ── Cloud routing (Groq / OpenRouter) ────────────────────────────────
        task = self._llm_router.detect_task(user_text)
        task_str = task.value if hasattr(task, "value") else str(task)
        if self._cloud.should_use_cloud(task_str):
            try:
                cloud_resp = self._cloud.call(
                    messages, task_type=task_str,
                    temperature=temperature, max_tokens=max_tokens,
                )
                raw = cloud_resp.content
                logger.info(f"Cloud: {cloud_resp.provider}/{cloud_resp.model} "
                            f"{cloud_resp.latency_ms:.0f}ms {cloud_resp.tokens_used}tok")
                self.history.append({"role": "assistant", "content": raw})
                self._cache.set(self.model, user_text, raw, {"action": "answer", "params": {}})
                try:
                    self.memory.store_conversation(user_text, raw, importance=0.6)
                except Exception:
                    pass
                # GraphRAG extrakce na pozadí
                try:
                    self._graph_rag.extract_and_store(user_text, raw)
                except Exception:
                    pass
                return raw, {"action": "answer", "params": {}, "provider": cloud_resp.provider}
            except Exception as _ce:
                logger.warning(f"Cloud routing selhal ({_ce}), fallback na Ollama")

        # ── Ollama fallback ───────────────────────────────────────────────────
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
            # Self-debugging: oprav odpověď pokud obsahuje chybové patterny
            try:
                from agent_roles import SelfDebuggingAgent
                _debugger = SelfDebuggingAgent(self.url, self.model)
                if _debugger.has_error(raw):
                    logger.info("Self-debugging: detekována chyba v odpovědi, opravuji...")
                    raw = _debugger.debug_and_fix(user_text, raw)
            except Exception as _dbg_err:
                logger.debug(f"Self-debugging přeskočen: {_dbg_err}")
            self.history.append({"role": "assistant", "content": raw})
            # Ulož do cache (faktické dotazy se nevyřadí automaticky uvnitř .set())
            answer_action = {"action": "answer", "params": {}}
            self._cache.set(self.model, user_text, raw, answer_action)
            try:
                self.memory.store_conversation(user_text, raw, importance=0.6)
            except Exception as _me:
                logger.warning(f"Memory store chyba (ignorováno): {_me}")
            # GraphRAG extrakce
            try:
                self._graph_rag.extract_and_store(user_text, raw)
            except Exception:
                pass
            return raw, {"action": "answer", "params": {}}
        except requests.Timeout:
            self.history.pop()
            return "Ollama nereaguje (timeout).", {"action": "answer", "params": {}}
        except Exception as e:
            self.history.pop()
            return f"Chyba: {e}", {"action": "answer", "params": {}}

    # ── COPILOT TOOL-CALLING ─────────────────────────

    _COPILOT_TOOLS_HINT = (
        "\n\nMáš k dispozici nástroje pro akce na PC (otevření app, screenshot, počasí…). "
        "Použij je, když uživatel chce provést akci. Jinak odpověz konverzačně."
    )

    def try_copilot_tools(
        self,
        user_text: str,
        tools_schema: list,
        on_tool_call: Callable[[str, dict], str],
        *,
        max_rounds: int = 2,
    ) -> Optional[str]:
        """Ollama nativní tool-calling pro Copilot.

        Vrátí finální text pokud model odpověděl nebo nástroj proběhl.
        Vrátí None pokud tool-calling selhal — volající použije stream_ask().
        """
        if not tools_schema or not getattr(self, "_ollama_available", True):
            return None

        _rate_limiter.wait_if_needed()
        messages, routed_model, temperature, max_tokens = self._build_messages(user_text)
        if messages and messages[0]["role"] == "system":
            messages[0] = {
                **messages[0],
                "content": messages[0]["content"] + self._COPILOT_TOOLS_HINT,
            }

        last_observation = ""

        for _round in range(max_rounds):
            payload = {
                "model":    routed_model,
                "messages": messages,
                "tools":    tools_schema,
                "stream":   False,
                "options":  {"temperature": temperature, "num_predict": max_tokens},
            }
            try:
                resp = requests.post(self.url, json=payload, timeout=60)
                resp.raise_for_status()
                msg = resp.json().get("message", {})
            except Exception as e:
                logger.warning(f"Copilot tool-calling chyba ({e}) — fallback na stream")
                return None

            tool_calls = msg.get("tool_calls", [])
            content    = (msg.get("content") or "").strip()

            if not tool_calls:
                if content:
                    self._finalize_copilot_turn(user_text, content)
                    return content
                if last_observation:
                    self._finalize_copilot_turn(user_text, last_observation)
                    return last_observation
                return None

            messages.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                fn   = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}

                try:
                    observation = on_tool_call(name, args)
                except Exception as e:
                    observation = f"Chyba nástroje {name}: {e}"

                if len(observation) > 1200:
                    observation = observation[:1200] + "…[zkráceno]"
                last_observation = observation

                messages.append({"role": "tool", "content": observation})

        if last_observation:
            self._finalize_copilot_turn(user_text, last_observation)
            return last_observation
        return None

    def stream_ask_with_tools(
        self,
        user_text: str,
        tools_schema: list,
        on_tool_call: Callable[[str, dict], str],
    ) -> Optional[str]:
        """Alias pro try_copilot_tools — Copilot tool loop bez streamingu."""
        return self.try_copilot_tools(user_text, tools_schema, on_tool_call)

    def _finalize_copilot_turn(self, user_text: str, response: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": response})
        try:
            self.memory.store_conversation(user_text, response, importance=0.6)
        except Exception as _me:
            logger.warning(f"Memory store chyba (ignorováno): {_me}")

    # ── STREAM ASK ───────────────────────────────────

    def stream_ask(self, user_text: str):
        if not getattr(self, '_ollama_available', True):
            yield "Ollama není dostupná. Řekni mi lokální příkaz (otevři, nastav, screenshot...)."
            return
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

        # Rate limiting — pouze pro LLM volání (local router prošel výše)
        _rate_limiter.wait_if_needed()

        self.history.append({"role": "user", "content": user_text})
        self._stream_resp = None
        messages, routed_model, temperature, max_tokens = self._build_messages(user_text)

        # ── Cloud streaming (Groq / OpenRouter) ──────────────────────────────
        task = self._llm_router.detect_task(user_text)
        task_str = task.value if hasattr(task, "value") else str(task)
        if self._cloud.should_use_cloud(task_str):
            full_response = ""
            try:
                for chunk in self._cloud.call_streaming(
                    messages, task_type=task_str,
                    temperature=temperature, max_tokens=max_tokens,
                ):
                    full_response += chunk
                    yield chunk
                if full_response.strip():
                    self.history.append({"role": "assistant", "content": full_response.strip()})
                    try:
                        self.memory.store_conversation(user_text, full_response.strip(), importance=0.6)
                    except Exception:
                        pass
                return
            except Exception as _ce:
                logger.warning(f"Cloud streaming selhal ({_ce}), fallback na Ollama")
                # Pokud už jsme něco vyieldovali, nemůžeme začít znovu — logujeme jen

        # ── Ollama streaming fallback ─────────────────────────────────────────
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

    def save_history(self, path: str = None) -> None:
        """Uloží konverzační historii do JSON souboru."""
        try:
            p = _Path(path or _Path.home() / ".jarvis" / "history.json")
            p.parent.mkdir(parents=True, exist_ok=True)
            data = list(self.history)
            p.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.debug(f"Historie uložena: {len(data)} zpráv → {p}")
        except Exception as e:
            logger.warning(f"Uložení historie selhalo: {e}")

    def load_history(self, path: str = None) -> int:
        """Načte historii ze souboru. Vrátí počet načtených zpráv."""
        try:
            p = _Path(path or _Path.home() / ".jarvis" / "history.json")
            if not p.exists():
                return 0
            data = _json.loads(p.read_text(encoding="utf-8"))
            # Validace: každá zpráva musí mít role a content
            valid = [m for m in data if isinstance(m, dict) and "role" in m and "content" in m]
            self.history.extend(valid[-self.history.maxlen:])
            logger.info(f"Historie načtena: {len(valid)} zpráv z {p}")
            return len(valid)
        except Exception as e:
            logger.warning(f"Načtení historie selhalo: {e}")
            return 0

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


def _ollama_base(url: str) -> str:
    return url.replace("/api/chat", "").replace("/api/generate", "").rstrip("/")


def _ollama_installed_models(ollama_url: str) -> list[str]:
    base = _ollama_base(ollama_url)
    try:
        r = requests.get(f"{base}/api/tags", timeout=3)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def _pick_vision_model(preferred: str, ollama_url: str) -> str | None:
    installed = _ollama_installed_models(ollama_url)
    if not installed:
        return None
    candidates = [preferred]
    for name in installed:
        low = name.lower()
        if any(k in low for k in ("llava", "moondream", "bakllava", "minicpm-v", "vision")):
            candidates.append(name)
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if cand in installed:
            return cand
        stem = cand.split(":")[0]
        for name in installed:
            if name == stem or name.startswith(f"{stem}:"):
                return name
    return None


def _describe_via_ocr_llm(image_path: str, prompt: str) -> str:
    """Fallback bez vision modelu — fakta z oken + OCR, bez halucinací."""
    try:
        from vision import (
            _collect_desktop_context,
            _format_factual_screen_report,
            _ocr_snippet,
        )

        ctx = _collect_desktop_context()
        ocr = _ocr_snippet(image_path)
        return _format_factual_screen_report(ctx, ocr, prompt)
    except Exception as e:
        return f"Popis obrazovky selhal: {e}"


def ask_vision(prompt: str, image_path: str, model: str = "llava:7b",
               ollama_url: str = None) -> str:
    """
    Pošle screenshot + otázku do multimodálního modelu (LLaVA).
    Pokud model chybí, použije OCR + textový LLM.
    """
    try:
        from config import CONFIG
        url = ollama_url or CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
        model = model or CONFIG.get("vision_model", "llava:7b")

        picked = _pick_vision_model(model, url)
        if not picked:
            return _describe_via_ocr_llm(image_path, prompt)

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "model": picked,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [img_b64],
            }],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        resp = requests.post(url, json=payload, timeout=90)
        if resp.status_code == 404:
            return _describe_via_ocr_llm(image_path, prompt)
        resp.raise_for_status()
        result = resp.json().get("message", {}).get("content", "Žádná odpověď.")
        try:
            unload_url = url.replace("/api/chat", "/api/generate")
            requests.post(unload_url, json={"model": picked, "keep_alive": 0}, timeout=5)
        except Exception:
            pass
        return result
    except Exception as e:
        err = str(e)
        if "404" in err or "not found" in err.lower():
            return _describe_via_ocr_llm(image_path, prompt)
        return f"Chyba vision modelu: {e}"
