# API Reference — JARVIS v5.0

Backend běží na `http://localhost:8002`. Všechny endpointy vrací JSON pokud není uvedeno jinak.

---

## Systém a zdraví

### `GET /health`

Rychlý status check backendu.

**Response:**
```json
{
  "status": "ok",
  "uptime_s": 3621.4,
  "version": "5.0.0",
  "ws": "running",
  "ollama": "online",
  "model": "qwen2.5:3b"
}
```

---

### `GET /api/context`

Živý kontext PC pro Copilot a dashboard — okna, systém, schránka.

**Response:**
```json
{
  "formatted": "Aktuální čas: 21:29...\nAktivní okno: Cursor\n...",
  "active_window": "Cursor Agents",
  "windows": ["Firefox — Copilot", "simi@host:~"],
  "clipboard": "",
  "system": {
    "hostname": "simi-System-Product-Name",
    "os": "Linux 7.0.0-15-generic",
    "cpu": 12.5,
    "ram": 32.2,
    "ram_used_gb": 9.7,
    "ram_total_gb": 30.0,
    "disk": 9.9,
    "disk_free_gb": 801.2
  },
  "time": "21:29, Saturday 06.06.2026"
}
```

---

### `GET /api/system`

Aktuální systémové metriky (CPU, RAM, GPU, disk, síť).

**Response:**
```json
{
  "cpu": 12.4,
  "ram": 68.1,
  "ram_used_gb": 10.9,
  "ram_total_gb": 16.0,
  "disk": 45.2,
  "disk_used_gb": 180.4,
  "disk_total_gb": 512.0,
  "net_sent_mb": 1.2,
  "net_recv_mb": 8.7,
  "gpu": null,
  "cpu_temp": 52.0,
  "processes": 312
}
```

---

### `GET /api/status`

Detailní status všech JARVIS subsystémů.

**Response:**
```json
{
  "ollama_available": true,
  "model": "qwen2.5:3b",
  "memory_entries": 847,
  "plugins_loaded": 5,
  "agents_running": 0,
  "workers_active": ["git", "email"],
  "missions_active": 2,
  "uptime_s": 3621.4,
  "version": "5.0.0"
}
```

---

## Chat a příkazy

### `POST /api/chat`

Hlavní REST chat — stejný unified pipeline jako WebSocket (Copilot + Agent + akce).

**Request:**
```json
{ "text": "přehled o pc" }
```

**Response:**
```json
{ "response": "🖥️ hostname — Linux...\n📊 CPU 8% | RAM 32%..." }
```

Režim se vybírá automaticky: lokální příkaz → agent → Copilot LLM.

---

### `POST /api/command`

Odešle příkaz a čeká na synchronní odpověď (max 60s).

**Request:**
```json
{
  "command": "Napiš funkci pro výpočet faktoriálu v Pythonu",
  "stream": false
}
```

**Response:**
```json
{
  "response": "```python\ndef factorial(n: int) -> int:\n    ...\n```",
  "action": "answer",
  "provider": "groq",
  "latency_ms": 243
}
```

---

### `WS /ws/chat`

Streaming chat přes WebSocket. Odpovědi přicházejí chunk po chunku.

**Odeslání zprávy:**
```json
{ "command": "Vysvětli mi jak funguje transformer architektura" }
```
nebo starý formát:
```json
{ "text": "Vysvětli mi jak funguje transformer architektura" }
```

**Přijímané zprávy:**
```json
{ "type": "status", "data": "💬 Copilot…" }
{ "type": "status", "data": "⚡ Provádím akci…" }
{ "type": "status", "data": "🤖 Agent pracuje…" }
{ "type": "agent_step", "data": "Hledám soubory…" }
{ "type": "chunk", "data": "Transformer architektura" }
{ "type": "chunk", "data": " je typ neuronové sítě..." }
{ "type": "done" }
```

Při chybě:
```json
{ "type": "error", "data": "Ollama nereaguje (timeout)" }
```

---

## Paměť

### `GET /api/memory`

Statistiky paměťového systému + posledních N vzpomínek.

**Query params:** `limit` (default 20), `min_importance` (default 0.3)

**Response:**
```json
{
  "total": 847,
  "valid": 831,
  "avg_importance": 0.612,
  "recent": [
    {
      "id": "a3f9b2c1",
      "content": "Uživatel preferuje tmavý režim",
      "importance": 0.8,
      "tags": ["preference", "ui"],
      "created_at": 1748901234.5,
      "last_access": 1748905678.2
    }
  ],
  "graph": {
    "entities": 142,
    "relations": 287
  }
}
```

---

### `GET /api/memory/graph`

Knowledge graph — entity a relace pro vizualizaci.

