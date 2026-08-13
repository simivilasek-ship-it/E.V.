"""
Testy pro E.V. Smart Notifications (notification_engine.py)
"""
from __future__ import annotations
import time
from unittest.mock import patch, MagicMock

import pytest

from notification_engine import (
    CPUMonitor,
    Notification,
    NotificationEngine,
    send_desktop_notification,
)


# ── Pomocné mocky ────────────────────────────────────────────────────────────

def _mock_psutil(cpu: float, ram: float):
    """Vrátí patch context pro psutil.cpu_percent a virtual_memory."""
    vm = MagicMock()
    vm.percent = ram
    cpu_patch = patch("psutil.cpu_percent", return_value=cpu)
    ram_patch  = patch("psutil.virtual_memory", return_value=vm)
    return cpu_patch, ram_patch


# ── Testy ────────────────────────────────────────────────────────────────────

class TestCPUMonitorBelowThreshold:
    """CPU 50 %, threshold 90 → žádné alerty."""

    def test_cpu_monitor_below_threshold(self):
        monitor = CPUMonitor(cpu_threshold=90.0, ram_threshold=90.0, cooldown=300)
        cpu_patch, ram_patch = _mock_psutil(cpu=50.0, ram=50.0)
        with cpu_patch, ram_patch:
            alerts = monitor.check()
        assert alerts == [], f"Očekávány 0 alerty, dostáno: {alerts}"


class TestCPUMonitorAboveThreshold:
    """CPU 95 %, threshold 90 → přesně 1 CPU alert."""

    def test_cpu_monitor_above_threshold(self):
        monitor = CPUMonitor(cpu_threshold=90.0, ram_threshold=95.0, cooldown=300)
        # RAM pod prahem (80 %), CPU nad prahem (95 %)
        cpu_patch, ram_patch = _mock_psutil(cpu=95.0, ram=80.0)
        with cpu_patch, ram_patch:
            alerts = monitor.check()
        assert len(alerts) == 1, f"Očekáván 1 alert, dostáno: {len(alerts)}"
        assert "CPU" in alerts[0].title


class TestCooldownPreventsSpam:
    """Dvě rychlá volání → jen 1 alert díky cooldownu."""

    def test_cooldown_prevents_spam(self):
        monitor = CPUMonitor(cpu_threshold=90.0, ram_threshold=95.0, cooldown=300)
        cpu_patch, ram_patch = _mock_psutil(cpu=95.0, ram=80.0)
        with cpu_patch, ram_patch:
            first  = monitor.check()
            second = monitor.check()

        assert len(first)  == 1, "První volání musí vrátit alert"
        assert len(second) == 0, "Druhé volání v cooldown okně musí vrátit 0 alertů"


class TestSendNotificationNoCrash:
    """notify-send není k dispozici → graceful fallback (žádná výjimka)."""

    def test_send_notification_no_crash(self):
        n = Notification(
            title="Test",
            body="Testovací notifikace",
            icon="dialog-information",
            urgent=False,
        )
        # Simuluj chybějící notify-send — subprocess.run vyhodí FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError("notify-send not found")):
            result = send_desktop_notification(n)

        # Musí vrátit False (ne vyhodit výjimku)
        assert result is False


class TestNotificationEngineSmoke:
    """Smoke test — NotificationEngine lze vytvořit a zastavit."""

    def test_engine_create_stop(self):
        engine = NotificationEngine(config={"notification_cpu_threshold": 90})
        engine.start()
        assert engine._running is True
        engine.stop()
        # Vlákno je daemon — jen ověříme, že stop() nehodí výjimku
        assert engine._running is False

    def test_engine_send_no_crash(self):
        engine = NotificationEngine()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = engine.send("E.V. test", "tělo notifikace", urgent=False)
        assert result is False
