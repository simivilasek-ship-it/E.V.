"""WebSocket connection managers and broadcast helpers."""
from __future__ import annotations

import asyncio
import json

from src.api.deps import HAS_FASTAPI

if HAS_FASTAPI:
    from fastapi import WebSocket


class ConnectionManager:
    """Thread-safe správce WebSocket spojení."""

    def __init__(self):
        self._clients: set = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: str):
        dead: set = set()
        async with self._lock:
            clients = set(self._clients)
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        if dead:
            async with self._lock:
                self._clients -= dead

    def __len__(self):
        return len(self._clients)


ws_mgr = ConnectionManager()
graph_mgr = ConnectionManager()
confirm_mgr = ConnectionManager()

# zpětná kompatibilita — kód co přistupuje přímo přes _ws_clients / _graph_clients
ws_clients: set = set()
graph_clients: set = set()

main_loop = None


async def broadcast_graph_event(event: dict):
    """Broadcastuje graph event všem připojeným klientům."""
    dead = set()
    payload = json.dumps(event)
    for client in list(graph_clients):
        try:
            await client.send_text(payload)
        except Exception:
            dead.add(client)
    graph_clients.difference_update(dead)
