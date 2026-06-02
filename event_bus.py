"""
JARVIS — Event Bus / Message Bus
Centrální pub/sub systém. Všechny moduly komunikují přes eventy.

Použití:
    bus = get_event_bus()
    bus.subscribe("llm.response", handler)
    bus.publish(Event("gui.command", data={"text": "otevri chrome"}))
"""

from __future__ import annotations
import threading
import queue
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Typy eventů ──────────────────────────────────────

class EventType:
    # GUI
    GUI_COMMAND       = "gui.command"        # uživatel zadal příkaz
    GUI_STATE_CHANGE  = "gui.state_change"   # změna stavu orbu
    GUI_MESSAGE       = "gui.message"        # zobrazit zprávu

    # LLM
    LLM_START         = "llm.start"          # LLM začal zpracovávat
    LLM_CHUNK         = "llm.chunk"          # chunk streamované odpovědi
    LLM_DONE          = "llm.done"           # LLM dokončil
    LLM_ERROR         = "llm.error"          # chyba LLM

    # Commands
    CMD_EXECUTE       = "cmd.execute"        # příkaz se vykonává
    CMD_DONE          = "cmd.done"           # příkaz dokončen
    CMD_ERROR         = "cmd.error"          # chyba příkazu

    # Agents (background)
    AGENT_ALERT       = "agent.alert"        # agent detekoval problém
    AGENT_INFO        = "agent.info"         # agent info zpráva
    CPU_HIGH          = "agent.cpu_high"     # CPU > threshold
    RAM_HIGH          = "agent.ram_high"     # RAM > threshold
    DISK_LOW          = "agent.disk_low"     # disk < threshold
    TEMP_HIGH         = "agent.temp_high"    # teplota > threshold

    # Memory
    MEMORY_STORED     = "memory.stored"      # vzpomínka uložena
    MEMORY_RECALLED   = "memory.recalled"    # vzpomínka vybavena
    CONTEXT_CHANGED   = "memory.context"     # kontext se změnil

    # Scheduler
    TASK_SCHEDULED    = "scheduler.task"     # úkol naplánován
    TASK_FIRED        = "scheduler.fired"    # úkol se spustil

    # System
    JARVIS_READY      = "system.ready"       # JARVIS připraven
    JARVIS_SHUTDOWN   = "system.shutdown"    # JARVIS se ukončuje

    # Active window
    ACTIVE_WINDOW_CHANGED = "active_window.changed"  # aktivní okno se změnilo

    # Wildcard
    ALL               = "*"                  # přihlásit se ke všem


@dataclass
class Event:
    """Jedna událost v systému."""
    type:      str
    data:      Any    = None
    source:    str    = ""
    timestamp: float  = field(default_factory=time.time)

    def __repr__(self):
        return f"Event({self.type!r}, source={self.source!r})"


# ── Event Bus ─────────────────────────────────────────

class EventBus:
    """
    Centrální pub/sub message bus.
    Thread-safe, asynchronní zpracování v background threadu.
    """

    def __init__(self, workers: int = 2):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock        = threading.RLock()
        self._queue       = queue.Queue(maxsize=1000)
        self._running     = True
        self._history:    List[Event] = []
        self._max_history = 500

        # Worker thready pro zpracování eventů
        self._workers = [
            threading.Thread(target=self._process, daemon=True, name=f"EventBus-{i}")
            for i in range(workers)
        ]
        for w in self._workers:
            w.start()

        logger.debug(f"EventBus spuštěn ({workers} workers)")

    # ── Subscriber API ────────────────────────────────

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> Callable:
        """
        Přihlásí callback k danému typu eventu.
        event_type může být konkrétní ("gui.command") nebo "*" (vše).
        Vrátí funkci pro odhlášení.
        """
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

        def unsubscribe():
            self.unsubscribe(event_type, callback)

        return unsubscribe

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass

    # ── Publisher API ─────────────────────────────────

    def publish(self, event: Event) -> None:
        """Publikuje event — přidá do fronty ke zpracování."""
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning(f"EventBus fronta plná, zahazuji: {event}")

    def emit(self, event_type: str, data: Any = None, source: str = "") -> None:
        """Zkrácený zápis pro publish."""
        self.publish(Event(type=event_type, data=data, source=source))

    # ── Zpracování ────────────────────────────────────

    def _process(self):
        while self._running:
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # Ulož do historie
            with self._lock:
                self._history.append(event)
                if len(self._history) > self._max_history:
                    self._history.pop(0)

                # Získej callbacky pro konkrétní typ + wildcard
                callbacks = (
                    list(self._subscribers.get(event.type, [])) +
                    list(self._subscribers.get(EventType.ALL, []))
                )

            # Zavolej callbacky mimo zámek — každý v separátním daemon vlákně
            # s timeoutem 5 s, aby pomalý callback nezablokoval event loop.
            for cb in callbacks:
                t = threading.Thread(
                    target=self._safe_call, args=(cb, event), daemon=True)
                t.start()
                t.join(timeout=5.0)
                if t.is_alive():
                    logger.warning(
                        f"EventBus callback timeout (>5s): {getattr(cb, '__name__', cb)}"
                    )

    # ── Historie ──────────────────────────────────────

    def get_history(self, event_type: Optional[str] = None,
                    limit: int = 50) -> List[Event]:
        """Vrátí historii eventů (volitelně filtrovanou)."""
        with self._lock:
            history = self._history[-limit:]
        if event_type:
            history = [e for e in history if e.type == event_type]
        return history

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            counts: Dict[str, int] = {}
            for e in self._history:
                counts[e.type] = counts.get(e.type, 0) + 1
        return {
            "queue_size":   self._queue.qsize(),
            "history_size": len(self._history),
            "event_counts": counts,
            "subscribers":  {k: len(v) for k, v in self._subscribers.items()},
        }

    @staticmethod
    def _safe_call(cb: Callable, event: "Event") -> None:
        try:
            cb(event)
        except Exception as e:
            logger.error(f"EventBus callback chyba ({event.type}): {e}")

    def stop(self, timeout: float = 2.0):
        self._running = False
        for w in self._workers:
            w.join(timeout=timeout)
        logger.debug("EventBus zastaven")


# ── Singleton ─────────────────────────────────────────

_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
    return _bus


def shutdown_event_bus():
    global _bus
    with _bus_lock:
        if _bus:
            _bus.stop()
            _bus = None
