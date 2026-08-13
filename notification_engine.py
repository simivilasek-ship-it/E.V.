"""
E.V. Smart Notifications
- CPU/RAM/Disk alarmy
- Připomínky (scheduled)
- Systémové události
- Desktop notifikace přes libnotify
"""
from __future__ import annotations
import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    title: str
    body: str
    icon: str = "dialog-information"  # dialog-warning, dialog-error, system-run
    urgent: bool = False


def send_desktop_notification(n: Notification) -> bool:
    """Pošle desktop notifikaci přes libnotify (notify-send)."""
    try:
        cmd = ["notify-send", n.title, n.body, "-i", n.icon]
        if n.urgent:
            cmd += ["-u", "critical"]
        subprocess.run(cmd, capture_output=True, timeout=3)
        return True
    except Exception as e:
        logger.debug(f"notify-send selhal: {e}")
        return False


class CPUMonitor:
    """Monitoruje CPU/RAM a posílá notifikace při překročení threshold."""

    def __init__(self,
                 cpu_threshold: float = 90.0,
                 ram_threshold: float = 90.0,
                 cooldown: int = 300):
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.cooldown = cooldown
        self._last_cpu_alert = 0.0
        self._last_ram_alert = 0.0
        self._callback: Optional[Callable[[str], None]] = None

    def set_callback(self, cb: Callable[[str], None]) -> None:
        self._callback = cb

    def check(self) -> list[Notification]:
        import psutil
        now = time.time()
        alerts = []

        cpu = psutil.cpu_percent(interval=0.1)
        if cpu >= self.cpu_threshold and now - self._last_cpu_alert > self.cooldown:
            self._last_cpu_alert = now
            n = Notification(
                title="⚠️ Vysoké vytížení CPU",
                body=f"CPU je na {cpu:.0f}% — zkontroluj spuštěné procesy",
                icon="dialog-warning", urgent=True
            )
            alerts.append(n)
            if self._callback:
                self._callback(f"Varování: CPU je na {cpu:.0f}%")

        ram = psutil.virtual_memory().percent
        if ram >= self.ram_threshold and now - self._last_ram_alert > self.cooldown:
            self._last_ram_alert = now
            n = Notification(
                title="⚠️ Vysoké vytížení RAM",
                body=f"RAM je na {ram:.0f}% — zvažte restart aplikací",
                icon="dialog-warning", urgent=True
            )
            alerts.append(n)

        return alerts


class NotificationEngine:
    """Koordinuje všechny zdroje notifikací."""

    def __init__(self, config: dict = None):
        cfg = config or {}
        self.cpu_monitor = CPUMonitor(
            cpu_threshold=cfg.get("notification_cpu_threshold", 90),
            ram_threshold=cfg.get("notification_ram_threshold", 90),
        )
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ws_callback: Optional[Callable[[str, str], None]] = None

    def set_ws_callback(self, cb: Callable[[str, str], None]) -> None:
        """Callback pro odesílání notifikací přes WebSocket do UI."""
        self._ws_callback = cb
        self.cpu_monitor.set_callback(lambda msg: self._notify_ui("warning", msg))

    def _notify_ui(self, level: str, message: str) -> None:
        if self._ws_callback:
            try:
                self._ws_callback(level, message)
            except Exception:
                pass

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="notification-engine")
        self._thread.start()
        logger.info("NotificationEngine spuštěn")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                alerts = self.cpu_monitor.check()
                for alert in alerts:
                    send_desktop_notification(alert)
                    self._notify_ui("warning", f"{alert.title}: {alert.body}")
            except Exception as e:
                logger.debug(f"NotificationEngine loop chyba: {e}")
            time.sleep(30)  # Kontrola každých 30s

    def send(self, title: str, body: str, urgent: bool = False) -> bool:
        """Manuální odeslání notifikace."""
        return send_desktop_notification(Notification(title=title, body=body, urgent=urgent))


_engine: Optional[NotificationEngine] = None

def get_notification_engine(config: dict = None) -> NotificationEngine:
    global _engine
    if _engine is None:
        _engine = NotificationEngine(config)
    return _engine
