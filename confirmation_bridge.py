"""Web confirmation bridge for ELEVATED/RESTRICTED actions in headless mode."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_pending: Dict[str, dict] = {}
_confirm_clients: set = set()
_broadcast_fn: Optional[Callable[[dict], None]] = None
_lock = threading.Lock()


def set_broadcast(fn: Callable[[dict], None]) -> None:
    """Register async-safe broadcast callback (set from dashboard on startup)."""
    global _broadcast_fn
    _broadcast_fn = fn


def register_client(client: object) -> None:
    with _lock:
        _confirm_clients.add(client)


def unregister_client(client: object) -> None:
    with _lock:
        _confirm_clients.discard(client)


def has_active_clients() -> bool:
    with _lock:
        return bool(_confirm_clients)


def _broadcast(payload: dict) -> None:
    if _broadcast_fn:
        try:
            _broadcast_fn(payload)
        except Exception as e:
            logger.debug(f"confirm broadcast failed: {e}")


def request_confirmation(action: str, params: Dict[str, Any], timeout: float = 60.0) -> bool:
    """Block until user approves/denies via web UI, or timeout."""
    if not has_active_clients():
        return False

    req_id = str(uuid.uuid4())[:12]
    event = threading.Event()

    with _lock:
        _pending[req_id] = {
            "id": req_id,
            "action": action,
            "params": params,
            "event": event,
            "result": False,
            "created": time.time(),
        }

    _broadcast({
        "type": "confirm_request",
        "id": req_id,
        "action": action,
        "params": params,
        "timeout_s": int(timeout),
    })

    approved = event.wait(timeout=timeout)

    with _lock:
        entry = _pending.pop(req_id, None)

    if not approved:
        _broadcast({"type": "confirm_timeout", "id": req_id, "action": action})
        return False

    return bool(entry.get("result")) if entry else False


def respond(req_id: str, approved: bool) -> bool:
    """Apply user response from web UI."""
    with _lock:
        entry = _pending.get(req_id)
        if not entry:
            return False
        entry["result"] = approved
        entry["event"].set()

    _broadcast({
        "type": "confirm_resolved",
        "id": req_id,
        "approved": approved,
    })
    return True