**Response:**
```json
{
  "nodes": [
    { "id": "1", "label": "Petr", "group": "entity", "importance": 0.7 },
    { "id": "2", "label": "projekt Alpha", "group": "entity", "importance": 0.6 }
  ],
  "links": [
    {
      "id": 5,
      "source": "1",
      "target": "2",
      "label": "pracuje na",
      "ts": 1748901234.5,
      "confidence": 0.95
    }
  ]
}
```

---

## Agenti

### `GET /api/agents`

Status všech agentů (ReAct, Graf, Hierarchical).

**Response:**
```json
{
  "agents": [
    {
      "name": "graph_agent",
      "status": "idle",
      "last_run": 1748901234.5,
      "steps_completed": 4,
      "current_task": null
    }
  ]
}
```

---

### `POST /api/agent/parallel`

Spustí více agentů paralelně pro různé subtasky.

**Request:**
```json
{
  "tasks": [
    "Vyhledej nejnovější zprávy o AI",
    "Zkontroluj git status projektu",
    "Přečti soubor config.json"
  ]
}
```

**Response:**
```json
{
  "results": [
    { "task": "Vyhledej...", "result": "...", "steps": 3, "ok": true },
    { "task": "Zkontroluj...", "result": "...", "steps": 2, "ok": true },
    { "task": "Přečti...", "result": "...", "steps": 1, "ok": true }
  ],
  "total_steps": 6
}
```

---

### `GET /api/agent/timeline`

Historie posledních agent runs s výsledky.

**Response:**
```json
{
  "runs": [
    {
      "id": "run_abc123",
      "task": "Najdi chybu v test_memory.py",
      "status": "success",
      "steps": 4,
      "started_at": 1748901234.5,
      "duration_s": 8.2,
      "result": "Opravil jsem import na řádku 42"
    }
  ]
}
```

---

### `WS /ws/agents`

Live události agent pipeline — krok po kroku.

**Přijímané zprávy:**
```json
{ "type": "step_start", "agent": "graph_agent", "step": "planner", "task": "..." }
{ "type": "step_done",  "agent": "graph_agent", "step": "executor", "result": "..." }
{ "type": "agent_done", "agent": "graph_agent", "success": true, "steps": 4 }
```

---

### `WS /ws/graph`

Real-time vizualizace agent grafu (pro `AgentGraph.tsx`).

**Přijímané zprávy:**
```json
{ "type": "ready",      "status": "idle" }
{ "type": "node_enter", "node": "planner" }
{ "type": "node_exit" }
{ "type": "reasoning",  "text": "🤔 Analyzuji dostupné nástroje..." }
{ "type": "ping" }
```

---

## Mise (Mission Manager)

### `GET /api/missions`

Seznam všech misí.

**Response:**
```json
{
  "missions": [
    {
      "id": "m_abc123",
      "title": "Denní blog o AI",
      "description": "Napiš 7 blog postů o AI, jeden každý den",
      "status": "active",
      "deadline": "2026-06-10",
      "steps_total": 7,
      "steps_done": 3,
      "steps_failed": 0,
      "created_at": 1748901234.5,
      "last_activity": 1748987634.5
    }
  ]
}
```

---

### `POST /api/missions`

Vytvoří novou misi. LLM automaticky rozplánuje kroky.

**Request:**
```json
{
  "title": "Denní blog o AI",
  "description": "Napiš 7 blog postů o AI trendech, jeden každý den",
  "deadline": "2026-06-10"
}
```

**Response:**
```json
{
  "ok": true,
  "mission": {
    "id": "m_abc123",
    "steps": [
      { "id": "s_1", "description": "Napiš post o LLM architektuře", "due_date": "2026-06-04" },
      { "id": "s_2", "description": "Napiš post o RAG systémech",    "due_date": "2026-06-05" }
    ]
  }
}
```

---

### `PUT /api/missions/{id}/pause`

Pozastaví misi (executor ji přeskočí).

### `PUT /api/missions/{id}/resume`

Obnoví pozastavenou misi.

### `DELETE /api/missions/{id}`

Smaže misi a všechny její kroky.

---

## Vision

### `GET /api/vision/analyze`

Pořídí screenshot a spustí OCR + UI element analýzu.

**Response:**
```json
{
  "ocr_text": "Visual Studio Code\nFile Edit Selection View...\nclass JarvisMemory:",
  "active_app": "code",
  "ui_elements": [
    { "role": "button", "name": "File",    "x": 42,  "y": 28 },
    { "role": "input",  "name": "",        "x": 400, "y": 28 },
    { "role": "label",  "name": "JARVIS",  "x": 120, "y": 380 }
  ],
  "clickable_count": 47
}
```

---

## Plugin Marketplace

### `GET /api/marketplace`

Katalog všech dostupných pluginů.

