"""
Unit testy pro event_bus.py — subscribe, publish, wildcard, unsubscribe, history.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.unit]


@pytest.fixture
def bus():
    from event_bus import EventBus
    b = EventBus(workers=1)
    yield b
    b.stop(timeout=1.0)


def _wait_for(condition_fn, timeout=2.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


class TestSubscribePublish:

    def test_callback_called_on_publish(self, bus):
        from event_bus import Event
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        bus.publish(Event(type="test.event", data="ahoj"))
        assert _wait_for(lambda: len(received) == 1)
        assert received[0].data == "ahoj"

    def test_emit_shorthand(self, bus):
        received = []
        bus.subscribe("test.emit", lambda e: received.append(e.data))
        bus.emit("test.emit", data=42)
        assert _wait_for(lambda: len(received) == 1)
        assert received[0] == 42

    def test_multiple_subscribers_same_type(self, bus):
        from event_bus import Event
        calls = []
        bus.subscribe("multi", lambda e: calls.append("A"))
        bus.subscribe("multi", lambda e: calls.append("B"))
        bus.publish(Event(type="multi"))
        assert _wait_for(lambda: len(calls) == 2)
        assert set(calls) == {"A", "B"}

    def test_different_types_isolated(self, bus):
        from event_bus import Event
        a_calls, b_calls = [], []
        bus.subscribe("type.a", lambda e: a_calls.append(e))
        bus.subscribe("type.b", lambda e: b_calls.append(e))
        bus.publish(Event(type="type.a", data="jen A"))
        assert _wait_for(lambda: len(a_calls) == 1)
        time.sleep(0.1)
        assert len(b_calls) == 0


class TestWildcard:

    def test_wildcard_receives_all_events(self, bus):
        from event_bus import Event, EventType
        all_events = []
        bus.subscribe(EventType.ALL, lambda e: all_events.append(e.type))
        bus.publish(Event(type="x.y"))
        bus.publish(Event(type="a.b"))
        assert _wait_for(lambda: len(all_events) >= 2)
        assert "x.y" in all_events
        assert "a.b" in all_events

    def test_wildcard_plus_specific(self, bus):
        from event_bus import Event, EventType
        wildcard, specific = [], []
        bus.subscribe(EventType.ALL, lambda e: wildcard.append(e))
        bus.subscribe("my.event", lambda e: specific.append(e))
        bus.publish(Event(type="my.event"))
        assert _wait_for(lambda: len(specific) == 1 and len(wildcard) >= 1)


class TestUnsubscribe:

    def test_unsubscribe_stops_callbacks(self, bus):
        from event_bus import Event
        received = []
        unsub = bus.subscribe("unsub.test", lambda e: received.append(e))
        bus.publish(Event(type="unsub.test"))
        assert _wait_for(lambda: len(received) == 1)
        unsub()
        bus.publish(Event(type="unsub.test"))
        time.sleep(0.15)
        assert len(received) == 1

    def test_unsubscribe_nonexistent_safe(self, bus):
        bus.unsubscribe("neexistuje", lambda e: None)


class TestHistory:

    def test_history_stores_events(self, bus):
        from event_bus import Event
        bus.publish(Event(type="hist.test", data="x"))
        bus.publish(Event(type="hist.test", data="y"))
        assert _wait_for(lambda: len(bus.get_history()) >= 2)
        types = [e.type for e in bus.get_history()]
        assert "hist.test" in types

    def test_history_limit(self):
        from event_bus import EventBus, Event
        b = EventBus(workers=1)
        b._max_history = 3
        for i in range(6):
            b.publish(Event(type=f"e{i}"))
        _wait_for(lambda: len(b._history) >= 3, timeout=3.0)
        time.sleep(0.2)
        assert len(b._history) <= 3
        b.stop(timeout=1.0)


class TestThreadSafety:

    def test_concurrent_publishes(self, bus):
        from event_bus import Event
        counter = []
        lock = threading.Lock()

        def cb(e):
            with lock:
                counter.append(1)

        bus.subscribe("concurrent", cb)
        threads = [
            threading.Thread(target=lambda: bus.publish(Event(type="concurrent")))
            for _ in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert _wait_for(lambda: len(counter) == 20, timeout=3.0)


class TestSingleton:

    def test_get_event_bus_same_instance(self):
        from event_bus import get_event_bus
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2

    def test_event_type_gui_command_exists(self):
        from event_bus import EventType
        assert hasattr(EventType, "GUI_COMMAND")

    def test_event_type_all_wildcard_exists(self):
        from event_bus import EventType
        assert EventType.ALL == "*"

    def test_event_type_system_events_exist(self):
        from event_bus import EventType
        assert hasattr(EventType, "JARVIS_READY")
        assert hasattr(EventType, "JARVIS_SHUTDOWN")
