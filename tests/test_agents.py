"""Unit tests for background AgentManager / agents."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents import (
    AgentManager,
    BaseAgent,
    IdleDetectorAgent,
    ProcessWatcherAgent,
    SystemMonitorAgent,
)
from event_bus import EventType

pytestmark = [pytest.mark.unit]


@pytest.fixture
def bus():
    b = MagicMock()
    b.emit = MagicMock()
    b.subscribe = MagicMock()
    return b


def test_base_agent_start_stop_tick(bus):
    agent = BaseAgent(bus=bus, interval=0.01)
    agent.tick = MagicMock()
    agent.start()
    assert agent._running is True
    agent.start()  # idempotent
    agent.stop()
    assert agent._running is False
    agent.emit(EventType.AGENT_INFO, {"ok": True})
    bus.emit.assert_called()


def test_system_monitor_cooldown(bus):
    mon = SystemMonitorAgent(bus=bus, cpu_threshold=0, ram_threshold=0)
    assert mon._can_alert("cpu", 1000.0) is True
    assert mon._can_alert("cpu", 1001.0) is False
    assert mon._can_alert("cpu", 1000.0 + mon._alert_cooldown + 1) is True


def test_process_watcher_emits_stopped(bus):
    watcher = ProcessWatcherAgent(bus=bus, watch=["definitely-not-running-xyz"])
    watcher._known["definitely-not-running-xyz"] = True
    watcher.tick()
    assert any(
        call.args and call.args[0] == EventType.AGENT_ALERT
        for call in bus.emit.call_args_list
    )


def test_idle_detector_announces_once(bus):
    idle = IdleDetectorAgent(bus=bus, idle_timeout=0.0)
    idle._last_activity = 0
    idle.tick()
    idle.tick()
    infos = [c for c in bus.emit.call_args_list if c.args and c.args[0] == EventType.AGENT_INFO]
    assert len(infos) == 1


def test_agent_manager_register_status(bus):
    AgentManager._instance = None
    mgr = AgentManager(bus=bus)
    mgr.register(SystemMonitorAgent(bus=bus))
    mgr.register(ProcessWatcherAgent(bus=bus, watch=["ollama"]))
    status = mgr.status()
    assert isinstance(status, list)
    names = {row["name"] for row in status}
    assert "system_monitor" in names
    assert "process_watcher" in names
    dict_status = mgr.get_status()
    assert "system_monitor" in dict_status
    assert AgentManager.get_instance() is mgr
    AgentManager._instance = None


def test_create_default_has_three_agents(bus):
    AgentManager._instance = None
    mgr = AgentManager.create_default(bus=bus)
    assert len(mgr.status()) == 3
    AgentManager._instance = None
