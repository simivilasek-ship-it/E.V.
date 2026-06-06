"""JARVIS unified runtime — Copilot + Agent pipeline pro web API."""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_runtime = None
_lock = threading.Lock()
_ready = threading.Event()


def init_runtime() -> None:
    """Spustí plný JarvisApp (agenti, security, proactive, mise)."""
    global _runtime
    with _lock:
        if _runtime is not None:
            return
        try:
            from config import CONFIG

            CONFIG["wake_word_enabled"] = False
            CONFIG["web_mode"] = True
            from app_core import JarvisApp

            logger.info("JARVIS runtime: inicializuji Copilot + Agent pipeline…")
            _runtime = JarvisApp()
            _ready.set()
            logger.info("JARVIS runtime připraven (agenti, security, proactive, mise)")
        except Exception as e:
            logger.error(f"JARVIS runtime init selhal: {e}", exc_info=True)
            raise


def get_runtime():
    """Vrátí singleton JarvisApp; lazy init pokud lifespan ještě neběžel."""
    if _runtime is None:
        init_runtime()
    return _runtime


def is_ready() -> bool:
    return _runtime is not None and _ready.is_set()


def shutdown_runtime() -> None:
    global _runtime
    with _lock:
        if _runtime is None:
            return
        try:
            if getattr(_runtime, "mission_manager", None):
                _runtime.mission_manager.stop()
            if getattr(_runtime, "agent_manager", None):
                _runtime.agent_manager.stop_all()
            if getattr(_runtime, "worker_manager", None):
                _runtime.worker_manager.stop()
            if getattr(_runtime, "wake_word", None):
                _runtime.wake_word.stop()
            _runtime.llm.save_history()
        except Exception as e:
            logger.debug(f"Runtime shutdown: {e}")
        _runtime = None
        _ready.clear()


def process_chat(
    text: str,
    *,
    on_chunk: Optional[Callable[[str], None]] = None,
    on_agent_step: Optional[Callable[[str], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> str:
    """Zpracuje zprávu přes CommandRouter (plugin → local → agent → LLM)."""
    app = get_runtime()
    return app._router.process_for_web(
        text,
        on_chunk=on_chunk,
        on_agent_step=on_agent_step,
        on_status=on_status,
    )
