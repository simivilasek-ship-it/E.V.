"""
JARVIS — Web Dashboard
Lokální web UI pro monitoring, logy, historii, nastavení.
Spuštění: python dashboard.py  (port 8002)
"""

from __future__ import annotations
import asyncio
import json
import time
import threading
from datetime import datetime, timezone
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

import psutil

# Structured logging — loguru pokud dostupný, jinak stdlib logging
try:
    from loguru import logger as _loguru
    import logging

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
    import logging
    logger = logging.getLogger(__name__)
    HAS_LOGURU = False

logger_module_available = False
try:
    from event_bus import get_event_bus, EventType, Event
    from scheduler import get_scheduler
    from security_v2 import get_security_manager
    from agents import AgentManager
    from config import CONFIG, __version__
    logger_module_available = True
except ImportError:
    pass

_start_time = time.time()


from pathlib import Path
_TEMPLATE_DIR = Path(__file__).parent / "templates"
DASHBOARD_HTML = (_TEMPLATE_DIR / "dashboard.html").read_text(encoding="utf-8")


if HAS_FASTAPI:
    app = FastAPI(title="JARVIS Dashboard", docs_url=None, redoc_url=None)

    class ConnectionManager:
        """Thread-safe správce WebSocket spojení.
        Odstraňuje mrtvá spojení při každém broadcastu a při disconnect.
        """
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

    _ws_mgr    = ConnectionManager()   # logy
    _graph_mgr = ConnectionManager()   # graph events

    # zpětná kompatibilita — kód co přistupuje přímo přes _ws_clients / _graph_clients
    _ws_clients: set = set()
    _graph_clients: set = set()

    async def broadcast_graph_event(event: dict):
        """Broadcastuje graph event všem připojeným klientům."""
        dead = set()
        payload = json.dumps(event)
        for client in list(_graph_clients):
            try:
                await client.send_text(payload)
            except Exception:
                dead.add(client)
        _graph_clients.difference_update(dead)

    app.broadcast_graph_event = broadcast_graph_event

    _main_loop = None

    @app.on_event("startup")
    async def startup_event():
        global _main_loop
        _main_loop = asyncio.get_running_loop()
        try:
            from event_bus import get_event_bus
            
            def handle_bus_graph(event):
                if _main_loop and event.data:
                    asyncio.run_coroutine_threadsafe(
                        broadcast_graph_event(event.data),
                        _main_loop
                    )
            
            get_event_bus().subscribe("agent.graph", handle_bus_graph)
            logger.info("Dashboard: Odebírám 'agent.graph' eventy z EventBusu")
        except Exception as e:
            logger.warning(f"Dashboard: nelze se přihlásit k EventBusu: {e}")

    @app.get("/health")
    async def health():
        """Strukturovaný health check endpoint."""
        cpu  = psutil.cpu_percent(interval=0.1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime = round(time.time() - _start_time)

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

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return DASHBOARD_HTML

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
    async def audit_log():
        if not logger_module_available:
            return []
        try:
            return get_security_manager().get_audit_log(20)
        except Exception:
            return []

    # ── CORS pro React frontend na portu 3000 ────────
    try:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_methods=["*"], allow_headers=["*"])
    except Exception:
        pass

    @app.post("/api/notify")
    async def send_notification(body: dict):
        """Odešle desktop notifikaci přes libnotify."""
        from notification_engine import get_notification_engine
        ok = get_notification_engine().send(
            title=body.get("title", "JARVIS"),
            body=body.get("body", ""),
            urgent=body.get("urgent", False)
        )
        return {"ok": ok}

    @app.post("/api/command")
    async def run_command(body: dict):
        """Spustí příkaz přes JARVIS a vrátí odpověď."""
        cmd = body.get("command", "").strip()
        if not cmd:
            return {"error": "Prázdný příkaz"}
        try:
            from llm import LLMEngine, LocalRouter
            from config import CONFIG
            router = LocalRouter()
            msg, action = router.route(cmd)
            if action:
                from commands import CommandExecutor
                cmds = CommandExecutor(CONFIG)
                result = cmds.execute(action["action"], action.get("params", {}))
                return {"response": result or msg, "action": action["action"]}
            # Fallback — LLM
            llm = LLMEngine(CONFIG)
            resp, _ = llm.ask(cmd)
            return {"response": resp}
        except Exception as e:
            return {"response": f"Chyba: {e}", "error": str(e)}

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

    @app.get("/api/memory")
    async def memory_query(q: str = ""):
        """Dotaz do JARVIS paměti."""
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem = JarvisMemory(CONFIG)
            results = mem.recall(q, top_k=5) if q else []
            stats   = mem.stats()
            return {"results": results, "stats": stats}
        except Exception as e:
            return {"results": [], "error": str(e)}

    @app.get("/api/memory/graph")
    async def memory_graph():
        """Vrátí paměť jako force-directed graf (nodes + links)."""
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem   = JarvisMemory(CONFIG)
            items = mem.recall("", top_k=60, min_importance=0.0)

            nodes, links = [], []
            seen_ids = set()

            for item in items:
                nid  = str(item["id"])
                text = item["content"][:60] + ("…" if len(item["content"]) > 60 else "")
                imp  = item.get("importance", 0.5)
                tags = item.get("tags", [])
                nodes.append({
                    "id": nid, "label": text,
                    "full": item["content"][:200],
                    "importance": round(imp, 2), "tags": tags,
                    "group": tags[0] if tags else "memory",
                    "ts": item.get("created_at", 0),
                })
                seen_ids.add(nid)

            # Hrany: 1) sdílený tag, 2) překrývající slova, 3) časová blízkost
            node_list = list(nodes)
            for i, a in enumerate(node_list):
                for b in node_list[i+1:]:
                    label = None
                    # 1. Sdílený tag
                    common_tags = set(a["tags"]) & set(b["tags"])
                    if common_tags:
                        label = list(common_tags)[0]
                    else:
                        # 2. Sdílená klíčová slova (3+ znaky, mimo stop-slova)
                        stop = {"the","and","for","that","this","jsou","bylo","není","nebo"}
                        wa = {w for w in a["full"].lower().split() if len(w) > 3 and w not in stop}
                        wb = {w for w in b["full"].lower().split() if len(w) > 3 and w not in stop}
                        common_words = wa & wb
                        if len(common_words) >= 2:
                            label = list(common_words)[0]
                        # 3. Časová blízkost (< 60 minut)
                        elif a["ts"] and b["ts"] and abs(a["ts"] - b["ts"]) < 3600:
                            label = "časově blízké"
                    if label:
                        links.append({"source": a["id"], "target": b["id"], "label": label})
                        if len(links) >= 120:
                            break
                if len(links) >= 120:
                    break

            # Integrate GraphStore (entities + relations) if available
            try:
                if getattr(mem, 'graph_store', None):
                    try:
                        gd = mem.graph_store.dump()
                        # merge graph nodes (prefix with 'g-' to avoid id collision)
                        for n in gd.get('nodes', []):
                            nid = 'g-' + str(n.get('id'))
                            if nid not in seen_ids:
                                nodes.append({
                                    'id': nid,
                                    'label': n.get('label') or n.get('name'),
                                    'full': n.get('label') or n.get('name'),
                                    'importance': n.get('importance', 0.5),
                                    'tags': [],
                                    'group': n.get('group', 'entity'),
                                    'ts': 0,
                                })
                                seen_ids.add(nid)
                        for l in gd.get('links', []):
                            links.append({'source': 'g-' + str(l.get('source')), 'target': 'g-' + str(l.get('target')), 'label': l.get('label')})
                    except Exception:
                        pass
            except Exception:
                pass

            # Limit s total_count
            total = len(nodes)
            result = {"nodes": nodes[:80], "links": links[:120], "total": total}
            try:
                from config import CONFIG
                if CONFIG.get('memory_graph_timeline', True):
                    # timeline: recent relation events (ts, subject, predicate, object)
                    timeline = []
                    for l in links:
                        if l.get('ts'):
                            timeline.append({
                                'ts': l.get('ts'),
                                'subject_id': l.get('source'),
                                'object_id': l.get('target'),
                                'predicate': l.get('label'),
                                'source': l.get('source_meta'),
                                'confidence': l.get('confidence'),
                            })
                    timeline.sort(key=lambda x: x['ts'], reverse=True)
                    result['timeline'] = timeline[:80]
            except Exception:
                pass
            return result
        except Exception as e:
            return {"nodes": [], "links": [], "error": str(e)}

    @app.get("/api/profile")
    async def get_profile():
        """Vrátí základní user profile pro Hero panel (jméno, fakta)."""
        try:
            from user_profile import get_user_profile
            from config import CONFIG, __version__
            profile = get_user_profile()
            name  = profile.get("jméno") or profile.get("name") or ""
            facts = {f.key: f.value for f in profile.all_facts()} if hasattr(profile, "all_facts") else {}
            model = CONFIG.get("ollama_model", "?")
            return {
                "name":    name,
                "facts":   facts,
                "model":   model,
                "version": __version__,
            }
        except Exception:
            return {"name": "", "facts": {}, "model": "?", "version": "4.5"}

    @app.get("/api/config")
    async def get_config():
        """Vrátí aktuální konfiguraci (bez secrets)."""
        try:
            from config import CONFIG
            safe = {k: v for k, v in CONFIG.items()
                    if k not in ("brave_api_key",) and "key" not in k.lower()}
            return safe
        except Exception:
            return {}

    @app.get("/api/debug/bundle")
    async def debug_bundle(limit_log_lines: int = 400):
        """Vytvoří ZIP bundle pro bugreport (bez secrets)."""
        import io, json, os, platform, zipfile, time
        from pathlib import Path as _Path
        from fastapi.responses import StreamingResponse

        limit = max(50, min(int(limit_log_lines or 400), 2000))
        root = _Path(__file__).parent

        # Safe config
        try:
            from config import CONFIG, __version__
            safe_config = {k: v for k, v in CONFIG.items()
                           if k not in ("brave_api_key",) and "key" not in k.lower()}
        except Exception:
            __version__ = "unknown"
            safe_config = {}

        meta = {
            "timestamp": int(time.time()),
            "version": __version__,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "env": {
                "JARVIS_HEADLESS": os.getenv("JARVIS_HEADLESS", ""),
                "AUTO_RELOAD": os.getenv("AUTO_RELOAD", ""),
                "DEBUG_MODE": os.getenv("DEBUG_MODE", ""),
            },
        }

        def _tail_text(path: _Path) -> str:
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[-limit:])
            except Exception:
                return ""

        # Collect logs if present (never include .env)
        log_text = _tail_text(root / "jarvis.log")
        audit_text = _tail_text(root / "audit.log")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.writestr("config.safe.json", json.dumps(safe_config, ensure_ascii=False, indent=2))
            if log_text:
                zf.writestr("jarvis.log.tail.txt", log_text)
            if audit_text:
                zf.writestr("audit.log.tail.txt", audit_text)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=jarvis-debug-bundle.zip"},
        )

    @app.post("/api/config")
    async def update_config(body: dict):
        """Aktualizuje konfiguraci za běhu (whitelist bezpečných klíčů)."""
        ALLOWED = {
            # LLM
            "ollama_model", "history_size",
            # TTS
            "tts_enabled", "tts_voice", "tts_rate", "tts_streaming",
            # STT
            "stt_language", "stt_energy_threshold", "stt_timeout", "stt_phrase_limit",
            # Wake word
            "wake_word", "wake_word_enabled",
            # Agent
            "agent_max_steps", "agent_timeout",
            # MCP toggles
            "mcp_filesystem_enabled", "mcp_git_enabled", "mcp_memory_enabled",
            "mcp_fetch_enabled", "mcp_brave_enabled", "mcp_playwright_enabled",
            "mcp_github_enabled", "mcp_youtube_transcript_enabled",
            "mcp_google_maps_enabled", "mcp_slack_enabled",
            "mcp_sequential_thinking_enabled", "mcp_puppeteer_enabled",
            "mcp_computer_control_enabled", "mcp_time_enabled",
        }
        try:
            from config import CONFIG, save_config
            changed = {}
            for k, v in body.items():
                if k in ALLOWED:
                    CONFIG[k] = v
                    changed[k] = v
            if changed:
                save_config(CONFIG)
            return {"updated": changed, "ok": True}
        except Exception as e:
            return {"error": str(e), "ok": False}

    # ── Workflow Builder ──────────────────────────────
    @app.get("/api/workflows")
    async def list_workflows():
        from workflow_engine import get_workflow_engine
        return {"workflows": get_workflow_engine().list_all()}

    @app.post("/api/workflows")
    async def create_workflow(body: dict):
        import uuid
        from workflow_engine import get_workflow_engine, Workflow
        wf = Workflow(
            id=str(uuid.uuid4())[:8],
            name=body.get("name", "Nový workflow"),
            trigger_type=body.get("trigger_type", "manual"),
            trigger_config=body.get("trigger_config", {}),
            action=body.get("action", ""),
            cooldown_seconds=body.get("cooldown_seconds", 300),
        )
        get_workflow_engine().add(wf)
        return {"id": wf.id, "ok": True}

    @app.delete("/api/workflows/{workflow_id}")
    async def delete_workflow(workflow_id: str):
        from workflow_engine import get_workflow_engine
        ok = get_workflow_engine().remove(workflow_id)
        return {"ok": ok}

    # ── Mission Manager API ───────────────────────────

    @app.get("/api/missions")
    async def list_missions():
        try:
            from mission_manager import get_mission_manager
            return {"missions": get_mission_manager().list_missions()}
        except Exception as e:
            return {"missions": [], "error": str(e)}

    @app.post("/api/missions")
    async def create_mission(request: Request):
        try:
            from mission_manager import get_mission_manager
            import asyncio
            data = await request.json()
            mgr  = get_mission_manager()
            mission = await asyncio.get_event_loop().run_in_executor(
                None, lambda: mgr.create_mission(
                    data["title"], data.get("description", ""),
                    data.get("deadline")))
            return {"ok": True, "mission": mission}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/pause")
    async def pause_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().pause_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.put("/api/missions/{mission_id}/resume")
    async def resume_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().resume_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.delete("/api/missions/{mission_id}")
    async def delete_mission(mission_id: str):
        try:
            from mission_manager import get_mission_manager
            get_mission_manager().delete_mission(mission_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Vision v2 API ─────────────────────────────────

    @app.get("/api/vision/analyze")
    async def vision_analyze():
        """Pořídí screenshot, spustí OCR+UI analýzu, vrátí JSON."""
        try:
            from vision_v2 import VisionOCRPipeline
            import asyncio
            pipeline = VisionOCRPipeline()
            if not pipeline.available:
                return {"error": "OCR pipeline nedostupná (pip install pytesseract opencv-python)"}
            result = await asyncio.get_event_loop().run_in_executor(
                None, pipeline.analyze)
            return {
                "ocr_text":        result.ocr_text,
                "active_app":      result.active_app,
                "ui_elements":     [{"role": e.role, "name": e.name, "x": e.bbox[0], "y": e.bbox[1]} for e in result.ui_elements],
                "clickable_count": len(result.clickable_regions),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Agent Timeline ────────────────────────────────
    # ── Agent Timeline — SQLite persistence ──────────
    import sqlite3 as _sqlite3
    from pathlib import Path as _TLPath

    _TL_DB = _TLPath(__file__).parent / "memory_data" / "agent_runs.db"
    _TL_DB.parent.mkdir(parents=True, exist_ok=True)

    def _tl_init():
        with _sqlite3.connect(_TL_DB) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id       TEXT PRIMARY KEY,
                    task     TEXT,
                    steps    TEXT,
                    result   TEXT,
                    status   TEXT,
                    duration REAL,
                    ts       REAL
                )
            """)
    _tl_init()

    def _tl_save(run: dict):
        import json as _j, time as _t
        with _sqlite3.connect(_TL_DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO agent_runs VALUES (?,?,?,?,?,?,?)",
                (run.get("id", str(_t.time())),
                 run.get("task", ""),
                 _j.dumps(run.get("steps", []), ensure_ascii=False),
                 run.get("result", ""),
                 run.get("status", "done"),
                 run.get("duration", 0),
                 _t.time()))

    @app.get("/api/agent/timeline")
    async def agent_timeline(limit: int = 30):
        import json as _j
        try:
            with _sqlite3.connect(_TL_DB) as con:
                con.row_factory = _sqlite3.Row
                rows = con.execute(
                    "SELECT * FROM agent_runs ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
            runs = [{
                "id": r["id"], "task": r["task"],
                "steps": _j.loads(r["steps"]),
                "result": r["result"], "status": r["status"],
                "duration": r["duration"], "ts": r["ts"],
            } for r in rows]
            return {"runs": runs, "total": len(runs)}
        except Exception as e:
            return {"runs": [], "error": str(e)}

    @app.post("/api/agent/timeline")
    async def agent_timeline_save(body: dict):
        """Uloží agentský run do SQLite."""
        try:
            _tl_save(body)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Skill Generator ───────────────────────────────

    @app.post("/api/skill/generate")
    async def skill_generate(body: dict):
        """Vygeneruje plugin skeleton z přirozeného popisu."""
        prompt = body.get("prompt", "").strip()
        if not prompt:
            return {"error": "Prázdný prompt"}
        try:
            from llm import OllamaClient
            from config import CONFIG
            client = OllamaClient(CONFIG["ollama_url"], CONFIG["ollama_model"])

            system = """\
Jsi expert na tvorbu JARVIS pluginů. Vygeneruj funkční plugin pro zadaný účel.

Plugin se skládá ze dvou souborů:
1. skill.py — Python kód
2. manifest.json — metadata

FORMÁT ODPOVĚDI (jen JSON, nic jiného):
{
  "name": "nazev_pluginu",
  "description": "Co plugin dělá",
  "triggers": ["klíčové slovo 1", "klíčové slovo 2"],
  "permissions": ["answer"],
  "skill_py": "import re\\n...celý kód skill.py...",
  "manifest": {"name":"...","version":"1.0.0","description":"...","permissions":["answer"],"triggers":["..."]}
}

Pravidla pro skill.py:
- Importuj jen povolené moduly (requests, json, re, datetime, math, collections…)
- Definuj _PATTERN = re.compile(r"\\b(trigger)\\b", re.IGNORECASE)
- Definuj _handle(text: str) -> tuple[str, dict]
- Vrať (zpráva, {"action": "answer", "params": {}})
- def get_routes(): return [{"pattern": _PATTERN, "handler": _handle}]
- def get_actions(): return {}
"""
            result = client.call_json(
                [{"role": "system", "content": system},
                 {"role": "user", "content": f"Vytvoř plugin: {prompt}"}],
                temperature=0.3, max_tokens=1200,
            )
            if not result or "skill_py" not in result:
                return {"error": "LLM nevrátil validní JSON — zkus znovu nebo uprosti prompt"}
            # Validace syntaxe vygenerovaného kódu
            import ast as _ast
            try:
                _ast.parse(result["skill_py"])
            except SyntaxError as se:
                return {
                    "error": f"Syntaktická chyba v generovaném kódu (řádek {se.lineno}): {se.msg}",
                    "hint": "Zkus prompt přeformulovat nebo zjednodušit",
                    "raw": result,
                }
            # Ověř přítomnost povinných funkcí
            tree = _ast.parse(result["skill_py"])
            fns = {n.name for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef)}
            missing = {"get_routes", "get_actions"} - fns
            if missing:
                result["warning"] = f"Chybí funkce: {', '.join(missing)} — plugin nemusí fungovat"
            return result
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/skill/save")
    async def skill_save(body: dict):
        """Uloží vygenerovaný plugin do plugins/custom/."""
        import re as _re
        name       = body.get("name", "").strip().replace(" ", "_").lower()
        skill_code = body.get("skill_code", "")
        manifest   = body.get("manifest", {})
        if not name or not skill_code:
            return {"error": "Chybí name nebo skill_code"}
        if not _re.fullmatch(r"[a-z0-9_\\-]{1,64}", name):
            return {"error": "Neplatný název pluginu (povoleno: a-z, 0-9, _, -; max 64 znaků)"}
        try:
            from pathlib import Path as _Path
            root = _Path(__file__).parent
            base = (root / "plugins" / "custom").resolve()
            dest = (base / name).resolve()
            if base not in dest.parents:
                return {"error": "Neplatná cesta pro plugin (path traversal blocked)"}
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "skill.py").write_text(skill_code, encoding="utf-8")
            import json as _json
            if manifest:
                (dest / "manifest.json").write_text(
                    _json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"saved": str(dest), "name": name}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/skill/download/{name}")
    async def skill_download(name: str):
        """Stáhne plugin jako ZIP archiv."""
        import re as _re
        if not _re.fullmatch(r"[a-z0-9_\\-]{1,64}", name):
            from fastapi import HTTPException
            raise HTTPException(400, "Neplatný název pluginu")
        import zipfile, io
        from fastapi.responses import StreamingResponse
        from pathlib import Path as _Path
        dest = _Path(__file__).parent / "plugins" / "custom" / name
        if not dest.exists():
            from fastapi import HTTPException
            raise HTTPException(404, f"Plugin '{name}' nenalezen")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in dest.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(dest.parent))
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={name}.zip"},
        )

    @app.post("/api/agent/parallel")
    async def agent_parallel(body: dict):
        """Spustí MultiAgentOrchestrator v paralelním režimu.

        Body: {"task": "...", "max_steps": 5}
        Vrátí výsledky kroků s časováním.
        """
        task = body.get("task", "").strip()
        if not task:
            return {"error": "Chybí task"}
        max_steps = min(int(body.get("max_steps", 5)), 8)
        try:
            from config import CONFIG
            from commands import CommandExecutor
            from agent_roles import MultiAgentOrchestrator
            url   = CONFIG.get("ollama_url",   "http://localhost:11434/api/chat")
            model = CONFIG.get("ollama_model", "qwen2.5:3b")
            orch  = MultiAgentOrchestrator(url, model, executor=CommandExecutor(CONFIG))
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: orch.run_parallel(task, max_steps=max_steps))
            return {"result": result, "task": task}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/chat")
    async def chat_rest(body: dict):
        """REST fallback pro chat — vrátí celou odpověď najednou."""
        text = body.get("text", "").strip()
        if not text:
            return {"response": "Prázdná zpráva"}
        try:
            from local_router import LocalRouter
            from config import CONFIG
            msg, action = LocalRouter().route(text)
            if action and action.get("action") not in ("answer", None):
                from commands import CommandExecutor
                result = CommandExecutor(CONFIG).execute(action["action"], action.get("params", {}))
                return {"response": result or msg or "Hotovo."}
            from llm import LLMEngine
            resp, _ = LLMEngine(CONFIG).ask(text)
            return {"response": resp}
        except Exception as e:
            return {"response": f"Chyba: {e}"}

    @app.websocket("/ws/chat")
    async def ws_chat(ws: WebSocket):
        """WebSocket chat — streaming odpovědi chunk po chunku."""
        await ws.accept()

        async def send(obj: dict):
            try:
                await ws.send_text(json.dumps(obj))
            except Exception:
                pass

        try:
            while True:
                raw  = await ws.receive_text()
                data = json.loads(raw)
                text = (data.get("command") or data.get("text") or "").strip()
                if not text:
                    continue

                try:
                    from llm import LocalRouter, LLMEngine
                    from config import CONFIG

                    # LocalRouter je rychlý (regex) — OK synchronně
                    msg, action = LocalRouter().route(text)

                    if action and action.get("action") not in ("answer", None):
                        # Blokující OS příkaz → thread aby neblokoval event loop
                        from commands import CommandExecutor
                        def _run_cmd():
                            return CommandExecutor(CONFIG).execute(
                                action["action"], action.get("params", {}))
                        try:
                            import anyio
                            result = await anyio.to_thread.run_sync(_run_cmd)
                        except ImportError:
                            result = await asyncio.get_event_loop().run_in_executor(
                                None, _run_cmd)
                        reply = result or msg or "Hotovo."
                        await send({"type": "chunk", "data": reply})
                        await send({"type": "done"})
                    else:
                        # stream_ask je synchronní generátor — spusť v threadu,
                        # výsledky přeposílej přes asyncio.Queue do event loopu
                        llm    = LLMEngine(CONFIG)
                        q: asyncio.Queue = asyncio.Queue()

                        def _stream():
                            try:
                                for chunk in llm.stream_ask(text):
                                    if isinstance(chunk, str) and chunk:
                                        asyncio.run_coroutine_threadsafe(
                                            q.put(chunk), asyncio.get_event_loop())
                            finally:
                                asyncio.run_coroutine_threadsafe(
                                    q.put(None), asyncio.get_event_loop())

                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(None, _stream)

                        while True:
                            chunk = await q.get()
                            if chunk is None:
                                break
                            await send({"type": "chunk", "data": chunk})
                            await asyncio.sleep(0)
                        await send({"type": "done"})

                except Exception as e:
                    logger.error(f"ws_chat chyba: {e}")
                    await send({"type": "error", "data": str(e)})

        except WebSocketDisconnect:
            await _ws_mgr.disconnect(ws)
        except Exception as e:
            logger.warning(f"ws_chat uzavřen: {e}")
            await _ws_mgr.disconnect(ws)

    @app.websocket("/ws/logs")
    async def ws_logs(ws: WebSocket):
        """Live logy přes WebSocket — posílá JSON {level, message, ts}."""
        await _ws_mgr.connect(ws)
        _ws_clients.add(ws)   # zpětná kompatibilita pro broadcast_log
        try:
            while True:
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await _ws_mgr.disconnect(ws)
            _ws_clients.discard(ws)

    @app.websocket("/ws/audio")
    async def ws_audio(ws: WebSocket):
        """Duplex audio websocket (MVP).

        Client sends raw PCM16 mono frames (default 16kHz). Server runs VAD and emits
        EventType.AUDIO_SPEECH on detected speech (for barge-in interruption).

        This endpoint is intentionally minimal: it does not perform STT yet.
        """
        await ws.accept()

        try:
            from config import CONFIG
            if not bool(CONFIG.get("audio_ws_enabled", False)):
                await ws.send_text(json.dumps({"type": "error", "data": "audio_ws_enabled is false"}))
                await ws.close()
                return
        except Exception:
            pass

        vad = None
        try:
            from vad import get_vad
            from config import CONFIG
            if bool(CONFIG.get("vad_enabled", True)):
                vad = get_vad(CONFIG)
        except Exception:
            vad = None

        # lazy bus import
        bus = None
        try:
            from event_bus import get_event_bus, EventType
            bus = get_event_bus()
        except Exception:
            bus = None

        try:
            while True:
                frame = await ws.receive_bytes()
                if not frame:
                    continue
                # Debug: optionally broadcast audio frames (off by default)
                try:
                    if bus and False:
                        bus.emit(EventType.AUDIO_FRAME, {"n": len(frame)}, source="ws_audio")
                except Exception:
                    pass

                speech = False
                try:
                    if vad is not None:
                        speech = vad.is_speech(frame)
                except Exception:
                    speech = False

                if speech:
                    # emit event for barge-in
                    try:
                        if bus:
                            bus.emit(EventType.AUDIO_SPEECH, {"ts": time.time()}, source="ws_audio")
                    except Exception:
                        pass
                    # send ack to client
                    try:
                        await ws.send_text(json.dumps({"type": "vad", "speech": True}))
                    except Exception:
                        pass

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"ws_audio closed: {e}")

    @app.websocket("/ws/graph")
    async def ws_graph(ws: WebSocket):
        """Streaming stavu Graf agenta — posílá JSON eventi."""
        import json as _json
        await _graph_mgr.connect(ws)
        _graph_clients.add(ws)   # zpětná kompatibilita
        try:
            await ws.send_text(_json.dumps({"type": "ready", "status": "idle"}))
            while True:
                await asyncio.sleep(20)
                await ws.send_text(_json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await _graph_mgr.disconnect(ws)
            _graph_clients.discard(ws)

    @app.get("/api/models")
    async def list_models():
        """Vrátí dostupné Ollama modely."""
        try:
            import requests as _r
            from config import CONFIG
            base = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            r = _r.get(base.replace("/api/chat", "/api/tags"), timeout=4)
            if r.status_code == 200:
                return {"models": [m["name"] for m in r.json().get("models", [])]}
        except Exception:
            pass
        return {"models": []}

    @app.get("/api/settings")
    async def get_settings():
        """Vrátí aktuální nastavení + metadata (min/max/options) pro Settings UI."""
        import shutil as _shutil
        try:
            from config import CONFIG
        except ImportError:
            return {"error": "config modul není dostupný"}

        # Dostupné Ollama modely
        available_models: list = []
        try:
            import requests as _r
            base = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            r = _r.get(base.replace("/api/chat", "/api/tags"), timeout=3)
            if r.status_code == 200:
                available_models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass

        # MCP servery — statická tabulka (command + config key)
        _MCP_SERVERS = [
            ("filesystem",           "npx",  "mcp_filesystem_enabled"),
            ("git",                  "uvx",  "mcp_git_enabled"),
            ("mcp-memory",           "npx",  "mcp_memory_enabled"),
            ("fetch",                "uvx",  "mcp_fetch_enabled"),
            ("brave-search",         "npx",  "mcp_brave_enabled"),
            ("playwright",           "npx",  "mcp_playwright_enabled"),
            ("github",               "npx",  "mcp_github_enabled"),
            ("youtube-transcript",   "npx",  "mcp_youtube_transcript_enabled"),
            ("google-maps",          "npx",  "mcp_google_maps_enabled"),
            ("slack",                "npx",  "mcp_slack_enabled"),
            ("sequential-thinking",  "npx",  "mcp_sequential_thinking_enabled"),
            ("puppeteer",            "npx",  "mcp_puppeteer_enabled"),
            ("computer-control",     "uvx",  "mcp_computer_control_enabled"),
            ("time",                 "uvx",  "mcp_time_enabled"),
        ]
        mcp_status_map = {}
        for srv_name, cmd, cfg_key in _MCP_SERVERS:
            mcp_status_map[srv_name] = {
                "enabled": bool(CONFIG.get(cfg_key, True)),
                "command_found": _shutil.which(cmd) is not None,
            }

        return {
            "llm": {
                "model":            CONFIG.get("ollama_model", ""),
                "available_models": available_models,
                "history_size":     CONFIG.get("history_size", 20),
            },
            "tts": {
                "enabled":   CONFIG.get("tts_enabled", True),
                "voice":     CONFIG.get("tts_voice", ""),
                "rate":      CONFIG.get("tts_rate", "+0%"),
                "streaming": CONFIG.get("tts_streaming", True),
            },
            "stt": {
                "language":         CONFIG.get("stt_language", "cs-CZ"),
                "energy_threshold": CONFIG.get("stt_energy_threshold", 300),
                "timeout":          CONFIG.get("stt_timeout", 5),
                "phrase_limit":     CONFIG.get("stt_phrase_limit", 10),
            },
            "wake_word": {
                "enabled": CONFIG.get("wake_word_enabled", True),
                "word":    CONFIG.get("wake_word", "jarvis"),
            },
            "agent": {
                "max_steps": CONFIG.get("agent_max_steps", 10),
                "timeout":   CONFIG.get("agent_timeout", 60),
            },
            "mcp": mcp_status_map,
        }

    @app.get("/api/tts/voices")
    async def list_tts_voices():
        """Seznam dostupných edge-tts hlasů (filtrovano na cs-CZ + en-US/en-GB)."""
        import subprocess as _sub
        voices: list = []
        try:
            r = _sub.run(
                ["edge-tts", "--list-voices"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if not line or line.startswith("Name"):
                        continue
                    # Formát: "Name: cs-CZ-AntoninNeural, Gender: Male, Locale: cs-CZ"
                    # nebo tabulátorem oddělené sloupce
                    parts = [p.strip() for p in line.replace(",", "\t").split("\t") if p.strip()]
                    name = locale = gender = ""
                    for p in parts:
                        if p.startswith("Name:"):
                            name = p.split(":", 1)[1].strip()
                        elif p.startswith("Gender:"):
                            gender = p.split(":", 1)[1].strip()
                        elif p.startswith("Locale:"):
                            locale = p.split(":", 1)[1].strip()
                    # Fallback: první část jako name pokud parsování selhalo
                    if not name and parts:
                        name = parts[0]
                    if not locale:
                        # Odhadni z name (cs-CZ-AntoninNeural → cs-CZ)
                        segments = name.split("-")
                        if len(segments) >= 2:
                            locale = "-".join(segments[:2])
                    # Filtr: cs-CZ nebo en-US nebo en-GB
                    if locale in ("cs-CZ", "en-US", "en-GB"):
                        voices.append({"name": name, "locale": locale, "gender": gender})
        except FileNotFoundError:
            return {"voices": [], "error": "edge-tts není nainstalován (pip install edge-tts)"}
        except Exception as e:
            return {"voices": [], "error": str(e)}
        return {"voices": voices}

    @app.get("/api/mcp/status")
    async def mcp_status():
        """Status všech MCP serverů: name, enabled, command_found."""
        import shutil as _shutil
        try:
            from config import CONFIG
        except ImportError:
            return {"servers": [], "error": "config modul není dostupný"}

        _MCP_SERVERS = [
            ("filesystem",           "npx",  "mcp_filesystem_enabled"),
            ("git",                  "uvx",  "mcp_git_enabled"),
            ("mcp-memory",           "npx",  "mcp_memory_enabled"),
            ("fetch",                "uvx",  "mcp_fetch_enabled"),
            ("brave-search",         "npx",  "mcp_brave_enabled"),
            ("playwright",           "npx",  "mcp_playwright_enabled"),
            ("github",               "npx",  "mcp_github_enabled"),
            ("youtube-transcript",   "npx",  "mcp_youtube_transcript_enabled"),
            ("google-maps",          "npx",  "mcp_google_maps_enabled"),
            ("slack",                "npx",  "mcp_slack_enabled"),
            ("sequential-thinking",  "npx",  "mcp_sequential_thinking_enabled"),
            ("puppeteer",            "npx",  "mcp_puppeteer_enabled"),
            ("computer-control",     "uvx",  "mcp_computer_control_enabled"),
            ("time",                 "uvx",  "mcp_time_enabled"),
        ]
        servers = []
        for srv_name, cmd, cfg_key in _MCP_SERVERS:
            servers.append({
                "name":          srv_name,
                "enabled":       bool(CONFIG.get(cfg_key, True)),
                "command_found": _shutil.which(cmd) is not None,
                "config_key":    cfg_key,
            })
        return {"servers": servers}

    @app.post("/api/mcp/toggle")
    async def mcp_toggle(body: dict):
        """Zapne/vypne MCP server: {server: "github", enabled: true}."""
        _CONFIG_KEY_MAP = {
            "filesystem":          "mcp_filesystem_enabled",
            "git":                 "mcp_git_enabled",
            "mcp-memory":          "mcp_memory_enabled",
            "fetch":               "mcp_fetch_enabled",
            "brave-search":        "mcp_brave_enabled",
            "playwright":          "mcp_playwright_enabled",
            "github":              "mcp_github_enabled",
            "youtube-transcript":  "mcp_youtube_transcript_enabled",
            "google-maps":         "mcp_google_maps_enabled",
            "slack":               "mcp_slack_enabled",
            "sequential-thinking": "mcp_sequential_thinking_enabled",
            "puppeteer":           "mcp_puppeteer_enabled",
            "computer-control":    "mcp_computer_control_enabled",
            "time":                "mcp_time_enabled",
        }
        server  = body.get("server", "").strip()
        enabled = body.get("enabled")
        if not server:
            return {"ok": False, "error": "Chybí pole 'server'"}
        if enabled is None:
            return {"ok": False, "error": "Chybí pole 'enabled'"}
        cfg_key = _CONFIG_KEY_MAP.get(server)
        if not cfg_key:
            return {"ok": False, "error": f"Neznámý MCP server: '{server}'"}
        try:
            from config import CONFIG, save_config
            CONFIG[cfg_key] = bool(enabled)
            save_config(CONFIG)
            return {"ok": True, "server": server, "enabled": bool(enabled), "config_key": cfg_key}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.post("/api/vision")
    async def vision_query(body: dict):
        """Popis obrázku pomocí multimodálního LLM (llava)."""
        from pathlib import Path as _Path
        prompt     = body.get("prompt", "Popiš obrázek.")
        image_path = body.get("image_path", "")
        model      = body.get("model", "llava:7b")
        if not _Path(image_path).exists():
            return {"error": f"Soubor nenalezen: {image_path}"}
        try:
            from llm import ask_vision
            from config import CONFIG
            url    = CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
            answer = ask_vision(prompt, image_path, model, url)
            return {"answer": answer}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/graph/state")
    async def graph_state():
        """Vrátí aktuální stav graf agenta."""
        return {
            "nodes": ["planner", "router", "executor", "critic"],
            "edges": [
                {"from": "planner", "to": "router"},
                {"from": "router", "to": "executor"},
                {"from": "executor", "to": "critic"},
                {"from": "critic", "to": "router"},
                {"from": "critic", "to": "done"},
            ],
            "active_node": None,
            "status": "idle",
        }

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

    # ── Broadcast helper (voláno z app_core) ──────────
    async def _broadcast_log(message: str, level: str = "info"):
        dead = set()
        payload = json.dumps({"type":"log","level":level,"message":message,"ts":int(time.time()*1000)})
        for client in list(_ws_clients):
            try:
                await client.send_text(payload)
            except Exception:
                dead.add(client)
        _ws_clients.difference_update(dead)

    app.broadcast_log = _broadcast_log


def _mount_web_app():
    """Připojí React build jako statické soubory na /app."""
    if not HAS_FASTAPI:
        return
    from pathlib import Path as _Path
    web_dist = _Path(__file__).parent / "web_dist"
    if not web_dist.exists():
        return
    try:
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        # Statické soubory (JS, CSS, ikony)
        app.mount("/app/assets", StaticFiles(directory=str(web_dist / "assets")),
                  name="web_assets")

        # Všechny ostatní cesty pod /app → index.html (SPA fallback)
        @app.get("/app/{full_path:path}", include_in_schema=False)
        async def web_app(full_path: str):
            return FileResponse(str(web_dist / "index.html"))

        @app.get("/app", include_in_schema=False)
        async def web_app_root():
            return FileResponse(str(web_dist / "index.html"))

    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"Web app mount selhal: {e}")


# Připoj React web app při importu
if HAS_FASTAPI:
    _mount_web_app()


def run_dashboard(port: int = 8002):
    if not HAS_FASTAPI:
        print("FastAPI není nainstalováno: pip install fastapi uvicorn")
        return
    print(f"JARVIS Web Chat  → http://localhost:{port}/app")
    print(f"JARVIS Dashboard → http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


# Alias pro jarvis.py --dashboard
run = run_dashboard


def run_dashboard_background(port: int = 8002):
    t = threading.Thread(target=run_dashboard, kwargs={"port": port}, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    run_dashboard()
