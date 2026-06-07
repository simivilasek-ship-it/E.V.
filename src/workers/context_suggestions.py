"""
Proactive resource suggestions — CPU/RAM threshold alerts readable via API.
Subscribes to EventBus CPU_HIGH / RAM_HIGH from SystemMonitorAgent.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

_suggestions: List[Dict[str, Any]] = []
_lock = threading.Lock()
_MAX_SUGGESTIONS = 20

CPU_THRESHOLD = 85.0
RAM_THRESHOLD = 90.0


def get_suggestions(limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent proactive suggestions (newest first)."""
    n = max(1, min(int(limit or 10), _MAX_SUGGESTIONS))
    with _lock:
        return list(reversed(_suggestions[-n:]))


def _store_suggestion(kind: str, message: str, data: Optional[dict] = None) -> None:
    entry = {
        "kind": kind,
        "message": message,
        "data": data or {},
        "ts": time.time(),
    }
    with _lock:
        _suggestions.append(entry)
        if len(_suggestions) > _MAX_SUGGESTIONS:
            del _suggestions[:-_MAX_SUGGESTIONS]
    try:
        from event_bus import get_event_bus

        get_event_bus().emit("suggestion.created", entry, source="context_suggestions")
    except Exception:
        pass


class ContextSuggestionsWorker:
    """Polls CPU/RAM and mirrors SystemMonitor alerts into suggestion store."""

    def __init__(
        self,
        bus=None,
        interval: float = 25.0,
        cpu_threshold: float = CPU_THRESHOLD,
        ram_threshold: float = RAM_THRESHOLD,
    ):
        from event_bus import get_event_bus, EventType

        self._bus = bus or get_event_bus()
        self._interval = interval
        self._cpu_threshold = cpu_threshold
        self._ram_threshold = ram_threshold
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_poll: Dict[str, float] = {}
        self._cooldown = 120.0
        self._EventType = EventType

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            self._bus.subscribe(self._EventType.CPU_HIGH, self._on_cpu_high)
            self._bus.subscribe(self._EventType.RAM_HIGH, self._on_ram_high)
        except Exception as e:
            logger.debug(f"ContextSuggestions subscribe failed: {e}")
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="ContextSuggestions"
        )
        self._thread.start()
        logger.info("ContextSuggestionsWorker started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _can_emit(self, key: str) -> bool:
        now = time.time()
        if now - self._last_poll.get(key, 0) < self._cooldown:
            return False
        self._last_poll[key] = now
        return True

    def _on_cpu_high(self, event) -> None:
        data = event.data or {}
        msg = data.get("message") or f"CPU {data.get('cpu_percent', '?')}% — vysoké zatížení"
        _store_suggestion("cpu_high", msg, data)

    def _on_ram_high(self, event) -> None:
        data = event.data or {}
        msg = data.get("message") or f"RAM {data.get('ram_percent', '?')}% — málo volné paměti"
        _store_suggestion("ram_high", msg, data)

    def _poll_loop(self) -> None:
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                if cpu > self._cpu_threshold and self._can_emit("cpu_poll"):
                    _store_suggestion(
                        "cpu_high",
                        f"CPU {cpu:.0f}% — zvaž ukončení náročných procesů (příkaz: top procesy).",
                        {"cpu_percent": cpu, "threshold": self._cpu_threshold},
                    )
                ram = psutil.virtual_memory()
                if ram.percent > self._ram_threshold and self._can_emit("ram_poll"):
                    free_mb = ram.available // 1024 // 1024
                    _store_suggestion(
                        "ram_high",
                        f"RAM {ram.percent:.0f}% — zbývá {free_mb} MB (příkaz: top procesy).",
                        {"ram_percent": ram.percent, "free_mb": free_mb, "threshold": self._ram_threshold},
                    )
            except Exception as e:
                logger.debug(f"ContextSuggestions poll: {e}")
            time.sleep(self._interval)


_worker: Optional[ContextSuggestionsWorker] = None


def start_context_suggestions(bus=None) -> ContextSuggestionsWorker:
    global _worker
    if _worker is None:
        _worker = ContextSuggestionsWorker(bus=bus)
        _worker.start()
    return _worker


def stop_context_suggestions() -> None:
    global _worker
    if _worker is not None:
        _worker.stop()
        _worker = None
