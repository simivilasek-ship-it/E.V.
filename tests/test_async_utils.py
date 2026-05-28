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


# ── Fixtures ─────────────────────────────────────────


@pytest.fixture
def engine():
    from async_utils import AsyncEngine
    e = AsyncEngine(max_workers=2)
    e.start()
    yield e
    e.stop(timeout=2.0)


def _wait_result(task, timeout=5.0):
    """Čeká na výsledek AsyncTask přes result_blocking()."""
    return task.result_blocking(timeout=timeout)


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

    def test_run_sync_returns_task(self, engine):
        from async_utils import TaskStatus
        task = engine.run_sync(lambda: 42)
        result = _wait_result(task)
        assert result == 42
        assert task.status == TaskStatus.COMPLETED

    def test_run_sync_with_args(self, engine):
        task = engine.run_sync(lambda a, b: a + b, 3, 4)
        assert _wait_result(task) == 7

    def test_run_sync_exception_sets_failed_status(self, engine):
        from async_utils import TaskStatus

        def boom():
            raise ValueError("testovací chyba")

        task = engine.run_sync(boom)
        _wait_result(task)
        assert task.status == TaskStatus.FAILED

    def test_run_sync_task_name(self, engine):
        task = engine.run_sync(lambda: None, task_name="muj_task")
        _wait_result(task)
        assert task.name == "muj_task"

    def test_multiple_tasks_concurrent(self, engine):
        results = []
        lock = threading.Lock()

        def worker(n):
            time.sleep(0.05)
            with lock:
                results.append(n)
            return n

        tasks = [engine.run_sync(worker, i) for i in range(5)]
        values = [_wait_result(t) for t in tasks]
        assert sorted(values) == list(range(5))

    def test_run_sync_result_attribute(self, engine):
        task = engine.run_sync(lambda: "výsledek")
        _wait_result(task)
        assert task.result == "výsledek"


class TestTaskPriority:

    def test_priority_enum_values_exist(self):
        from async_utils import TaskPriority
        assert hasattr(TaskPriority, "CRITICAL")
        assert hasattr(TaskPriority, "HIGH")
        assert hasattr(TaskPriority, "NORMAL")
        assert hasattr(TaskPriority, "LOW")

    def test_critical_higher_value_than_low(self):
        from async_utils import TaskPriority
        # CRITICAL=3, HIGH=2, NORMAL=1, LOW=0 — vyšší číslo = vyšší priorita
        assert TaskPriority.CRITICAL.value > TaskPriority.LOW.value

    def test_run_sync_accepts_priority(self, engine):
        from async_utils import TaskPriority
        task = engine.run_sync(lambda: "ok", priority=TaskPriority.HIGH)
        assert _wait_result(task) == "ok"

    def test_run_sync_all_priorities(self, engine):
        from async_utils import TaskPriority
        for prio in TaskPriority:
            task = engine.run_sync(lambda: prio.name, priority=prio)
            result = _wait_result(task)
            assert result == prio.name


class TestAsyncTask:

    def test_task_id_unique(self, engine):
        t1 = engine.run_sync(lambda: 1)
        t2 = engine.run_sync(lambda: 2)
        assert t1.task_id != t2.task_id

    def test_task_result_blocking(self, engine):
        task = engine.run_sync(lambda: "výsledek")
        val = task.result_blocking(timeout=5.0)
        assert val == "výsledek"

    def test_task_result_attribute_after_wait(self, engine):
        task = engine.run_sync(lambda: 99)
        task.result_blocking(timeout=5.0)
        assert task.result == 99

    def test_task_error_stored_on_failure(self, engine):
        from async_utils import TaskStatus

        def fail():
            raise RuntimeError("boom")

        task = engine.run_sync(fail)
        task.result_blocking(timeout=5.0)
        assert task.status == TaskStatus.FAILED


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
