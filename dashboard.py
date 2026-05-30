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
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    from config import CONFIG
    logger_module_available = True
except ImportError:
    pass

_start_time = time.time()


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Courier New', monospace; background: #070b12;
         color: #e2f0ff; }
  .nav { background: #0b1220; border-bottom: 1px solid #1a3050;
         padding: 12px 24px; display: flex; gap: 20px; align-items: center; }
  .nav h1 { color: #00d4ff; font-size: 16px; letter-spacing: 4px; margin-right: 20px; }
  .nav a { color: #7ea8d4; text-decoration: none; font-size: 12px;
           padding: 4px 10px; border-radius: 4px; border: 1px solid #1a3050; }
  .nav a:hover, .nav a.active { color: #00d4ff; border-color: #00d4ff; }
  .container { padding: 20px; max-width: 1200px; margin: 0 auto; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 16px; margin-bottom: 20px; }
  .card { background: #0b1220; border: 1px solid #1a3050; border-radius: 8px;
          padding: 16px; }
  .card h3 { color: #7ea8d4; font-size: 10px; letter-spacing: 2px;
             margin-bottom: 10px; }
  .metric { font-size: 28px; color: #00d4ff; font-weight: bold; }
  .metric-sub { font-size: 11px; color: #475569; margin-top: 4px; }
  .bar { height: 4px; background: #1a3050; border-radius: 2px; margin-top: 8px; }
  .bar-fill { height: 100%; border-radius: 2px; background: #00d4ff;
              transition: width 0.5s; }
  .bar-fill.warn { background: #fbbf24; }
  .bar-fill.danger { background: #ef4444; }
  .log-box { background: #050a15; border: 1px solid #1a3050; border-radius: 6px;
             padding: 12px; height: 300px; overflow-y: auto; font-size: 11px;
             line-height: 1.6; }
  .log-line { padding: 2px 0; border-bottom: 1px solid #0b1220; }
  .log-line.error { color: #ef4444; }
  .log-line.warn { color: #fbbf24; }
  .log-line.ok { color: #10b981; }
  .log-line.info { color: #7ea8d4; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { color: #475569; font-size: 10px; letter-spacing: 1px; text-align: left;
       padding: 6px 8px; border-bottom: 1px solid #1a3050; }
  td { padding: 6px 8px; border-bottom: 1px solid #0b1220; color: #e2f0ff; }
  tr:hover td { background: #0b1220; }
  .badge { display: inline-block; padding: 2px 6px; border-radius: 3px;
           font-size: 10px; }
  .badge.green { background: #064e3b; color: #10b981; }
  .badge.red { background: #7f1d1d; color: #ef4444; }
  .badge.blue { background: #1e3a8a; color: #60a5fa; }
  .status-dot { display: inline-block; width: 8px; height: 8px;
                border-radius: 50%; margin-right: 6px; }
  .dot-green { background: #10b981; }
  .dot-red { background: #ef4444; }
  #refresh-time { color: #475569; font-size: 10px; margin-left: auto; }
</style>
</head>
<body>
<div class="nav">
  <h1>J A R V I S</h1>
  <a href="#overview" class="active">Přehled</a>
  <a href="#logs">Logy</a>
  <a href="#audit">Audit</a>
  <a href="#scheduler">Scheduler</a>
  <a href="#agents">Agenti</a>
  <span id="refresh-time">Obnovuje se...</span>
</div>

<div class="container">

  <!-- Přehled -->
  <div id="overview">
    <div class="grid" id="metrics-grid">
      <div class="card">
        <h3>CPU</h3>
        <div class="metric" id="cpu-val">—</div>
        <div class="bar"><div class="bar-fill" id="cpu-bar" style="width:0%"></div></div>
      </div>
      <div class="card">
        <h3>RAM</h3>
        <div class="metric" id="ram-val">—</div>
        <div class="bar"><div class="bar-fill" id="ram-bar" style="width:0%"></div></div>
      </div>
      <div class="card">
        <h3>DISK</h3>
        <div class="metric" id="disk-val">—</div>
        <div class="bar"><div class="bar-fill" id="disk-bar" style="width:0%"></div></div>
      </div>
      <div class="card">
        <h3>OLLAMA</h3>
        <div class="metric" id="ollama-status" style="font-size:14px">—</div>
        <div class="metric-sub" id="ollama-model">—</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <h3>AGENTI</h3>
      <table id="agents-table">
        <thead><tr><th>Agent</th><th>Status</th><th>Interval</th></tr></thead>
        <tbody><tr><td colspan="3" style="color:#475569">Načítám...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Scheduler -->
  <div class="card" id="scheduler" style="margin-bottom:16px">
    <h3>NAPLÁNOVANÉ ÚLOHY</h3>
    <table id="tasks-table">
      <thead><tr><th>ID</th><th>Název</th><th>Spuštění</th><th>Opakování</th><th>Počet</th></tr></thead>
      <tbody><tr><td colspan="5" style="color:#475569">Žádné naplánované úlohy</td></tr></tbody>
    </table>
  </div>

  <!-- Audit log -->
  <div class="card" id="audit" style="margin-bottom:16px">
    <h3>AUDIT LOG (posledních 20)</h3>
    <table id="audit-table">
      <thead><tr><th>Čas</th><th>Akce</th><th>Povoleno</th><th>Důvod</th></tr></thead>
      <tbody><tr><td colspan="4" style="color:#475569">Načítám...</td></tr></tbody>
    </table>
  </div>

  <!-- Logy -->
  <div class="card" id="logs">
    <h3>SYSTEM LOGY</h3>
    <div class="log-box" id="log-box">Připojuji se...</div>
  </div>

</div>

<script>
const $ = id => document.getElementById(id);

function barClass(pct) {
  return pct > 90 ? 'danger' : pct > 75 ? 'warn' : '';
}

async function refresh() {
  try {
    // Metriky systému
    const sys = await fetch('/api/system').then(r => r.json());
    $('cpu-val').textContent = sys.cpu + '%';
    $('ram-val').textContent = sys.ram + '%';
    $('disk-val').textContent = sys.disk + '%';
    ['cpu','ram','disk'].forEach(k => {
      const bar = $(k+'-bar');
      bar.style.width = sys[k] + '%';
      bar.className = 'bar-fill ' + barClass(sys[k]);
    });

    // Ollama
    const status = await fetch('/api/status').then(r => r.json());
    $('ollama-status').innerHTML =
      `<span class="status-dot ${status.ollama ? 'dot-green':'dot-red'}"></span>` +
      (status.ollama ? 'Online' : 'Offline');
    $('ollama-model').textContent = status.model || '—';

    // Agenti
    const agents = await fetch('/api/agents').then(r => r.json());
    const atbody = $('agents-table').querySelector('tbody');
    atbody.innerHTML = Object.entries(agents).map(([n,a]) =>
      `<tr><td>${n}</td>
       <td><span class="badge ${a.running?'green':'red'}">${a.running?'běží':'zastaven'}</span></td>
       <td>${a.interval}s</td></tr>`
    ).join('') || '<tr><td colspan="3" style="color:#475569">Žádní agenti</td></tr>';

    // Scheduler
    const tasks = await fetch('/api/scheduler').then(r => r.json());
    const ttbody = $('tasks-table').querySelector('tbody');
    ttbody.innerHTML = tasks.length ?
      tasks.map(t =>
        `<tr><td style="color:#475569">${t.id}</td><td>${t.name}</td>
         <td>${t.fire_at}</td>
         <td>${t.repeat ? t.repeat+'s' : '—'}</td>
         <td>${t.run_count}</td></tr>`
      ).join('') :
      '<tr><td colspan="5" style="color:#475569">Žádné naplánované úlohy</td></tr>';

    // Audit
    const audit = await fetch('/api/audit').then(r => r.json());
    const aubody = $('audit-table').querySelector('tbody');
    aubody.innerHTML = audit.map(e => {
      const t = new Date(e.timestamp*1000).toLocaleTimeString();
      return `<tr>
        <td style="color:#475569">${t}</td>
        <td>${e.action}</td>
        <td><span class="badge ${e.allowed?'green':'red'}">${e.allowed?'ANO':'NE'}</span></td>
        <td style="color:#475569">${e.reason}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="4" style="color:#475569">Prázdný log</td></tr>';

    $('refresh-time').textContent = 'Obnoveno: ' + new Date().toLocaleTimeString();
  } catch(e) {
    console.error(e);
  }
}

// WebSocket pro logy
const ws = new WebSocket(`ws://${location.host}/ws/logs`);
ws.onmessage = e => {
  const box = $('log-box');
  const line = document.createElement('div');
  const data = JSON.parse(e.data);
  line.className = 'log-line ' + (data.level||'info').toLowerCase();
  line.textContent = `[${new Date().toLocaleTimeString()}] ${data.message}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
  if (box.children.length > 200) box.removeChild(box.firstChild);
};
ws.onerror = () => {
  $('log-box').innerHTML = '<div class="log-line warn">WebSocket nedostupný</div>';
};

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


if HAS_FASTAPI:
    app = FastAPI(title="JARVIS Dashboard", docs_url=None, redoc_url=None)
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
            "version": "4.4.0",
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
        if logger_module_available:
            from config import CONFIG
            import requests as _r
            try:
                r = _r.get("http://localhost:11434/api/tags", timeout=2)
                ok = r.status_code == 200
            except Exception:
                ok = False
            return {"ollama": ok, "model": CONFIG.get("ollama_model", "?")}
        return {"ollama": False, "model": "—"}

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
            import json as _json
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
                    "importance": round(imp, 2), "tags": tags,
                    "group": tags[0] if tags else "memory",
                })
                seen_ids.add(nid)

                # Hrany mezi uzly se stejným tagem
                for other in items:
                    other_id = str(other["id"])
                    if other_id == nid or other_id not in seen_ids:
                        continue
                    common = set(tags) & set(other.get("tags", []))
                    if common:
                        links.append({
                            "source": nid, "target": other_id,
                            "label": list(common)[0],
                        })

            return {"nodes": nodes[:50], "links": links[:80]}
        except Exception as e:
            return {"nodes": [], "links": [], "error": str(e)}

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

    @app.post("/api/config")
    async def update_config(body: dict):
        """Aktualizuje konfiguraci za běhu (whitelist bezpečných klíčů)."""
        ALLOWED = {"ollama_model", "tts_rate", "tts_voice", "stt_language",
                   "wake_word_enabled", "tts_enabled", "tts_streaming"}
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

    # ── Agent Timeline ────────────────────────────────
    _agent_timeline: list = []   # in-memory buffer posledních runů

    @app.get("/api/agent/timeline")
    async def agent_timeline():
        return {"runs": _agent_timeline[-20:]}

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
            return result
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/skill/save")
    async def skill_save(body: dict):
        """Uloží vygenerovaný plugin do plugins/custom/."""
        name       = body.get("name", "").strip().replace(" ", "_").lower()
        skill_code = body.get("skill_code", "")
        manifest   = body.get("manifest", {})
        if not name or not skill_code:
            return {"error": "Chybí name nebo skill_code"}
        try:
            from pathlib import Path as _Path
            dest = _Path(__file__).parent / "plugins" / "custom" / name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "skill.py").write_text(skill_code, encoding="utf-8")
            import json as _json
            if manifest:
                (dest / "manifest.json").write_text(
                    _json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"saved": str(dest), "name": name}
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
                # Podpora obou field names: "command" (nový) i "text" (starý)
                text = (data.get("command") or data.get("text") or "").strip()
                if not text:
                    continue

                try:
                    from llm import LocalRouter, LLMEngine
                    from config import CONFIG

                    msg, action = LocalRouter().route(text)

                    if action and action.get("action") not in ("answer", None):
                        from commands import CommandExecutor
                        result = CommandExecutor(CONFIG).execute(
                            action["action"], action.get("params", {}))
                        reply = result or msg or "Hotovo."
                        await send({"type": "chunk", "data": reply})
                        await send({"type": "done"})
                    else:
                        # Streaming LLM odpověď
                        llm = LLMEngine(CONFIG)
                        buffer = []
                        for chunk in llm.stream_ask(text):
                            if isinstance(chunk, str) and chunk:
                                buffer.append(chunk)
                                await send({"type": "chunk", "data": chunk})
                                await asyncio.sleep(0)  # yield event loop
                        await send({"type": "done"})

                except Exception as e:
                    logger.error(f"ws_chat chyba: {e}")
                    await send({"type": "error", "data": str(e)})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"ws_chat uzavřen: {e}")

    @app.websocket("/ws/logs")
    async def ws_logs(ws: WebSocket):
        """Live logy přes WebSocket — posílá JSON {level, message, ts}."""
        await ws.accept()
        _ws_clients.add(ws)
        try:
            while True:
                # Keep-alive — čekáme na ping od klienta
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping"}))
        except WebSocketDisconnect:
            _ws_clients.discard(ws)
        except Exception:
            _ws_clients.discard(ws)

    @app.websocket("/ws/graph")
    async def ws_graph(ws: WebSocket):
        """Streaming stavu Graf agenta — posílá JSON eventi."""
        await ws.accept()
        _graph_clients.add(ws)
        try:
            while True:
                await asyncio.sleep(30)  # keep-alive
        except WebSocketDisconnect:
            _graph_clients.discard(ws)
        except Exception:
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
