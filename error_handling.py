"""
JARVIS v4.2 — Error Handling & Fallback System
Robust error handling with graceful degradation and recovery.
"""

import os
import sys
import time
import json
import logging
import traceback
import functools
from typing import (Any, Callable, Dict, List, Optional, Tuple, Type,
                    TypeVar, Union, Awaitable, Generic)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ══════════════════════════════════════════════════════
#  ERROR SEVERITY
# ══════════════════════════════════════════════════════

class ErrorSeverity(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


# ══════════════════════════════════════════════════════
#  ERROR TYPES
# ══════════════════════════════════════════════════════

class ErrorCategory(Enum):
    NETWORK = "network"
    SYSTEM = "system"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


# ══════════════════════════════════════════════════════
#  ERROR RECORD
# ══════════════════════════════════════════════════════

@dataclass
class ErrorRecord:
    """Záznam o chybě"""
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    source: str
    message: str
    exception: Optional[Exception] = None
    traceback: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = False
    recovery_action: str = ""


# ══════════════════════════════════════════════════════
#  FALLBACK RESULT
# ══════════════════════════════════════════════════════

@dataclass
class FallbackResult(Generic[T]):
    """Výsledek operace s fallbackem"""
    success: bool
    result: Optional[T] = None
    error: Optional[Exception] = None
    error_message: str = ""
    fallback_used: bool = False
    fallback_source: str = ""
    duration_ms: float = 0.0


# ══════════════════════════════════════════════════════
#  ERROR HANDLER
# ══════════════════════════════════════════════════════

class ErrorHandler:
    """
    Centrální error handler s podporou:
    - Kategorizace chyb
    - Automatického fallbacku
    - Logování a notifikací
    - Recovery strategií
    - Rate limitingu
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._error_log: List[ErrorRecord] = []
        self._max_log_size = self.config.get("max_error_log", 1000)
        self._rate_limit_window = self.config.get("rate_limit_window", 60.0)  # sekund
        self._rate_limit_max = self.config.get("rate_limit_max", 10)  # max chyb v okně
        self._error_counts: Dict[str, List[float]] = {}
        self._suppressed_errors: set = set()

        # Fallback registry
        self._fallbacks: Dict[str, List[Callable]] = {}
        self._recovery_strategies: Dict[str, Callable] = {}

        # Callbacky
        self.on_error: Optional[Callable[[ErrorRecord], None]] = None
        self.on_recovery: Optional[Callable[[ErrorRecord], None]] = None

        logger.info(f"ErrorHandler inicializován (max_log={self._max_log_size})")

    # ── REGISTRACE FALLBACKŮ ─────────────────────────

    def register_fallback(self, operation: str, fallback_func: Callable[..., Any]):
        """
        Zaregistruje fallback funkci pro danou operaci.
        Fallbacky se zkouší v pořadí registrace.
        """
        if operation not in self._fallbacks:
            self._fallbacks[operation] = []
        self._fallbacks[operation].append(fallback_func)
        logger.debug(f"Fallback registrován pro '{operation}': {fallback_func.__name__}")

    def register_recovery(self, error_type: str, recovery_func: Callable[[ErrorRecord], bool]):
        """
        Zaregistruje recovery strategii pro daný typ chyby.
        Recovery funkce by měla vrátit True pokud byla oprava úspěšná.
        """
        self._recovery_strategies[error_type] = recovery_func
        logger.debug(f"Recovery strategie registrována pro '{error_type}'")

    # ── EXECUTION WITH FALLBACK ──────────────────────

    def execute_with_fallback(self, operation: str, primary_func: Callable[..., T],
                              *args, **kwargs) -> FallbackResult[T]:
        """
        Spustí operaci s fallbackem.
        Pokud primární funkce selže, zkouší se fallbacky v pořadí registrace.
        """
        start_time = time.time()

        # Zkus primární funkci
        try:
            result = primary_func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            return FallbackResult(
                success=True,
                result=result,
                duration_ms=duration,
            )
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Primární funkce '{operation}' selhala: {error_msg}")

            # Zkus fallbacky
            fallbacks = self._fallbacks.get(operation, [])
            for i, fallback_func in enumerate(fallbacks):
                try:
                    logger.info(f"Zkouším fallback {i+1}/{len(fallbacks)} pro '{operation}'")
                    result = fallback_func(*args, **kwargs)
                    duration = (time.time() - start_time) * 1000
                    return FallbackResult(
                        success=True,
                        result=result,
                        fallback_used=True,
                        fallback_source=fallback_func.__name__,
                        duration_ms=duration,
                    )
                except Exception as fb_e:
                    logger.warning(f"Fallback {i+1} selhal: {fb_e}")
                    continue

            # Všechny fallbacky selhaly
            duration = (time.time() - start_time) * 1000
            return FallbackResult(
                success=False,
                error=e,
                error_message=error_msg,
                duration_ms=duration,
            )

    def safe_execute(self, func: Callable[..., T], *args,
                     default: Optional[T] = None,
                     error_message: str = "",
                     severity: ErrorSeverity = ErrorSeverity.ERROR,
                     category: ErrorCategory = ErrorCategory.UNKNOWN,
                     **kwargs) -> T:
        """
        Bezpečné spuštění funkce s výchozí hodnotou při chybě.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.log_error(
                severity=severity,
                category=category,
                source=func.__name__,
                message=error_message or str(e),
                exception=e,
                context={"args": str(args), "kwargs": str(kwargs)},
            )
            return default  # type: ignore

    # ── ERROR LOGGING ────────────────────────────────

    def log_error(self, severity: ErrorSeverity, category: ErrorCategory,
                  source: str, message: str,
                  exception: Optional[Exception] = None,
                  context: Dict[str, Any] = None,
                  recovered: bool = False,
                  recovery_action: str = ""):
        """Zaloguje chybu s kontrolou rate limitu"""
        # Rate limiting
        if self._is_rate_limited(source):
            logger.debug(f"Rate limit pro '{source}', chyba přeskočena")
            return

        # Vytvoř záznam
        record = ErrorRecord(
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            source=source,
            message=message,
            exception=exception,
            traceback=traceback.format_exc() if exception else "",
            context=context or {},
            recovered=recovered,
            recovery_action=recovery_action,
        )

        # Přidej do logu
        self._error_log.append(record)
        if len(self._error_log) > self._max_log_size:
            self._error_log.pop(0)

        # Loguj podle severity
        log_msg = f"[{category.value}] {source}: {message}"
        if severity == ErrorSeverity.DEBUG:
            logger.debug(log_msg)
        elif severity == ErrorSeverity.INFO:
            logger.info(log_msg)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        elif severity == ErrorSeverity.ERROR:
            logger.error(log_msg)
            if exception:
                logger.debug(f"Traceback: {record.traceback}")
        elif severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg)
            if exception:
                logger.debug(f"Traceback: {record.traceback}")

        # Notifikace
        if self.on_error:
            try:
                self.on_error(record)
            except Exception:
                pass

        # Zkus recovery
        if not recovered and category.value in self._recovery_strategies:
            self._attempt_recovery(record)

    def _is_rate_limited(self, source: str) -> bool:
        """Zkontroluje rate limiting pro zdroj chyb"""
        now = time.time()
        if source not in self._error_counts:
            self._error_counts[source] = []

        # Vyčisti staré záznamy
        self._error_counts[source] = [
            t for t in self._error_counts[source]
            if now - t < self._rate_limit_window
        ]

        # Zkontroluj limit
        if len(self._error_counts[source]) >= self._rate_limit_max:
            return True

        self._error_counts[source].append(now)
        return False

    def _attempt_recovery(self, record: ErrorRecord):
        """Pokusí se o automatickou recovery"""
        strategy = self._recovery_strategies.get(record.category.value)
        if not strategy:
            return

        try:
            logger.info(f"Zkouším recovery pro '{record.category.value}'")
            success = strategy(record)
            if success:
                record.recovered = True
                record.recovery_action = f"Automatická recovery: {strategy.__name__}"
                logger.info(f"Recovery úspěšná pro '{record.category.value}'")
                if self.on_recovery:
                    try:
                        self.on_recovery(record)
                    except Exception:
                        pass
            else:
                logger.warning(f"Recovery selhala pro '{record.category.value}'")
        except Exception as e:
            logger.error(f"Chyba při recovery: {e}")

    # ── ERROR QUERIES ────────────────────────────────

    def get_errors(self, category: Optional[ErrorCategory] = None,
                   severity: Optional[ErrorSeverity] = None,
                   source: Optional[str] = None,
                   limit: int = 50) -> List[ErrorRecord]:
        """Získá chyby podle filtrů"""
        filtered = list(self._error_log)

        if category:
            filtered = [e for e in filtered if e.category == category]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if source:
            filtered = [e for e in filtered if source in e.source]

        return filtered[-limit:]

    def get_error_stats(self) -> Dict[str, Any]:
        """Vrátí statistiky chyb"""
        total = len(self._error_log)
        if total == 0:
            return {"total": 0, "categories": {}, "severities": {}, "recovered": 0}

        categories = {}
        severities = {}
        recovered = 0

        for error in self._error_log:
            cat = error.category.value
            categories[cat] = categories.get(cat, 0) + 1

            sev = error.severity.name
            severities[sev] = severities.get(sev, 0) + 1

            if error.recovered:
                recovered += 1

        return {
            "total": total,
            "categories": categories,
            "severities": severities,
            "recovered": recovered,
            "recovery_rate": (recovered / total * 100) if total > 0 else 0,
        }

    def clear_errors(self):
        """Vymaže log chyb"""
        self._error_log.clear()
        self._error_counts.clear()
        logger.info("Error log vymazán")


