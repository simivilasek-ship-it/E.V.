"""Auto-migrated from dashboard.py — ws_agents routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil

from src.api.deps import (
    HAS_LOGURU,
    __version__,
    get_scheduler,
    get_security_manager,
    logger,
    logger_module_available,
    start_time,
)
from src.api.paths import ROOT
from src.api.ws import (
    confirm_mgr,
    graph_clients,
    graph_mgr,
    ws_clients,
    ws_mgr,
)

if logger_module_available:
    pass  # imports satisfied above
else:
    def get_scheduler():  # type: ignore
        raise RuntimeError("scheduler unavailable")

    def get_security_manager():  # type: ignore
        raise RuntimeError("security unavailable")


def register(app):

    @app.websocket("/ws/agents")
    async def ws_agents(ws: WebSocket):
        """Streaming metrik systému — posílá JSON každé 2s."""
        await ws.accept()
        try:
            while True:
                cpu  = psutil.cpu_percent(interval=0.1)
                ram  = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                # CPU teplota
                cpu_temp = None
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for tname in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                            if tname in temps:
                                cpu_temp = round(temps[tname][0].current, 1)
                                break
                except Exception:
                    pass

                # Síťová aktivita
                net_recv = 0
                net_sent = 0
                try:
                    n1 = psutil.net_io_counters()
                    await asyncio.sleep(0.1)
                    n2 = psutil.net_io_counters()
                    net_recv = round((n2.bytes_recv - n1.bytes_recv) / 0.1 / 1024, 1)
                    net_sent = round((n2.bytes_sent - n1.bytes_sent) / 0.1 / 1024, 1)
                except Exception:
                    pass

                payload = {
                    "type": "metrics",
                    "cpu":  round(cpu, 1),
                    "ram":  round(ram.percent, 1),
                    "disk": round(disk.percent, 1),
                    "cpu_temp": cpu_temp,
                    "net_recv": net_recv,
                    "net_sent": net_sent,
                    "ts":   int(time.time() * 1000),
                }
                await ws.send_text(json.dumps(payload))
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws_agents uzavřen: {e}")


