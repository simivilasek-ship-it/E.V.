"""
JARVIS — LLM Router 2.0
Inteligentní routing požadavků na různé modely podle úkolu.
Fallback při selhání, token-budget management, task-specific modely.
"""

from __future__ import annotations
import logging
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import requests

logger = logging.getLogger(__name__)


class TaskType(Enum):
    CHAT        = "chat"        # obecná konverzace
    CODE        = "code"        # psaní kódu
    TRANSLATE   = "translate"   # překlad
    SUMMARIZE   = "summarize"   # shrnutí
    MATH        = "math"        # matematika
    CREATIVE    = "creative"    # kreativní psaní
    COMMAND     = "command"     # systémový příkaz (rychlé)
    # --- v2 typy ---
    FAST        = "fast"        # Qwen 1.5B nebo nejmenší dostupný
    STANDARD    = "standard"    # Qwen 3B (default)
    REASONING   = "reasoning"   # Llama 8B nebo Qwen 7B
    VISION      = "vision"      # LLaVA
    AGENT       = "agent"       # Llama 8B pro multi-step


@dataclass
class ModelConfig:
    name:         str
    max_tokens:   int    = 2000
    temperature:  float  = 0.2
    timeout:      int    = 60
    priority:     int    = 0     # vyšší = preferovaný


@dataclass
class RoutingRule:
    task_type:   TaskType
    patterns:    List[str]       # regex patterny pro detekci
    model_names: List[str]       # preferované modely (v pořadí)
    temperature: float = 0.2
    max_tokens:  int   = 1000