**Response:**
```json
{
  "plugins": [
    {
      "id": "calculator",
      "name": "calculator",
      "description": "Rozšířená kalkulačka s historií výpočtů",
      "author": "JARVIS team",
      "version": "2.1.0",
      "rating": 4.8,
      "reviews": 12,
      "downloads": 1024,
      "tags": ["math", "builtin"],
      "installed": true,
      "has_update": false
    }
  ],
  "updates": {}
}
```

---

### `POST /api/marketplace/install/{name}`

Nainstaluje plugin z registru nebo GitHub.

**Response:**
```json
{ "ok": true, "message": "Plugin 'calculator' nainstalován. Restartuj JARVIS pro aktivaci." }
```

---

### `DELETE /api/marketplace/uninstall/{name}`

Odinstaluje plugin.

---

### `POST /api/marketplace/update/{name}`

Aktualizuje plugin na nejnovější verzi (uninstall + install).

---

### `POST /api/marketplace/review/{name}`

Přidá hodnocení pluginu.

**Request:**
```json
{ "rating": 4.5, "comment": "Funguje skvěle, oceňuji historii výpočtů." }
```

---

### `GET /api/marketplace/reviews/{name}`

Vrátí seznam hodnocení pro plugin.

**Response:**
```json
{
  "reviews": [
    { "rating": 5.0, "comment": "Perfektní!", "ts": 1748901234.5 },
    { "rating": 4.0, "comment": "Dobrý, ale chybí export.", "ts": 1748905678.2 }
  ],
  "avg": 4.5
}
```

---

### `POST /api/marketplace/run/{name}`

Spustí plugin v izolovaném sandboxu a vrátí výstup.

**Request (volitelně):**
```json
{ "timeout": 30 }
```

**Response:**
```json
{
  "ok": true,
  "stdout": "Plugin výstup zde\n",
  "stderr": "",
  "returncode": 0,
  "elapsed": 0.124
}
```

---

## Konfigurace

### `GET /api/config`

Vrátí aktuální konfiguraci (bez API klíčů).

### `POST /api/config`

Uloží novou konfiguraci do `config.json`.

**Request:**
```json
{
  "ollama_model": "llama3.1:8b",
  "tts_rate": 180,
  "cloud_routing_enabled": true
}
```

---

## Workflow Engine

### `GET /api/workflows`

Seznam aktivních workflow.

### `POST /api/workflows`

Vytvoří nový workflow.

**Request:**
```json
{
  "name": "CPU Alert",
  "trigger": { "type": "cpu", "threshold": 90 },
  "actions": [
    { "type": "notify", "message": "CPU překročilo 90%!" },
    { "type": "kill_process", "target": "chrome" }
  ]
}
```

### `DELETE /api/workflows/{id}`

Smaže workflow.

---

## Notifikace

### `POST /api/notify`

Odešle desktopovou notifikaci.

**Request:**
```json
{
  "title": "JARVIS",
  "body": "Úkol dokončen",
  "urgency": "normal"
}
```
`urgency`: `"low"` | `"normal"` | `"high"`

---

## Audit log

### `GET /api/audit`

Vrátí poslední security záznamy z `~/.jarvis_audit.jsonl`.

Query: `limit` (1–500, default 50)

```json
[
  {
    "timestamp": 1717654321.5,
    "action": "shell_exec",
    "params": {"cmd": "ls"},
    "allowed": false,
    "reason": "Shell příkaz není v whitelistu",
    "user_text": "spusť ls",
    "result": ""
  }
]
```

UI: panel **Nastavení → Security audit log** (auto-refresh 15s).

---

## Logy

### `WS /ws/logs`

Live log stream — každý záznam jako JSON:

```json
{ "level": "INFO",  "message": "LLM: odpověď vygenerována za 234ms", "ts": 1748901234.5 }
{ "level": "ERROR", "message": "Groq timeout po 30s, fallback na Ollama", "ts": 1748901240.1 }
```

---

## Potvrzování akcí (Security)

### `WS /ws/confirm`

Kanál pro schvalování ELEVATED/RESTRICTED akcí ve web UI.

```
Server → Klient: { "type": "confirm_request", "id": "abc", "action": "delete_file", "params": {...}, "timeout_s": 60 }
Klient → Server: { "type": "confirm_response", "id": "abc", "approved": true }
Server → Klient: { "type": "confirm_resolved", "id": "abc", "approved": true }
```

### `POST /api/confirm/respond`

REST fallback pro confirmation modal.

```json
{ "id": "abc123", "approved": true }
```

---

## Audio

### `WS /ws/audio`

Duplex audio WebSocket. Klient posílá raw PCM16 mono frames (16 kHz).

```
Klient → Server: ArrayBuffer (PCM16 frames)
Server → Klient: { "type": "transcript", "text": "..." }
Server → Klient: { "type": "speech_start" }
Server → Klient: { "type": "speech_end" }
```
