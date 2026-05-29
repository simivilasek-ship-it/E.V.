"""
JARVIS v4.4 — Async Operations
Unified async/threading layer for JARVIS operations.
Provides consistent async execution with proper error handling and lifecycle management.
"""

import asyncio
import threading
import logging
import queue
import time
import functools
from typing import (Any, Callable, Coroutine, Dict, List, Optional,
                    TypeVar, Generic, Union, Awaitable)
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ══════════════════════════════════════════════════════
#  TASK PRIORITY & STATUS
# ══════════════════════════════════════════════════════

class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# ══════════════════════════════════════════════════════
#  TASK RESULT
# ══════════════════════════════════════════════════════

@dataclass
class TaskResult(Generic[T]):
    """Výsledek asynchronní operace"""
    task_id: str
    status: TaskStatus
    result: Optional[T] = None
    error: Optional[Exception] = None
    error_message: str = ""
    duration_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == TaskStatus.FAILED


# ══════════════════════════════════════════════════════
#  ASYNC ENGINE
# ══════════════════════════════════════════════════════

class AsyncEngine:
    """
    Hlavní engine pro asynchronní operace.
    Spravuje event loop, thread pool a task queue.
    """

    def __init__(self, max_workers: int = 4, max_queue_size: int = 100):
        self._max_workers = max_workers
        self._max_queue_size = max_queue_size
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="jarvis-worker"
        )
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, 'AsyncTask'] = {}
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._task_counter = 0
        self._lock = threading.Lock()

        # Callbacky
        self.on_task_start: Optional[Callable[[str], None]] = None
        self.on_task_complete: Optional[Callable[[TaskResult], None]] = None
        self.on_task_error: Optional[Callable[[str, Exception], None]] = None

        logger.info(f"AsyncEngine inicializován ({max_workers} workers)")

    def start(self):
        """Spustí event loop v samostatném vlákně"""
        if self._running:
            return

        self._running = True

        # Vytvoř event loop v samostatném vlákně
        def _run_loop():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._event_loop.run_forever()

        self._loop_thread = threading.Thread(
            target=_run_loop,
            daemon=True,
            name="jarvis-event-loop"
        )
        self._loop_thread.start()

        # Spusť worker pro zpracování fronty
        self._start_queue_worker()

        logger.info("AsyncEngine spuštěn")

    def stop(self, timeout: float = 5.0):
        """Zastaví engine a počká na dokončení úloh"""
        self._running = False

        # Zruš všechny pending tasky
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if task.status == TaskStatus.PENDING:
                    task.cancel()

        # Zastav event loop
        if self._event_loop and self._event_loop.is_running():
            try:
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                if self._loop_thread:
                    self._loop_thread.join(timeout=timeout)
            except Exception as e:
                logger.warning(f"Chyba při zastavování event loop: {e}")

        # Ukliď thread pool
        self._thread_pool.shutdown(wait=False)

        logger.info("AsyncEngine zastaven")

    def _start_queue_worker(self):
        """Spustí worker pro zpracování fronty úloh"""
        def _worker():
            while self._running:
                try:
                    priority, _, task_id = self._task_queue.get(timeout=0.5)
                    task = self._tasks.get(task_id)
                    if task and task.status == TaskStatus.PENDING:
                        self._execute_task(task)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Chyba queue worker: {e}")

        thread = threading.Thread(target=_worker, daemon=True, name="jarvis-queue-worker")
        thread.start()

    def _generate_task_id(self) -> str:
        """Vygeneruje unikátní ID úlohy"""
        with self._lock:
            self._task_counter += 1
            return f"task-{self._task_counter}-{int(time.time() * 1000)}"

    # ── SPUŠTĚNÍ ÚLOH ────────────────────────────────

    def run_sync(self, func: Callable[..., T], *args,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 timeout: Optional[float] = None,
                 task_name: str = "",
                 **kwargs) -> 'AsyncTask[T]':
        """
        Spustí synchronní funkci v thread poolu.
        Vrací AsyncTask pro sledování průběhu.
        """
        task_id = self._generate_task_id()
        task = AsyncTask(
            task_id=task_id,
            name=task_name or func.__name__,
            priority=priority,
            timeout=timeout,
            engine=self,
        )

        with self._lock:
            self._tasks[task_id] = task

        # Přidej do fronty
        self._task_queue.put((priority.value, time.time(), task_id))

        # Ulož parametry pro pozdější spuštění
        task._func = func
        task._args = args
        task._kwargs = kwargs

        return task

    def run_async(self, coro: Coroutine[Any, Any, T],
                  priority: TaskPriority = TaskPriority.NORMAL,
                  timeout: Optional[float] = None,
                  task_name: str = "") -> 'AsyncTask[T]':
        """
        Spustí asynchronní funkci v event loop.
        Vrací AsyncTask pro sledování průběhu.
        """
        task_id = self._generate_task_id()
        task = AsyncTask(
            task_id=task_id,
            name=task_name or coro.__name__ if hasattr(coro, '__name__') else "async",
            priority=priority,
            timeout=timeout,
            engine=self,
        )

        with self._lock:
            self._tasks[task_id] = task

        # Spusť v event loop
        if self._event_loop and self._event_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._event_loop)
            task._future = future
            task._status = TaskStatus.RUNNING

            # Přidej callback pro dokončení
            future.add_done_callback(
                lambda f: self._on_async_done(task_id, f)
            )

            # Timeout
            if timeout:
                self._event_loop.call_later(
                    timeout,
                    lambda: self._check_timeout(task_id)
                )

        return task

    def _execute_task(self, task: 'AsyncTask'):
        """Spustí úlohu v thread poolu"""
        if task.status != TaskStatus.PENDING:
            return

        task._status = TaskStatus.RUNNING
        task._start_time = time.time()

        # Notifikace
        if self.on_task_start:
            try:
                self.on_task_start(task.task_id)
            except Exception:
                pass

        # Spusť v thread poolu
        future = self._thread_pool.submit(self._run_task_wrapper, task)
        task._future = future

        # Callback pro dokončení
        future.add_done_callback(lambda f: self._on_task_done(task.task_id, f))

    def _run_task_wrapper(self, task: 'AsyncTask'):
        """Wrapper pro spuštění úlohy s timeoutem a error handlingem"""
        try:
            if task.timeout:
                # Spusť s timeoutem
                result = self._run_with_timeout(task)
            else:
                result = task._func(*task._args, **task._kwargs)

            task._result = result
            task._status = TaskStatus.COMPLETED
            return result

        except Exception as e:
            task._error = e
            task._status = TaskStatus.FAILED
            task._error_message = str(e)
            logger.error(f"Task '{task.name}' selhal: {e}")
            return None

    def _run_with_timeout(self, task: 'AsyncTask') -> Any:
        """Spustí funkci s timeoutem"""
        result = [None]
        exception = [None]
        finished = threading.Event()

        def _target():
            try:
                result[0] = task._func(*task._args, **task._kwargs)
            except Exception as e:
                exception[0] = e
            finally:
                finished.set()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()

        if not finished.wait(timeout=task.timeout):
            task._status = TaskStatus.TIMEOUT
            raise TimeoutError(f"Task '{task.name}' překročil timeout {task.timeout}s")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _on_task_done(self, task_id: str, future: Future):
        """Callback po dokončení úlohy v thread poolu"""
        task = self._tasks.get(task_id)
        if not task:
            return

        task._completed_at = datetime.now()
        task._duration_ms = (time.time() - task._start_time) * 1000 if task._start_time else 0

        result = TaskResult(
            task_id=task_id,
            status=task.status,
            result=task._result,
            error=task._error,
            error_message=task._error_message,
            duration_ms=task._duration_ms,
            completed_at=task._completed_at,
        )

        # Notifikace
        if task.status == TaskStatus.FAILED and self.on_task_error:
            try:
                self.on_task_error(task_id, task._error)
            except Exception:
                pass

        if self.on_task_complete:
            try:
                self.on_task_complete(result)
            except Exception:
                pass

        # Vyčisti po dokončení
        self._cleanup_task(task_id)

    def _on_async_done(self, task_id: str, future: Future):
        """Callback po dokončení async úlohy"""
        task = self._tasks.get(task_id)
        if not task:
            return

        task._completed_at = datetime.now()

        try:
            exception = future.exception()
            if exception:
                task._status = TaskStatus.FAILED
                task._error = exception
                task._error_message = str(exception)
            else:
                task._result = future.result()
                task._status = TaskStatus.COMPLETED
        except Exception as e:
            task._status = TaskStatus.FAILED
            task._error = e
            task._error_message = str(e)

        result = TaskResult(
            task_id=task_id,
            status=task.status,
            result=task._result,
            error=task._error,
            error_message=task._error_message,
            completed_at=task._completed_at,
        )

        if self.on_task_complete:
            try:
                self.on_task_complete(result)
            except Exception:
                pass

        self._cleanup_task(task_id)

    def _check_timeout(self, task_id: str):
        """Zkontroluje timeout async úlohy"""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task._status = TaskStatus.TIMEOUT
            task._error_message = f"Timeout po {task.timeout}s"
            if task._future:
                task._future.cancel()

    def _cleanup_task(self, task_id: str):
        """Vyčistí dokončenou úlohu a udržuje max 100 úloh v paměti."""
        with self._lock:
            # Vždy smaž dokončenou úlohu
            self._tasks.pop(task_id, None)
            # Pokud stále přesahujeme limit, smaž nejdéle dokončenou
            if len(self._tasks) > 100:
                oldest = min(
                    self._tasks.keys(),
                    key=lambda k: (
                        self._tasks[k]._completed_at or self._tasks[k].created_at
                    ),
                )
                del self._tasks[oldest]

    # ── SPRÁVA ÚLOH ──────────────────────────────────

    def cancel_task(self, task_id: str) -> bool:
        """Zruší úlohu"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.cancel()
        if task._future and not task._future.done():
            task._future.cancel()

        return True

    def get_task(self, task_id: str) -> Optional['AsyncTask']:
        """Získá úlohu podle ID"""
        return self._tasks.get(task_id)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Získá výsledek úlohy"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        return TaskResult(
            task_id=task_id,
            status=task.status,
            result=task._result,
            error=task._error,
            error_message=task._error_message,
            duration_ms=task._duration_ms,
            completed_at=task._completed_at,
        )

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Počká na dokončení úlohy"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task._future:
            try:
                task._future.result(timeout=timeout)
            except TimeoutError:
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.TIMEOUT,
                    error_message=f"Timeout po {timeout}s",
                )
            except Exception as e:
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=e,
                    error_message=str(e),
                )

        return self.get_task_result(task_id)

    def get_active_tasks(self) -> List['AsyncTask']:
        """Vrátí seznam aktivních úloh"""
        return [
            task for task in self._tasks.values()
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Vrátí statistiky enginu"""
        with self._lock:
            total = len(self._tasks)
            active = len(self.get_active_tasks())
            completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)

        return {
            "total_tasks": total,
            "active_tasks": active,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "queue_size": self._task_queue.qsize(),
            "max_workers": self._max_workers,
            "running": self._running,
        }


