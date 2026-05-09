"""
JARVIS — Background Agents
Autonomní agenti běžící na pozadí — monitorují systém a reagují na podmínky.
"""

from __future__ import annotations
import threading
import time
import logging
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import psutil

from event_bus import EventBus, Event, EventType, get_event_bus

logger = logging.getLogger(__name__)


# ── Základní agent ────────────────────────────────────

class BaseAgent:
    """Základ pro všechny background agenty."""

    name: str = "base_agent"

    def __init__(self, bus: Optional[EventBus] = None, interval: float = 30.0):
        self._bus      = bus or get_event_bus()
        self._interval = interval
        self._running  = False
        self._thread:  Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name=self.name)
        self._thread.start()
        logger.info(f"Agent {self.name} spuštěn (interval {self._interval}s)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self):
        while self._running:
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Agent {self.name} chyba: {e}")
            time.sleep(self._interval)

    def tick(self):
        """Přepište v potomkovi."""
        pass

    def emit(self, event_type: str, data: Any = None):
        self._bus.emit(event_type, data, source=self.name)


# ── System Monitor Agent ──────────────────────────────

class SystemMonitorAgent(BaseAgent):
    """
    Sleduje CPU, RAM, disk, teploty.
    Publikuje alerty přes EventBus při překročení prahů.
    """

    name = "system_monitor"

    def __init__(self, bus=None, interval: float = 20.0,
                 cpu_threshold: float = 85.0,
                 ram_threshold: float = 90.0,
                 disk_threshold: float = 90.0):
        super().__init__(bus, interval)
        self.cpu_thresh  = cpu_threshold
        self.ram_thresh  = ram_threshold
        self.disk_thresh = disk_threshold
        self._last_alert: Dict[str, float] = {}
        self._alert_cooldown = 120.0  # s — minimální pauza mezi alerty

    def tick(self):
        now = time.time()

        # CPU
        cpu = psutil.cpu_percent(interval=1)
        if cpu > self.cpu_thresh and self._can_alert("cpu", now):
            self.emit(EventType.CPU_HIGH, {
                "cpu_percent": cpu, "threshold": self.cpu_thresh,
                "message": f"CPU {cpu:.0f}% — přetížení!",
            })

        # RAM
        ram = psutil.virtual_memory()
        if ram.percent > self.ram_thresh and self._can_alert("ram", now):
            free_mb = ram.available // 1024 // 1024
            self.emit(EventType.RAM_HIGH, {
                "ram_percent": ram.percent, "free_mb": free_mb,
                "message": f"RAM {ram.percent:.0f}% — jen {free_mb} MB volných!",
            })

        # Disk
        try:
            disk = psutil.disk_usage("/")
            if disk.percent > self.disk_thresh and self._can_alert("disk", now):
                free_gb = disk.free // 1024 ** 3
                self.emit(EventType.DISK_LOW, {
                    "disk_percent": disk.percent, "free_gb": free_gb,
                    "message": f"Disk {disk.percent:.0f}% — jen {free_gb} GB volných!",
                })
        except Exception:
            pass

        # Teploty (pokud jsou dostupné)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.current > 85:
                            if self._can_alert(f"temp_{name}", now):
                                self.emit(EventType.TEMP_HIGH, {
                                    "sensor": name, "temp": entry.current,
                                    "message": f"Teplota {name}: {entry.current:.0f}°C!",
                                })
        except Exception:
            pass

        # Publikuj pravidelné info
        self.emit(EventType.AGENT_INFO, {
            "cpu": cpu, "ram": ram.percent,
            "timestamp": now,
        })

    def _can_alert(self, key: str, now: float) -> bool:
        last = self._last_alert.get(key, 0)
        if now - last > self._alert_cooldown:
            self._last_alert[key] = now
            return True
        return False


# ── Process Watcher Agent ─────────────────────────────

class ProcessWatcherAgent(BaseAgent):
    """
    Hlídá konkrétní procesy — upozorní pokud se ukončí nebo spotřebují příliš zdrojů.
    """

    name = "process_watcher"

    def __init__(self, bus=None, interval: float = 15.0,
                 watch: Optional[List[str]] = None):
        super().__init__(bus, interval)
        self.watch = watch or ["ollama"]  # procesy k hlídání
        self._known: Dict[str, bool] = {}

    def tick(self):
        running = {p.info["name"] for p in psutil.process_iter(["name"]) if p.info["name"]}

        for name in self.watch:
            is_running = any(name.lower() in r.lower() for r in running)
            was_running = self._known.get(name, True)

            if was_running and not is_running:
                self.emit(EventType.AGENT_ALERT, {
                    "process": name, "status": "stopped",
                    "message": f"Proces '{name}' se ukončil.",
                })
            elif not was_running and is_running:
                self.emit(EventType.AGENT_INFO, {
                    "process": name, "status": "started",
                    "message": f"Proces '{name}' byl spuštěn.",
                })

            self._known[name] = is_running


# ── Idle Detector Agent ───────────────────────────────

class IdleDetectorAgent(BaseAgent):
    """
    Detekuje nečinnost uživatele.
    Po X minutách bez příkazu přejde JARVIS do úsporného režimu.
    """

    name = "idle_detector"

    def __init__(self, bus=None, idle_timeout: float = 300.0):
        super().__init__(bus, interval=30.0)
        self._idle_timeout   = idle_timeout
        self._last_activity  = time.time()
        self._idle_announced = False

        # Resetuj při každém příkazu
        bus = bus or get_event_bus()
        bus.subscribe(EventType.GUI_COMMAND, self._on_activity)
        bus.subscribe(EventType.LLM_START,   self._on_activity)

    def _on_activity(self, event: Event):
        self._last_activity  = time.time()
        self._idle_announced = False

    def tick(self):
        idle_secs = time.time() - self._last_activity
        if idle_secs > self._idle_timeout and not self._idle_announced:
            self._idle_announced = True
            self.emit(EventType.AGENT_INFO, {
                "idle_minutes": idle_secs / 60,
                "message": f"JARVIS nečinný {idle_secs/60:.0f} minut.",
            })


# ── Agent Manager ─────────────────────────────────────

class AgentManager:
    """Spravuje všechny background agenty."""

    def __init__(self, bus: Optional[EventBus] = None):
        self._bus    = bus or get_event_bus()
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> "AgentManager":
        self._agents[agent.name] = agent
        return self

    def start_all(self):
        for agent in self._agents.values():
            agent.start()
        logger.info(f"AgentManager: spuštěno {len(self._agents)} agentů")

    def stop_all(self):
        for agent in self._agents.values():
            agent.stop()

    def get_status(self) -> Dict[str, Any]:
        return {
            name: {"running": a._running, "interval": a._interval}
            for name, a in self._agents.items()
        }

    @classmethod
    def create_default(cls, bus: Optional[EventBus] = None) -> "AgentManager":
        """Vytvoří výchozí sadu agentů."""
        mgr = cls(bus)
        mgr.register(SystemMonitorAgent(bus))
        mgr.register(ProcessWatcherAgent(bus, watch=["ollama"]))
        mgr.register(IdleDetectorAgent(bus, idle_timeout=600))
        return mgr
