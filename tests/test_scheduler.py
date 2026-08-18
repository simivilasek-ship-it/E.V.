"""Unit tests for Scheduler."""
from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from scheduler import Scheduler

pytestmark = [pytest.mark.unit]


@pytest.fixture
def sched():
    bus = MagicMock()
    s = Scheduler(bus=bus)
    yield s
    s.stop()


def test_after_and_cancel(sched):
    ran = []
    tid = sched.after(60, lambda: ran.append(1), name="later")
    pending = sched.get_pending()
    assert any(p["id"] == tid for p in pending)
    assert sched.cancel(tid) is True
    assert sched.cancel("missing") is False
    assert all(p["id"] != tid for p in sched.get_pending())


def test_cancel_by_name(sched):
    sched.after(30, lambda: None, name="job")
    sched.after(30, lambda: None, name="job")
    assert sched.cancel_by_name("job") == 2
    assert sched.cancel_by_name("job") == 0


def test_fmt_repeat():
    assert Scheduler._fmt_repeat(None) == "—"
    assert Scheduler._fmt_repeat(30) == "30s"
    assert Scheduler._fmt_repeat(120) == "2m"
    assert Scheduler._fmt_repeat(3600) == "1h"
    assert Scheduler._fmt_repeat(86400) == "1d"


def test_every_day_at_schedules_future(sched):
    now = datetime.now()
    tid = sched.every_day_at(now.hour, now.minute, lambda: None, name="daily")
    pending = {p["id"]: p for p in sched.get_pending()}
    assert tid in pending
    assert pending[tid]["repeat"] == "1d"


def test_task_fires_quickly(sched):
    ran = []
    sched.start()
    sched.after(0.05, lambda: ran.append("ok"), name="soon")
    deadline = time.time() + 2.0
    while not ran and time.time() < deadline:
        time.sleep(0.05)
    assert ran == ["ok"]
