"""
Unit testy pro async_utils.py — AsyncEngine, run_sync, priority queue, singleton.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.unit]


# ── Helpers ───────────────────────────────────────────

def _wait_done(task, timeout=5.0, interval=0.02):
    """Poll dokud task není COMPLETED/FAILED/TIMEOUT/CANCELLED."""
    from async_utils import TaskStatus
    terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED,
                TaskStatus.TIMEOUT, TaskStatus.CANCELLED}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if task.status in terminal:
            return True
        time.sleep(interval)
    return False


# ── Fixtures ─────────────────────────────────────────


@pytest.fixture
def engine():
    from async_utils import AsyncEngine
    e = AsyncEngine(max_workers=2)
    e.start()
    time.sleep(0.05)   # dej worker threadu chvíli na start
    yield e
    e.stop(timeout=2.0)


# ── Lifecycle ─────────────────────────────────────────


class TestAsyncEngineLifecycle:

    def test_start_stop(self):
        from async_utils import AsyncEngine
        e = AsyncEngine(max_workers=2)
        assert not e._running
        e.start()
        assert e._running
        e.stop(timeout=2.0)
        assert not e._running

    def test_double_start_idempotent(self):
        from async_utils import AsyncEngine
        e = AsyncEngine(max_workers=2)
        e.start()
        e.start()
        assert e._running
        e.stop(timeout=2.0)

    def test_loop_thread_daemon(self, engine):
        assert engine._loop_thread is not None
        assert engine._loop_thread.daemon


class TestRunSync:

    def test_run_sync_completes(self, engine):
        from async_utils import TaskStatus
        task = engine.run_sync(lambda: 42)
        assert _wait_done(task)
        assert task.status == TaskStatus.COMPLETED

    def test_run_sync_returns_correct_value(self, engine):
        task = engine.run_sync(lambda: 42)
        _wait_done(task)
        assert task.result == 42

    def test_run_sync_with_args(self, engine):
        task = engine.run_sync(lambda a, b: a + b, 3, 4)
        _wait_done(task)
        assert task.result == 7

    def test_run_sync_exception_sets_failed_status(self, engine):
        from async_utils import TaskStatus

        def boom():
            raise ValueError("testovací chyba")

        task = engine.run_sync(boom)
        _wait_done(task)
        assert task.status == TaskStatus.FAILED

    def test_run_sync_task_name(self, engine):
        task = engine.run_sync(lambda: None, task_name="muj_task")
        _wait_done(task)
        assert task.name == "muj_task"

    def test_multiple_tasks_concurrent(self, engine):
        results = []
        lock = threading.Lock()

        def worker(n):
            time.sleep(0.02)
            with lock:
                results.append(n)
            return n

        tasks = [engine.run_sync(worker, i) for i in range(5)]
        for t in tasks:
            _wait_done(t)
        values = [t.result for t in tasks]
        assert sorted(values) == list(range(5))

    def test_run_sync_result_attribute(self, engine):
        task = engine.run_sync(lambda: "výsledek")
        _wait_done(task)
        assert task.result == "výsledek"


class TestTaskPriority:

    def test_priority_enum_values_exist(self):
        from async_utils import TaskPriority
        for name in ("CRITICAL", "HIGH", "NORMAL", "LOW"):
            assert hasattr(TaskPriority, name)

    def test_critical_different_from_low(self):
        from async_utils import TaskPriority
        assert TaskPriority.CRITICAL.value != TaskPriority.LOW.value

    def test_run_sync_accepts_all_priorities(self, engine):
        from async_utils import TaskPriority
        for prio in TaskPriority:
            task = engine.run_sync(lambda: True, priority=prio)
            assert _wait_done(task)
            assert task.result is True


class TestAsyncTask:

    def test_task_id_unique(self, engine):
        t1 = engine.run_sync(lambda: 1)
        t2 = engine.run_sync(lambda: 2)
        assert t1.task_id != t2.task_id

    def test_task_result_after_completion(self, engine):
        task = engine.run_sync(lambda: "výsledek")
        _wait_done(task)
        assert task.result == "výsledek"

    def test_task_error_stored_on_failure(self, engine):
        from async_utils import TaskStatus

        def fail():
            raise RuntimeError("boom")

        task = engine.run_sync(fail)
        _wait_done(task)
        assert task.status == TaskStatus.FAILED
        assert task.error is not None


class TestSingleton:

    def test_get_async_engine_returns_same_instance(self):
        from async_utils import get_async_engine, shutdown_async_engine
        shutdown_async_engine()
        e1 = get_async_engine()
        e2 = get_async_engine()
        assert e1 is e2
        shutdown_async_engine(timeout=2.0)

    def test_shutdown_resets_singleton(self):
        from async_utils import get_async_engine, shutdown_async_engine
        shutdown_async_engine()
        e1 = get_async_engine()
        shutdown_async_engine(timeout=2.0)
        e2 = get_async_engine()
        assert e1 is not e2
        shutdown_async_engine(timeout=2.0)
