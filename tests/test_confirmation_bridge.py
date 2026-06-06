"""Tests for web confirmation bridge."""

import threading
import time

from confirmation_bridge import (
    has_active_clients,
    register_client,
    unregister_client,
    request_confirmation,
    respond,
)


def test_no_clients_returns_false():
    unregister_client("fake")
    assert has_active_clients() is False
    assert request_confirmation("delete_file", {"path": "/tmp/x"}) is False


def test_approve_via_respond():
    client = object()
    register_client(client)
    try:
        result: list[bool] = []

        def worker():
            result.append(request_confirmation("delete_file", {"path": "/tmp/a"}, timeout=5.0))

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.2)
        # simulate pending request — we need the id from pending; respond after broadcast
        from confirmation_bridge import _pending, _lock
        with _lock:
            req_id = next(iter(_pending.keys()))
        assert respond(req_id, True) is True
        t.join(timeout=3)
        assert result == [True]
    finally:
        unregister_client(client)


def test_deny_via_respond():
    client = object()
    register_client(client)
    try:
        result: list[bool] = []

        def worker():
            result.append(request_confirmation("shutdown", {}, timeout=5.0))

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.2)
        from confirmation_bridge import _pending, _lock
        with _lock:
            req_id = next(iter(_pending.keys()))
        assert respond(req_id, False) is True
        t.join(timeout=3)
        assert result == [False]
    finally:
        unregister_client(client)