class LLMRouter:
    """
    Router pro LLM požadavky.
    - Detekuje typ úkolu z textu
    - Vybere nejvhodnější model
    - Při selhání zkusí fallback model
    - Sleduje statistiky a latenci
    """

    # aliases pro zpětnou kompatibilitu s kódem volajícím router.url / router.default_model
    @property
    def url(self) -> str:
        return self._url

    @property
    def default_model(self) -> str:
        return self._default

    def __init__(self, ollama_url: str, default_model: str):
        self._url     = ollama_url
        self._default = default_model
        self._models: Dict[str, ModelConfig]  = {}
        self._rules:  List[RoutingRule]       = []
        self._stats:  Dict[str, Dict]         = {}
        self._available_cache: Optional[List[str]] = None
        self._cache_ts: float = 0

        # v2 — cache pro _get_available_models()
        self._models_cache: set = set()
        self._models_cache_ts: float = 0.0

        self._setup_default_rules()

    # ── Konfigurace ───────────────────────────────────

    def register_model(self, config: ModelConfig):
        self._models[config.name] = config
        self._stats[config.name]  = {
            "calls": 0, "errors": 0, "total_ms": 0.0, "tokens": 0}

    def add_rule(self, rule: RoutingRule):
        self._rules.append(rule)

    def _setup_default_rules(self):
        """Výchozí pravidla pro routing."""
        self._rules = [
            RoutingRule(
                task_type=TaskType.CODE,
                patterns=[r"\b(napiš|write|kód|code|python|javascript|funkci|function|class|třídu)\b"],
                model_names=["qwen2.5-coder:1.5b-base", "deepseek-coder:latest",
                             "qwen2.5:3b"],
                temperature=0.1, max_tokens=2000,
            ),
            RoutingRule(
                task_type=TaskType.MATH,
                patterns=[r"\b(vypočítej|calculate|kolik je|matematika|\d+\s*[\+\-\*\/]\s*\d+)\b"],
                model_names=["qwen2.5:3b", "llama3.1:8b"],
                temperature=0.0, max_tokens=500,
            ),
            RoutingRule(
                task_type=TaskType.TRANSLATE,
                patterns=[r"\b(přelož|translate|přeložit|in english|do češtiny)\b"],
                model_names=["qwen2.5:3b", "llama3.1:8b"],
                temperature=0.1, max_tokens=800,
            ),
            RoutingRule(
                task_type=TaskType.COMMAND,
                patterns=[r"\b(otevři|spusť|zavři|stáhni|pust|hlasitost)\b"],
                model_names=["qwen2.5:3b"],
                temperature=0.0, max_tokens=200,
            ),
        ]

    # ── Routing ───────────────────────────────────────

    def detect_task(self, text: str) -> TaskType:
        """Detekuje typ úkolu z textu (v2 — rozšířená detekce)."""
        t = text.lower()

        # Vision — obrázky, screenshoty, kamera
        if any(w in t for w in ["obrazovk", "screenshot", "kamera", "webcam",
                                 "vidís", "co vidíš"]):
            return TaskType.VISION

        # Kód — programování
        if any(w in t for w in ["kód", "funkci", "class", "python", "javascript",
                                 "def ", "import", "napiš kód", "oprav bug"]):
            return TaskType.CODE

        # Math — výpočty, vzorce
        if any(w in t for w in ["vypočítej", "integral", "derivace", "matici",
                                 "rovnici", "pravděpodobnost"]):
            return TaskType.MATH

        # Reasoning — analýza, plánování, porovnání
        if any(w in t for w in ["analyzuj", "porovnej", "vysvětli proč",
                                 "jaký je rozdíl", "plánuj", "strategii",
                                 "výhody nevýhody"]):
            return TaskType.REASONING

        # Agent — multi-step úkoly
        if any(w in t for w in ["najdi a ulož", "zkontroluj a",
                                 "vyhledej a", "stáhni a"]):
            return TaskType.AGENT

        # Rychlá odpověď — krátká fráze, překlad, čas, počasí
        if len(text) < 50 and any(w in t for w in ["přelož", "přepiš",
                                                     "kolik je", "jaké je"]):
            return TaskType.FAST

        # Starý routing přes RoutingRule patterny (zpětná kompatibilita)
        for rule in self._rules:
            for pattern in rule.patterns:
                if re.search(pattern, t, re.IGNORECASE):
                    return rule.task_type

        return TaskType.STANDARD

    def get_model_for_task(self, task: TaskType) -> Tuple[str, float, int]:
        """Vrátí (model, temperature, max_tokens) pro daný úkol (v2)."""
        available = self._get_available_models()

        model_prefs: Dict = {
            TaskType.FAST:      (["qwen2.5:1.5b", "phi3:mini", self._default], 0.3, 300),
            TaskType.STANDARD:  ([self._default], 0.7, 800),
            TaskType.CODE:      (["deepseek-coder:latest", "qwen2.5:7b", self._default], 0.1, 1500),
            TaskType.MATH:      (["qwen2.5:7b", self._default], 0.1, 600),
            TaskType.REASONING: (["llama3.1:8b", "qwen2.5:7b", self._default], 0.5, 1200),
            TaskType.VISION:    (["llava:7b", self._default], 0.7, 800),
            TaskType.AGENT:     (["llama3.1:8b", "qwen2.5:7b", self._default], 0.3, 1000),
        }

        if task in model_prefs:
            candidates, temp, max_tok = model_prefs[task]
            for m in candidates:
                if m in available or m == self._default:
                    return m, temp, max_tok
            return self._default, 0.7, 800

        # Zpětná kompatibilita — starý routing přes RoutingRule
        for rule in self._rules:
            if rule.task_type == task:
                for model_name in rule.model_names:
                    if model_name in available or not available:
                        return model_name, rule.temperature, rule.max_tokens

        return self._default, 0.2, 1000

    def route(self, text: str, system_prompt: str,
              history: list) -> Tuple[str, dict]:
        """
        Vrátí (raw_response, metadata) pro daný text.
        Automaticky vybere model, zkusí fallback při selhání.
        """
        task       = self.detect_task(text)
        model, temp, max_tok = self.get_model_for_task(task)

        models_to_try = [model, self._default]
        # Odstraň duplicity ale zachovej pořadí
        seen = set()
        models_to_try = [m for m in models_to_try
                         if not (m in seen or seen.add(m))]

        for attempt_model in models_to_try:
            try:
                result, ms = self._call(
                    attempt_model, system_prompt, history,
                    text, temp, max_tok)
                self._record_success(attempt_model, ms)
                return result, {
                    "model": attempt_model, "task": task.value,
                    "latency_ms": ms, "fallback": attempt_model != model,
                }
            except Exception as e:
                self._record_error(attempt_model)
                logger.warning(f"Router: {attempt_model} selhal ({e}), zkouším fallback")

        raise RuntimeError(f"Všechny modely selhaly pro: {text[:50]}")

    # ── HTTP volání ───────────────────────────────────

    def _call(self, model: str, system: str, history: list,
              user_text: str, temperature: float, max_tokens: int) -> Tuple[str, float]:
        """Zavolá Ollama API a vrátí (content, latency_ms)."""
        messages = [{"role": "system", "content": system}] + list(history)
        messages.append({"role": "user", "content": user_text})

        payload = {
            "model":   model,
            "messages": messages,
            "stream":  False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        t0   = time.time()
        resp = requests.post(self._url, json=payload, timeout=60)
        resp.raise_for_status()
        ms   = (time.time() - t0) * 1000

        content = resp.json().get("message", {}).get("content", "")
        return content, ms

    # ── Statistiky ────────────────────────────────────

    def _record_success(self, model: str, ms: float):
        if model not in self._stats:
            self._stats[model] = {"calls":0,"errors":0,"total_ms":0.0,"tokens":0}
        s = self._stats[model]
        s["calls"]    += 1
        s["total_ms"] += ms

    def _record_error(self, model: str):
        if model not in self._stats:
            self._stats[model] = {"calls":0,"errors":0,"total_ms":0.0,"tokens":0}
        self._stats[model]["errors"] += 1

    def get_stats(self) -> Dict:
        result = {}
        for model, s in self._stats.items():
            avg_ms = s["total_ms"] / s["calls"] if s["calls"] else 0
            result[model] = {**s, "avg_latency_ms": round(avg_ms, 1)}
        return result

    def _get_available_models(self) -> set:
        """Vrátí set dostupných modelů z Ollama (cachováno na 60s, timeout 2s)."""
        now = time.time()
        # v2 cache (set-based)
        if now - self._models_cache_ts < 60 and self._models_cache:
            return self._models_cache
        # starý list-based cache (zpětná kompatibilita)
        if now - self._cache_ts < 60 and self._available_cache is not None:
            return set(self._available_cache)
        try:
            r = requests.get(
                self._url.replace("/api/chat", "/api/tags"), timeout=2)
            if r.status_code == 200:
                models = {m["name"] for m in r.json().get("models", [])}
                self._models_cache = models
                self._models_cache_ts = now
                # zachovej i starý cache
                self._available_cache = list(models)
                self._cache_ts = now
                return models
        except Exception:
            pass
        return {self._default}