# ══════════════════════════════════════════════════════
#  ASYNC TASK
# ══════════════════════════════════════════════════════

class AsyncTask(Generic[T]):
    """
    Reprezentuje asynchronní úlohu.
    Umožňuje sledovat průběh, získat výsledek a zrušit úlohu.
    """

    def __init__(self, task_id: str, name: str,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 timeout: Optional[float] = None,
                 engine: Optional[AsyncEngine] = None):
        self.task_id = task_id
        self.name = name
        self.priority = priority
        self.timeout = timeout
        self._engine = engine
        self._status = TaskStatus.PENDING
        self._result: Optional[T] = None
        self._error: Optional[Exception] = None
        self._error_message: str = ""
        self._future: Optional[Future] = None
        self._func: Optional[Callable] = None
        self._args: tuple = ()
        self._kwargs: dict = {}
        self._start_time: Optional[float] = None
        self._duration_ms: float = 0.0
        self._created_at: datetime = datetime.now()
        self._completed_at: Optional[datetime] = None
        self._callbacks: List[Callable[['AsyncTask'], None]] = []

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def result(self) -> Optional[T]:
        return self._result

    @property
    def error(self) -> Optional[Exception]:
        return self._error

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def duration_ms(self) -> float:
        return self._duration_ms

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def is_done(self) -> bool:
        return self._status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                                TaskStatus.CANCELLED, TaskStatus.TIMEOUT)

    @property
    def is_success(self) -> bool:
        return self._status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self._status == TaskStatus.FAILED

    def cancel(self):
        """Zruší úlohu"""
        if not self.is_done:
            self._status = TaskStatus.CANCELLED
            if self._future and not self._future.done():
                self._future.cancel()

    def add_done_callback(self, callback: Callable[['AsyncTask'], None]):
        """Přidá callback volaný po dokončení"""
        self._callbacks.append(callback)
        if self.is_done:
            try:
                callback(self)
            except Exception:
                pass

    def result_blocking(self, timeout: Optional[float] = None) -> Optional[T]:
        """Počká na výsledek (blokující)"""
        if self._future:
            try:
                return self._future.result(timeout=timeout)
            except TimeoutError:
                self._status = TaskStatus.TIMEOUT
                raise
            except Exception as e:
                self._status = TaskStatus.FAILED
                raise
        return self._result

    def __repr__(self) -> str:
        return (f"AsyncTask(id={self.task_id}, name='{self.name}', "
                f"status={self._status.value}, priority={self.priority.name})")


