"""Bridge install events from EventBus to WebSocket clients (/ws/logs)."""
from __future__ import annotations

import json
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_broadcast_fn: Optional[Callable[[str], None]] = None
_registered = False


def set_broadcast(fn: Callable[[str], None]) -> None:
    """Register async-safe broadcast callback (set from dashboard on startup)."""
    global _broadcast_fn
    _broadcast_fn = fn


def _format_message(event_type: str, data: dict) -> str:
    app = data.get("app", "?")
    stage = data.get("stage", "")
    method = data.get("method", "")
    if stage == "starting":
        return f"Začínám instalaci {app}…"
    if stage == "method" and method:
        return f"Instaluji {app} přes {method}…"
    if stage == "success":
        msg = f"{app} nainstalováno"
        if method:
            msg += f" ({method})"
        if data.get("launched"):
            msg += " — spouštím"
        return msg + "."
    if stage == "error" or event_type.endswith("error"):
        errors = data.get("errors") or []
        detail = "; ".join(errors) if errors else data.get("message", "neznámá chyba")
        return f"Instalace {app} selhala: {detail}"
    return data.get("message") or f"Instalace {app}: {stage}"


def _to_ws_payload(event) -> str:
    from event_bus import EventType

    data = dict(event.data or {})
    is_error = event.type == EventType.INSTALL_ERROR
    msg_type = "install_error" if is_error else "install_progress"
    message = data.get("message") or _format_message(event.type, data)
    payload = {
        "type": msg_type,
        "app": data.get("app", ""),
        "stage": data.get("stage", ""),
        "message": message,
        "method": data.get("method"),
        "errors": data.get("errors"),
        "ts": int(time.time() * 1000),
    }
    return json.dumps(payload, ensure_ascii=False)


def _forward(event) -> None:
    if not _broadcast_fn:
        return
    try:
        _broadcast_fn(_to_ws_payload(event))
    except Exception as e:
        logger.debug(f"install broadcast failed: {e}")


def register(bus=None) -> None:
    """Subscribe to install events on the global EventBus."""
    global _registered
    if _registered:
        return
    from event_bus import EventType, get_event_bus

    bus = bus or get_event_bus()
    bus.subscribe(EventType.INSTALL_PROGRESS, _forward)
    bus.subscribe(EventType.INSTALL_ERROR, _forward)
    _registered = True
