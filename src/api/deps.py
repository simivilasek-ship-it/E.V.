"""Shared dependencies and runtime flags for the FastAPI app."""
from __future__ import annotations

import logging
import time

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request  # noqa: F401
    from fastapi.responses import HTMLResponse, JSONResponse  # noqa: F401
    import uvicorn  # noqa: F401

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    from loguru import logger as _loguru

    class _InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = _loguru.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            _loguru.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    logger = _loguru
    HAS_LOGURU = True
except ImportError:
    logger = logging.getLogger(__name__)
    HAS_LOGURU = False

logger_module_available = False

def get_scheduler():  # type: ignore
    raise RuntimeError("scheduler unavailable")


def get_security_manager():  # type: ignore
    raise RuntimeError("security unavailable")


try:
    from event_bus import get_event_bus, EventType, Event  # noqa: F401
    from scheduler import get_scheduler as _get_scheduler
    from security_v2 import get_security_manager as _get_security_manager
    from agents import AgentManager  # noqa: F401
    from config import CONFIG, __version__  # noqa: F401

    get_scheduler = _get_scheduler
    get_security_manager = _get_security_manager
    logger_module_available = True
except ImportError:
    __version__ = "unknown"

start_time = time.time()
