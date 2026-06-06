"""Auto-migrated from dashboard.py — marketplace routes."""
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

    # ── Plugin Marketplace v2 API ─────────────────────────────────────────────

    @app.get("/api/marketplace")
    async def marketplace_catalog():
        """Katalog pluginů pro Marketplace UI."""
        try:
            from plugin_marketplace import PluginMarketplace
            mp = PluginMarketplace()
            return {"plugins": mp.get_catalog(), "updates": mp.check_updates()}
        except Exception as e:
            return {"plugins": [], "error": str(e)}

    @app.post("/api/marketplace/install/{name}")
    async def marketplace_install(name: str):
        try:
            from plugin_marketplace import PluginMarketplace
            import anyio
            mp = PluginMarketplace()
            result = await anyio.to_thread.run_sync(lambda: mp.install(name))
            return {"ok": True, "message": result}
        except ImportError:
            from plugin_marketplace import PluginMarketplace
            import asyncio
            mp = PluginMarketplace()
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: mp.install(name))
            return {"ok": True, "message": result}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    @app.delete("/api/marketplace/uninstall/{name}")
    async def marketplace_uninstall(name: str):
        try:
            from plugin_marketplace import PluginMarketplace
            mp = PluginMarketplace()
            result = mp.uninstall(name)
            return {"ok": True, "message": result}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    @app.post("/api/marketplace/update/{name}")
    async def marketplace_update(name: str):
        try:
            from plugin_marketplace import PluginMarketplace
            import asyncio
            mp = PluginMarketplace()
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: mp.update(name))
            return {"ok": True, "message": result}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    @app.post("/api/marketplace/review/{name}")
    async def marketplace_review(name: str, request: Request):
        try:
            from plugin_marketplace import PluginMarketplace
            data = await request.json()
            mp = PluginMarketplace()
            result = mp.submit_review(name, data.get("rating", 5), data.get("comment", ""))
            return {"ok": True, "message": result}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    @app.get("/api/marketplace/reviews/{name}")
    async def marketplace_reviews(name: str):
        try:
            from plugin_marketplace import PluginMarketplace
            mp = PluginMarketplace()
            return {"reviews": mp.get_reviews(name), "avg": mp.avg_rating(name)}
        except Exception as e:
            return {"reviews": [], "error": str(e)}

    @app.post("/api/marketplace/run/{name}")
    async def marketplace_run_sandboxed(name: str, request: Request):
        """Spustí plugin v sandboxu a vrátí stdout/stderr."""
        try:
            from plugin_marketplace import PluginMarketplace
            import asyncio
            data = await request.json() if request.headers.get("content-type") == "application/json" else {}
            mp   = PluginMarketplace()
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: mp.run_sandboxed(name, timeout=data.get("timeout", 30)))
            return result
        except Exception as e:
            return {"ok": False, "stderr": str(e)}

    @app.get("/api/plugins")
    async def list_plugins():
        """Seznam načtených pluginů s health statusem."""
        try:
            from plugin_system import create_plugin_manager
            from config import CONFIG
            pm = create_plugin_manager(CONFIG)
            pm.load_all_plugins()
            health   = pm.health_check()
            hmap     = {h["name"]: h for h in health}
            plugins  = pm.list_plugins()
            enriched = []
            for p in plugins:
                h = hmap.get(p["name"], {})
                enriched.append({
                    "name":        p["name"],
                    "version":     p.get("version", "1.0"),
                    "description": p.get("description", ""),
                    "status":      h.get("status", "unknown"),
                    "routes":      h.get("routes", 0),
                    "actions":     h.get("actions", 0),
                    "error":       h.get("error"),
                })
            return {
                "plugins": enriched,
                "total":   len(enriched),
                "healthy": sum(1 for h in health if h["status"] == "ok"),
            }
        except Exception as e:
            return {"plugins": [], "error": str(e)}


