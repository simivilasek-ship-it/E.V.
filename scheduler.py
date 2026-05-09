"""
JARVIS — Task Scheduler
Plánování úloh v čase — jednoduché i opakující se.
"""

from __future__ import annotations
import threading
import time
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from event_bus import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    id:         str
    name:       str
    fn:         Callable
    args:       tuple
    kwargs:     dict
    fire_at:    float          # unix timestamp
    repeat:     Optional[float] = None   # opakování v sekundách (None = jednorázové)
    status:     TaskStatus     = TaskStatus.PENDING
    last_run:   Optional[float] = None
    run_count:  int            = 0
    max_runs:   Optional[int]  = None    # None = neomezeně


class Scheduler:
    """
    Jednoduchý task scheduler.
    Podporuje jednorázové i opakující se úlohy.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self._bus     = bus or get_event_bus()
        self._tasks:  Dict[str, ScheduledTask] = {}
        self._lock    = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="Scheduler")
        self._thread.start()
        logger.info("Scheduler spuštěn")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    # ── Plánování ─────────────────────────────────────

    def at(self, when: datetime, fn: Callable, *args,
           name: str = "", **kwargs) -> str:
        """Spustí funkci v konkrétní čas."""
        return self._add(fn, args, kwargs, when.timestamp(), None, name)

    def after(self, seconds: float, fn: Callable, *args,
              name: str = "", **kwargs) -> str:
        """Spustí funkci za X sekund."""
        return self._add(fn, args, kwargs, time.time() + seconds, None, name)

    def every(self, seconds: float, fn: Callable, *args,
              name: str = "", max_runs: Optional[int] = None, **kwargs) -> str:
        """Spouští funkci každých X sekund."""
        return self._add(fn, args, kwargs, time.time() + seconds, seconds,
                         name, max_runs)

    def every_day_at(self, hour: int, minute: int, fn: Callable, *args,
                     name: str = "", **kwargs) -> str:
        """Spouští funkci každý den v daný čas."""
        now  = datetime.now()
        fire = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if fire <= now:
            fire += timedelta(days=1)
        return self._add(fn, args, kwargs, fire.timestamp(), 86400.0, name)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
                return True
        return False

    def cancel_by_name(self, name: str) -> int:
        cancelled = 0
        with self._lock:
            for t in self._tasks.values():
                if t.name == name and t.status == TaskStatus.PENDING:
                    t.status = TaskStatus.CANCELLED
                    cancelled += 1
        return cancelled

    def get_pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"id": t.id, "name": t.name,
                 "fire_at": datetime.fromtimestamp(t.fire_at).strftime("%H:%M:%S"),
                 "repeat": t.repeat, "run_count": t.run_count}
                for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            ]

    # ── Interní ───────────────────────────────────────

    def _add(self, fn, args, kwargs, fire_at, repeat, name, max_runs=None) -> str:
        task_id = str(uuid.uuid4())[:8]
        task    = ScheduledTask(
            id=task_id, name=name or fn.__name__,
            fn=fn, args=args, kwargs=kwargs,
            fire_at=fire_at, repeat=repeat, max_runs=max_runs,
        )
        with self._lock:
            self._tasks[task_id] = task

        self._bus.emit(EventType.TASK_SCHEDULED, {
            "id": task_id, "name": task.name,
            "fire_at": datetime.fromtimestamp(fire_at).strftime("%H:%M:%S"),
            "repeat": repeat,
        })
        return task_id

    def _loop(self):
        while self._running:
            now = time.time()
            to_run = []

            with self._lock:
                for task in list(self._tasks.values()):
                    if task.status != TaskStatus.PENDING:
                        continue
                    if task.fire_at <= now:
                        to_run.append(task)

            for task in to_run:
                self._run_task(task)

            # Odstraň staré dokončené úlohy
            with self._lock:
                done_ids = [
                    tid for tid, t in self._tasks.items()
                    if t.status in (TaskStatus.DONE, TaskStatus.FAILED,
                                    TaskStatus.CANCELLED)
                ]
                for tid in done_ids:
                    del self._tasks[tid]

            time.sleep(0.5)

    def _run_task(self, task: ScheduledTask):
        task.status   = TaskStatus.RUNNING
        task.last_run = time.time()
        task.run_count += 1

        try:
            task.fn(*task.args, **task.kwargs)
            task.status = TaskStatus.DONE

            self._bus.emit(EventType.TASK_FIRED, {
                "id": task.id, "name": task.name,
                "run_count": task.run_count,
            })
        except Exception as e:
            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.name} selhal: {e}")

        # Plánuj příští spuštění pro opakující se úlohy
        if (task.repeat and task.status != TaskStatus.FAILED and
                (task.max_runs is None or task.run_count < task.max_runs)):
            with self._lock:
                new_task = ScheduledTask(
                    id=task.id, name=task.name,
                    fn=task.fn, args=task.args, kwargs=task.kwargs,
                    fire_at=time.time() + task.repeat,
                    repeat=task.repeat, run_count=task.run_count,
                    max_runs=task.max_runs,
                )
                self._tasks[task.id] = new_task


# ── Singleton ─────────────────────────────────────────

_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
        _scheduler.start()
    return _scheduler
