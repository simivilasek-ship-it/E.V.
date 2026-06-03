"""
JARVIS — Cloud Router (Groq + OpenRouter)
Hybridní přepínač: jednoduché dotazy → Ollama (lokálně),
komplexní/kódovací/reasoning → Groq nebo OpenRouter (500+ tok/s).

Konfigurace v .env nebo config.json:
  GROQ_API_KEY=gsk_...
  OPENROUTER_API_KEY=sk-or-...
  CLOUD_ROUTING_ENABLED=true
  CLOUD_ROUTING_THRESHOLD=complex   # simple|complex|always
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# ── Dostupné cloud modely ─────────────────────────────────────────────────────

GROQ_MODELS = {
    "fast":      "llama-3.1-8b-instant",      # ~500 tok/s, skvělé pro chat/překlad
    "smart":     "llama-3.3-70b-versatile",   # 70B, reasoning/kód
    "code":      "llama-3.1-70b-versatile",   # kód + tooling
    "vision":    "llama-3.2-90b-vision-preview",  # multimodal (preview)
}

OPENROUTER_MODELS = {
    "fast":      "meta-llama/llama-3.1-8b-instruct:free",
    "smart":     "meta-llama/llama-3.3-70b-instruct",
    "code":      "qwen/qwen-2.5-coder-32b-instruct",
    "vision":    "qwen/qwen2.5-vl-72b-instruct",
    "reasoning": "deepseek/deepseek-r1",
}


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class CloudResponse:
    content: str
    provider: str           # "groq" | "openrouter" | "ollama"
    model: str
    latency_ms: float
    tokens_used: int = 0
    cached: bool = False


@dataclass
class CloudStats:
    calls: int = 0
    errors: int = 0
    total_ms: float = 0.0
    tokens: int = 0
    provider_calls: dict = field(default_factory=dict)

    def record(self, provider: str, ms: float, tokens: int = 0):
        self.calls += 1
        self.total_ms += ms
        self.tokens += tokens
        self.provider_calls[provider] = self.provider_calls.get(provider, 0) + 1

    def avg_latency(self) -> float:
        return self.total_ms / self.calls if self.calls else 0.0


# ── Hlavní CloudRouter ────────────────────────────────────────────────────────

class CloudRouter:
    """
    Inteligentní hybridní router: lokální Ollama ↔ Groq ↔ OpenRouter.

    Routing strategie (CLOUD_ROUTING_THRESHOLD):
      'simple'  — cloud jen pro rychlé odpovědi (překlad, krátké dotazy)
      'complex' — cloud pro kód, reasoning, agenty (výchozí)
      'always'  — vždy cloud (Ollama = fallback)

    Priorita providerů: Groq (nejrychlejší) → OpenRouter → Ollama (fallback)
    """

    COMPLEX_TASK_TYPES = {"code", "reasoning", "math", "agent", "vision"}
    SIMPLE_TASK_TYPES  = {"fast", "translate", "command"}

    def __init__(self, config: dict):
        self.config  = config
        self._stats  = CloudStats()
        self._groq_key       = config.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
        self._openrouter_key = config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
        self._enabled        = self._resolve_enabled(config)
        self._threshold      = config.get("cloud_routing_threshold", "complex").lower()

        if self._enabled:
            providers = []
            if self._groq_key:
                providers.append("Groq")
            if self._openrouter_key:
                providers.append("OpenRouter")
            if providers:
                logger.info(f"CloudRouter aktivní — providery: {', '.join(providers)}, threshold={self._threshold}")
            else:
                logger.warning("CloudRouter: žádný API klíč nenalezen (GROQ_API_KEY / OPENROUTER_API_KEY)")
                self._enabled = False
        else:
            logger.info("CloudRouter: vypnutý (CLOUD_ROUTING_ENABLED=false)")

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def should_use_cloud(self, task_type: str) -> bool:
        """Rozhodne, zda má jít dotaz do cloudu."""
        if not self._enabled:
            return False
        if self._threshold == "always":
            return True
        if self._threshold == "complex":
            return task_type in self.COMPLEX_TASK_TYPES
        if self._threshold == "simple":
            return task_type in self.SIMPLE_TASK_TYPES
        return False

    def call(
        self,
        messages: list[dict],
        task_type: str = "standard",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> CloudResponse:
        """
        Zavolá cloud provider (Groq → OpenRouter → fallback error).
        Při selhání Groq automaticky zkusí OpenRouter.
        """
        t0 = time.monotonic()

        # 1) Groq (nejrychlejší — LLaMA3 500+ tok/s)
        if self._groq_key:
            try:
                result = self._call_groq(messages, task_type, temperature, max_tokens, stream)
                ms = (time.monotonic() - t0) * 1000
                self._stats.record("groq", ms, result.tokens_used)
                result.latency_ms = ms
                return result
            except Exception as e:
                logger.warning(f"Groq selhal ({e}), zkouším OpenRouter...")

        # 2) OpenRouter (záloha — více modelů)
        if self._openrouter_key:
            try:
                result = self._call_openrouter(messages, task_type, temperature, max_tokens, stream)
                ms = (time.monotonic() - t0) * 1000
                self._stats.record("openrouter", ms, result.tokens_used)
                result.latency_ms = ms
                return result
            except Exception as e:
                logger.error(f"OpenRouter selhal ({e})")

        raise RuntimeError("Všechny cloud providery selhaly")

    def call_streaming(self, messages: list[dict], task_type: str = "standard",
                       temperature: float = 0.7, max_tokens: int = 1000):
        """Generator yielding text chunks ze streaming cloud API."""
        if self._groq_key:
            try:
                yield from self._stream_groq(messages, task_type, temperature, max_tokens)
                return
            except Exception as e:
                logger.warning(f"Groq streaming selhal ({e}), zkouším OpenRouter...")
        if self._openrouter_key:
            try:
                yield from self._stream_openrouter(messages, task_type, temperature, max_tokens)
                return
            except Exception as e:
                logger.error(f"OpenRouter streaming selhal ({e})")
        raise RuntimeError("Všechny cloud streaming providery selhaly")

    def stats(self) -> dict:
        return {
            "enabled": self._enabled,
            "threshold": self._threshold,
            "total_calls": self._stats.calls,
            "total_errors": self._stats.errors,
            "avg_latency_ms": round(self._stats.avg_latency(), 1),
            "total_tokens": self._stats.tokens,
            "provider_calls": self._stats.provider_calls,
            "groq_available": bool(self._groq_key),
            "openrouter_available": bool(self._openrouter_key),
        }

    # ── Groq API ──────────────────────────────────────────────────────────────

    def _groq_model(self, task_type: str) -> str:
        mapping = {
            "code":      GROQ_MODELS["code"],
            "reasoning": GROQ_MODELS["smart"],
            "math":      GROQ_MODELS["smart"],
            "agent":     GROQ_MODELS["smart"],
            "vision":    GROQ_MODELS["vision"],
            "fast":      GROQ_MODELS["fast"],
        }
        return mapping.get(task_type, GROQ_MODELS["fast"])

    def _call_groq(self, messages: list[dict], task_type: str,
                   temperature: float, max_tokens: int, stream: bool) -> CloudResponse:
        model = self._groq_model(task_type)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._groq_key}",
            "Content-Type":  "application/json",
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload, headers=headers, timeout=30,
        )
        resp.raise_for_status()
        data    = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        tokens  = data.get("usage", {}).get("total_tokens", 0)
        return CloudResponse(content=content, provider="groq", model=model,
                             latency_ms=0.0, tokens_used=tokens)

    def _stream_groq(self, messages: list[dict], task_type: str,
                     temperature: float, max_tokens: int):
        import json as _json
        model = self._groq_model(task_type)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._groq_key}",
            "Content-Type":  "application/json",
        }
        with requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload, headers=headers, stream=True, timeout=30,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8")
                if text.startswith("data: "):
                    text = text[6:]
                if text.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(text)["choices"][0]["delta"].get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue

    # ── OpenRouter API ────────────────────────────────────────────────────────

    def _openrouter_model(self, task_type: str) -> str:
        mapping = {
            "code":      OPENROUTER_MODELS["code"],
            "reasoning": OPENROUTER_MODELS["reasoning"],
            "math":      OPENROUTER_MODELS["reasoning"],
            "agent":     OPENROUTER_MODELS["smart"],
            "vision":    OPENROUTER_MODELS["vision"],
            "fast":      OPENROUTER_MODELS["fast"],
        }
        return mapping.get(task_type, OPENROUTER_MODELS["fast"])

    def _call_openrouter(self, messages: list[dict], task_type: str,
                         temperature: float, max_tokens: int, stream: bool) -> CloudResponse:
        model = self._openrouter_model(task_type)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/jarvis-ai",
            "X-Title":       "JARVIS",
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload, headers=headers, timeout=45,
        )
        resp.raise_for_status()
        data    = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        tokens  = data.get("usage", {}).get("total_tokens", 0)
        return CloudResponse(content=content, provider="openrouter", model=model,
                             latency_ms=0.0, tokens_used=tokens)

    def _stream_openrouter(self, messages: list[dict], task_type: str,
                           temperature: float, max_tokens: int):
        import json as _json
        model = self._openrouter_model(task_type)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/jarvis-ai",
            "X-Title":       "JARVIS",
        }
        with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload, headers=headers, stream=True, timeout=45,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8")
                if text.startswith("data: "):
                    text = text[6:]
                if text.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(text)["choices"][0]["delta"].get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_enabled(config: dict) -> bool:
        env_val = os.getenv("CLOUD_ROUTING_ENABLED", "").lower()
        if env_val in ("true", "1", "yes"):
            return True
        if env_val in ("false", "0", "no"):
            return False
        return bool(config.get("cloud_routing_enabled", True))


# Singleton
_cloud_router: Optional[CloudRouter] = None

def get_cloud_router(config: dict = None) -> CloudRouter:
    global _cloud_router
    if _cloud_router is None:
        if config is None:
            from config import CONFIG
            config = CONFIG
        _cloud_router = CloudRouter(config)
    return _cloud_router