# ══════════════════════════════════════════════════════
#  DECORATORS
# ══════════════════════════════════════════════════════

def async_task(engine: AsyncEngine, priority: TaskPriority = TaskPriority.NORMAL,
               timeout: Optional[float] = None):
    """
    Dekorátor pro spuštění funkce jako asynchronní úlohy.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> AsyncTask:
            return engine.run_sync(
                func, *args,
                priority=priority,
                timeout=timeout,
                task_name=func.__name__,
                **kwargs
            )
        return wrapper
    return decorator


def async_coro(engine: AsyncEngine, priority: TaskPriority = TaskPriority.NORMAL,
               timeout: Optional[float] = None):
    """
    Dekorátor pro spuštění coroutine jako asynchronní úlohy.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> AsyncTask:
            coro = func(*args, **kwargs)
            return engine.run_async(
                coro,
                priority=priority,
                timeout=timeout,
                task_name=func.__name__,
            )
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════

_engine_instance: Optional[AsyncEngine] = None


def get_async_engine() -> AsyncEngine:
    """Vrátí globální instanci AsyncEngine (singleton)"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AsyncEngine()
        _engine_instance.start()
    return _engine_instance


def shutdown_async_engine(timeout: float = 5.0):
    """Zastaví globální AsyncEngine"""
    global _engine_instance
    if _engine_instance:
        _engine_instance.stop(timeout=timeout)
        _engine_instance = None