# ══════════════════════════════════════════════════════
#  DECORATORS
# ══════════════════════════════════════════════════════

def with_error_handling(handler: ErrorHandler,
                        default: Any = None,
                        error_message: str = "",
                        severity: ErrorSeverity = ErrorSeverity.ERROR,
                        category: ErrorCategory = ErrorCategory.UNKNOWN):
    """
    Dekorátor pro automatické error handling.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return handler.safe_execute(
                func, *args,
                default=default,
                error_message=error_message or f"Chyba v {func.__name__}",
                severity=severity,
                category=category,
                **kwargs
            )
        return wrapper
    return decorator


def with_fallback(handler: ErrorHandler, operation: str):
    """
    Dekorátor pro automatický fallback.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = handler.execute_with_fallback(operation, func, *args, **kwargs)
            if not result.success:
                raise result.error or RuntimeError(result.error_message)
            return result.result
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════
#  BUILT-IN FALLBACKS
# ══════════════════════════════════════════════════════

def register_builtin_fallbacks(handler: ErrorHandler):
    """Zaregistruje built-in fallbacky"""

    # Fallback pro síťové operace
    def _network_fallback(*args, **kwargs) -> Any:
        """Fallback pro síťové chyby — zkus znovu po krátké pauze"""
        time.sleep(1)
        raise RuntimeError("Síťový fallback selhal")

    handler.register_fallback("network_request", _network_fallback)

    # Fallback pro STT
    def _stt_fallback(*args, **kwargs) -> Optional[str]:
        """Fallback pro STT — vrátí None"""
        logger.warning("STT fallback: vracím None")
        return None

    handler.register_fallback("stt_listen", _stt_fallback)

    # Fallback pro TTS
    def _tts_fallback(text: str) -> str:
        """Fallback pro TTS — pouze zaloguje"""
        logger.info(f"TTS fallback: {text[:50]}...")
        return "ok"

    handler.register_fallback("tts_speak", _tts_fallback)

    # Fallback pro LLM
    def _llm_fallback(text: str) -> Tuple[str, Dict]:
        """Fallback pro LLM — základní odpověď"""
        logger.warning(f"LLM fallback pro: {text[:50]}...")
        return f"Omlouvám se, ale LLM není dostupný. Zpráva: {text}", {"action": "answer", "params": {}}

    handler.register_fallback("llm_ask", _llm_fallback)
    handler.register_fallback("llm_stream", _llm_fallback)

    # Recovery strategie
    def _network_recovery(record: ErrorRecord) -> bool:
        """Recovery pro síťové chyby — zkontroluj pripojení"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            logger.info("Síťové připojení obnoveno")
            return True
        except Exception:
            logger.warning("Síť stále nedostupná")
            return False

    handler.register_recovery("network", _network_recovery)

    def _dependency_recovery(record: ErrorRecord) -> bool:
        """Recovery pro chybějící dependency — zaloguj a pokračuj"""
        logger.warning(f"Chybějící dependency: {record.message}")
        return True  # Pokračujeme s omezenou funkcionalitou

    handler.register_recovery("dependency", _dependency_recovery)

    logger.info("Built-in fallbacky registrovány")


# ══════════════════════════════════════════════════════
#  SINGLETON
# ══════════════════════════════════════════════════════

_handler_instance: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Vrátí globální instanci ErrorHandler (singleton)"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = ErrorHandler()
        register_builtin_fallbacks(_handler_instance)
    return _handler_instance