"""Auto-migrated from dashboard.py — monitoring routes."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import psutil
from fastapi.responses import JSONResponse

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

    @app.get("/health")
    async def health():
        """Strukturovaný health check endpoint."""
        cpu  = psutil.cpu_percent(interval=0.1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime = round(time.time() - start_time)

        ollama_ok = False
        try:
            import requests as _r
            r = _r.get("http://localhost:11434/api/tags", timeout=1)
            ollama_ok = r.status_code == 200
        except Exception:
            pass

        status = "healthy" if ram.percent < 90 else "degraded"
        return JSONResponse({
            "status": status,
            "ok": True,                      # jednoduché pole pro frontend
            "ws": "running",                 # WebSocket server běží
            "uptime_s": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": __version__,
            "port": 8002,
            "checks": {
                "ollama": {"ok": ollama_ok},
                "cpu":    {"ok": cpu < 95, "value": round(cpu, 1)},
                "ram":    {"ok": ram.percent < 90, "value": round(ram.percent, 1)},
                "disk":   {"ok": disk.percent < 95, "value": round(disk.percent, 1)},
            },
            "logging": "loguru" if HAS_LOGURU else "stdlib",
        }, status_code=200 if status == "healthy" else 503)

    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/app", status_code=302)

    @app.get("/api/system")
    async def system_metrics():
        import psutil, asyncio
        cpu  = psutil.cpu_percent(interval=0.1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # CPU teplota
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    if name in temps:
                        cpu_temp = round(temps[name][0].current, 1)
                        break
        except Exception:
            pass

        # Síťová aktivita (bytes/s za poslední sekundu)
        net = {"sent": 0, "recv": 0}
        try:
            n1 = psutil.net_io_counters()
            await asyncio.sleep(0.1)
            n2 = psutil.net_io_counters()
            net = {
                "sent": round((n2.bytes_sent - n1.bytes_sent) / 0.1 / 1024, 1),  # KB/s
                "recv": round((n2.bytes_recv - n1.bytes_recv) / 0.1 / 1024, 1),
            }
        except Exception:
            pass

        # GPU usage (nvidia-smi nebo AMD)
        gpu = {"usage": None, "vram": None, "name": None}
        try:
            import subprocess
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,name",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split(", ")
                if len(parts) >= 3:
                    gpu["usage"] = int(parts[0])
                    used = int(parts[1])
                    total = int(parts[2])
                    gpu["vram"] = round(used / total * 100, 1) if total > 0 else None
                    gpu["name"] = parts[3].strip()[:30] if len(parts) > 3 else "NVIDIA GPU"
        except Exception:
            pass

        return {
            "cpu":      round(cpu, 1),
            "ram":      round(ram.percent, 1),
            "disk":     round(disk.percent, 1),
            "cpu_temp": cpu_temp,
            "net":      net,
            "gpu":      gpu,
            "ram_gb":   round(ram.used / 1024**3, 1),
            "ram_total": round(ram.total / 1024**3, 1),
        }

    @app.get("/api/status")
    async def status():
        """Returns basic runtime and feature availability status."""
        from config import CONFIG
        # Ollama status
        ollama_ok = False
        try:
            import requests as _r
            r = _r.get(CONFIG.get("ollama_url", "http://localhost:11434/api/chat").replace("/api/chat", "/api/tags"), timeout=2)
            ollama_ok = r.status_code == 200
        except Exception:
            ollama_ok = False

        # Feature-level capabilities (MVP notes)
        features = {
            "computer_use": {
                "enabled": bool(CONFIG.get("computer_use_enabled", False)),
                "backend": CONFIG.get("computer_use_backend", "auto"),
                "cross_platform": "partial (Linux-first)" if CONFIG.get("computer_use_backend", "auto") in ("auto", "linux_atspi") else "limited",
                "note": "Full cross-platform Computer Use currently focused on Linux (GNOME). Windows/macOS support partial or experimental.",
            },
            "audio_duplex": {
                "live_duplex_stt_tts": bool(CONFIG.get("audio_ws_enabled", False)),
                "note": "Live duplex STT/TTS streaming is experimental / opt-in and may require additional setup.",
            },
            "memory_graph": {
                "backend": CONFIG.get("graph_backend", "sqlite_mvp"),
                "note": "Graph memory is MVP using local SQLite (entities+relations). Enterprise graph DB adapters (Neo4j/Memgraph) planned.",
            },
            "mcp_auto_install": {
                "enabled": bool(CONFIG.get("mcp_auto_install_enabled", False)),
                "note": "MCP auto-install is disabled by default; current system only suggests servers and requires explicit user approval to install.",
            },
            "shadow_mode": {
                "enabled": bool(CONFIG.get("shadow_mode_enabled", False)),
                "level": CONFIG.get("shadow_mode_level", "suggestions"),
                "note": "Shadow Mode currently offers read-only suggestions (no automatic commits or CI self-healing unless 'autofix' is enabled and explicitly approved).",
            },
        }

        return {
            "ollama": ollama_ok,
            "model": CONFIG.get("ollama_model", "?"),
            "features": features,
        }

    @app.get("/api/agents")
    async def agents_status():
        result = {}
        try:
            from agents import AgentManager
            mgr = AgentManager.get_instance()
            if mgr:
                result = mgr.status()
        except Exception:
            pass
        if not result:
            # Fallback — zjisti alespoň co jsou to za procesy
            for name in ("cpu_monitor", "ram_monitor", "disk_monitor"):
                result[name] = {"running": logger_module_available, "interval": 30}
        return result

    @app.get("/api/scheduler")
    async def scheduler_tasks():
        if not logger_module_available:
            return []
        try:
            return get_scheduler().get_pending()
        except Exception:
            return []

    @app.get("/api/audit")
    async def audit_log(limit: int = 50):
        if not logger_module_available:
            return []
        n = max(1, min(int(limit or 50), 500))
        try:
            return get_security_manager().get_audit_log(n)
        except Exception:
            return []


