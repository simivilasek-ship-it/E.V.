# JARVIS v4.3 — Lokální AI asistent pro Linux

> Ovládej celý počítač hlasem nebo textem. Běží 100 % lokálně, žádný cloud, žádný API klíč.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-420%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.3.0-orange)]()

---
## Co je nového v v4.3

| Změna | Detail |
|---|---|
| **Desktop app** | `app_desktop.py` — pywebview nativní okno, stejné React HUD UI jako web |
| **Sci-Fi HUD** | Orbitron font, SVG arc progress rings, sparkline grafy, hex grid pozadí |
| **3D AI Orb** | GLSL vertex shader (Simplex noise), pulsující glow, ring + particle system |
| **Plugin sandbox** | `ManifestValidator` + `ThreadPoolExecutor` timeout — pluginy nemohou zablokovat JARVIS |
| **420 testů** | 0 failed — stabilizace celé test suite |
| **Vosk offline STT** | Fallback bez internetu, český model ~50 MB |
| **Streaming TTS** | `edge-tts → ffplay stdin`, první slovo ~1s dříve |
| **`/health` endpoint** | `{"status":"ok","ws":"running"}` pro monitoring |
| **WS exponential backoff** | Max 5 pokusů: 1s→2s→4s→8s→16s, jasná chybová hláška |
| **ruff clean** | 0 kritických chyb (F821/F811/E711/E712) |

---



## Demo

```
"Otevři Spotify a pak najdi ceny RTX 4090 a ulož je do poznámky"

  ┌─ Planner ─────────────────────────────────────────────┐
  │  1. otevři Spotify                                    │
  │  2. vyhledej ceny RTX 4090                           │
  │  3. ulož výsledek do poznámky                        │
  └───────────────────────────────────────────────────────┘
       ↓ Router → Executor → Critic (×3)
  "Spotify spuštěn. RTX 4090: ~35 000 Kč. Poznámka uložena."
```

---

## Quickstart — 3 způsoby

### Desktop app (doporučeno — nativní okno s HUD UI)
```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_desktop.sh
```

### Klasická Tkinter GUI
```bash
bash start_jarvis.sh
```

---

## Rozhraní

### Desktop app — React HUD (`app_desktop.py`)

Nativní okno postavené na **pywebview + FastAPI + React**. Žádný prohlížeč není potřeba.

- **AI Orb** — 3D koule s GLSL vertex shaderem (simplex noise), mění barvu a amplitudu podle stavu (`idle / listening / thinking / speaking`)
- **Chat** — streamovaná odpověď chunk po chunku, markdown + code highlighting, historie ↑↓
- **SystemPanel** — SVG arc ringly pro CPU / RAM / disk s live daty
- **PluginStore** — instalace pluginů z marketplace jedním kliknutím
- **StatusBar** — Ollama status, aktuální model, connection dot

Spuštění:
```bash
bash start_desktop.sh      # sestaví React + spustí okno
python app_desktop.py      # přímo (předpokládá web_dist/)
```

### Web dashboard (`dashboard.py`)

```bash
python dashboard.py        # localhost:8002
```

Monitoring: CPU / RAM / disk, logy, audit trail, scheduler, agenti.
WebSocket `/ws/chat` pro live chat přímo z browseru.

### Tkinter GUI (`jarvis.py`)

Klasické desktopové okno s animovaným orbem, chatem a nastavením STT/TTS/MCP.

---

## Co JARVIS umí

### Ovládání PC (bez LLM — okamžitě)
```
"Otevři Chrome / Discord / Spotify"  → spustí aplikaci
"Zavři Discord"                      → ukončí proces
"Hlasitost na 60 / Ztlum"           → nastaví zvuk
"Jas na 80"                          → jas obrazovky
"Screenshot"                         → PNG na plochu
"Vytvoř složku projekt"              → mkdir
"Vypni / Restartuj počítač"          → shutdown / restart
```

### Vision
```
"Co vidíš na obrazovce?"  → Screenshot + LLaVA popis
"Přečti text z okna"      → OCR (pytesseract)
"Zapni kameru"            → webcam + LLaVA
```

### YouTube & média
```
"Zahraj Bohemian Rhapsody"  → yt-dlp + ffplay streaming
"Stáhni video X"            → yt-dlp download
"Play / pauza / další"      → mediální klávesy
```

### AI odpovědi
```
"Co je strojové učení?"     → Wikipedia + Ollama
"Přelož hello world"        → Ollama překlad
"Vypočítej 15 % z 3 400"    → AST sandbox kalkulátor
"Napiš Python funkci pro X" → Ollama kód (qwen2.5-coder)
"100 USD na CZK"            → měnový konvertor
```

### Paměť
```
"Zapamatuj si mám rád kávu"  → SQLite + embedding
"Co víš o mně?"              → sémantický recall
"Koho jsem zmínil minule?"   → cosine similarity search
```

---

## Architekturní diagram

```
╔══════════════════════════════════════════════════════════════╗
║          VSTUP: Hlas / Text / Web chat / Desktop UI         ║
╚══════════════════════╦═══════════════════════════════════════╝
                       │
          ┌────────────▼────────────────────────────┐
          │         LOCAL ROUTER                    │
          │   regex + fuzzy matching (rapidfuzz)    │
          │   95 % příkazů zpracuje bez LLM         │
          └──────┬───────────────────────┬──────────┘
                 │ match                 │ no match
          ┌──────▼──────┐        ┌───────▼────────────────────┐
          │   Plugin    │        │      LLM PIPELINE          │
          │   Routes    │        │                            │
          └──────┬──────┘        │  Graf agent / ReAct agent  │
                 │               │  LLMEngine + LLMRouter     │
                 │               │  (OllamaClient — sdílený)  │
                 │               └─────────────┬──────────────┘
                 │                             │
          ┌──────▼─────────────────────────────▼──────┐
          │          SECURITY v2 (5 úrovní)           │
          └──────────────────────┬────────────────────┘
                                 │
          ┌──────────────────────▼────────────────────┐
          │      CommandExecutor (40+ akcí)           │
          └──────────────────────┬────────────────────┘
                                 │
                    TTS Streaming (~1 s první odezva)
```

**Podpůrné systémy:**
```
Memory (SQLite + embeddingy)   ←→  UserProfile + DailySummarizer
EventBus (async callbacky)     ←→  Scheduler (1d/1h/5m formát)
AgentManager (CPU/RAM/disk)    ←→  HealthCheck (Ollama, RAM, disk)
AsyncEngine (prioritní fronta) ←→  OfflineMode (queue + KB)
```

---

## Plugin systém

```
plugins/custom/muj_plugin/
  ├── manifest.json   ← metadata + permissions
  └── skill.py        ← handler (sandbox: AST kontrola importů)
```

### Příklad — počasí Brno

**`manifest.json`**
```json
{
  "name": "pocasi_brno",
  "version": "1.0.0",
  "description": "Počasí pro Brno jedním slovem",
  "author": "ja",
  "permissions": [],
  "triggers": ["počasí brno", "jak je venku"]
}
```

**`skill.py`**
```python
import re, requests

_RE = re.compile(r"\b(pocasi\s+brno|jak\s+je\s+venku)\b", re.IGNORECASE)

def _handle(text):
    try:
        r = requests.get("https://wttr.in/Brno?format=3", timeout=5)
        return r.text.strip(), {"action": "answer", "params": {}}
    except Exception:
        return "Počasí nedostupné.", {"action": "answer", "params": {}}

def get_routes():  return [{"pattern": _RE, "handler": _handle}]
def get_actions(): return {}
```

### Sandbox permissions

| Permission | Odemkne |
|---|---|
| *(žádná)* | stdlib, requests, numpy, pandas |
| `os` | `os`, `os.path` |
| `subprocess` | `subprocess` |
| `filesystem` | `shutil`, `glob`, `tempfile` |
| `system` | `psutil`, `platform` |
| `database` | `sqlite3`, `sqlalchemy` |

### Marketplace

```
"marketplace seznam"                  → dostupné pluginy
"nainstaluj plugin calculator"        → builtin instalace
"nainstaluj z github user/plugin"     → GitHub ZIP
```

---

## Konfigurace

### `config.json`
```json
{
  "ollama_url":              "http://localhost:11434/api/chat",
  "ollama_model":            "qwen2.5:3b",
  "tts_voice":               "cs-CZ-AntoninNeural",
  "tts_rate":                170,
  "tts_streaming":           true,
  "stt_language":            "cs-CZ",
  "wake_word":               "jarvis",
  "wake_word_enabled":       true,
  "agent_max_steps":         8,
  "agent_timeout":           120,
  "mcp_filesystem_enabled":  true,
  "mcp_brave_enabled":       false
}
```

### Ollama modely

| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | výchozí — česky, rychlý |
| `qwen2.5-coder:1.5b-base` | ~2 GB | kód (LLMRouter auto-vybere) |
| `llama3.1:8b` | ~8 GB | komplexní analýzy |
| `llava:7b` | ~8 GB | vision — popis obrazovky, webcam |

---

## MCP integrace (9 serverů)

> `node --version` ≥ 18 + `pip install mcp`

| Server | Co umí | API klíč |
|---|---|---|
| Filesystem | čtení souborů, strom adresářů | ❌ |
| Fetch | načtení obsahu stránek | ❌ |
| Git | git log / status / diff | ❌ |
| Memory Graph | knowledge graph | ❌ |
| Time | čas + časová pásma | ❌ |
| Sequential Thinking | krok-za-krokem plánování | ❌ |
| Puppeteer | screenshot webu, browser automation | ❌ |
| Computer Control | klikání, psaní, okna | ❌ |
| Brave Search | webové vyhledávání | ✅ `BRAVE_API_KEY` |

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 422 testů, 0 failed
```

### Testovací sady

| Soubor | Počet | Pokrývá |
|---|---|---|
| `test_jarvis.py` | 108 | integrace — celý stack |
| `tests/test_agent_graph.py` | 27 | Graf agent — uzly, retry, timeout |
| `tests/test_integration.py` | 30 | security pipeline, sandbox, path |
| `tests/test_commands.py` | 24 | CommandExecutor — 40+ akcí |
| `tests/test_security.py` | 22 | oprávnění, audit log |
| `tests/test_async_utils.py` | 16 | AsyncEngine — cleanup, priorita |
| `tests/test_react_agent.py` | 17 | ReAct — parsing, tool calls |
| `tests/test_event_bus.py` | 13 | EventBus — subscribe, timeout |
| `tests/test_new_modules.py` | 23 | health check, cache, offline |
| ostatní | ~142 | STT, TTS, vision, marketplace… |

### Přidání nové akce

```python
# 1. Pattern v local_router.py
re.compile(r"\b(muj\s+prikaz)\b") → ("muj_akce", args)

# 2. Handler v commands/utils.py
def cmd_muj_prikaz(param: str) -> str: ...

# 3. Export z commands/__init__.py
from .utils import cmd_muj_prikaz

# 4. Security level v security_v2.py
"muj_prikaz": PermissionLevel.STANDARD

# 5. Test v tests/test_commands.py
```

---

## Architektura souborů

```
jarvis.py             — Tkinter GUI bootstrap
app_desktop.py        — Desktop app (pywebview + React HUD)
app_core.py           — orchestrátor, lazy init, routing pipeline
│
├── local_router.py   — LocalRouter: regex + fuzzy (rapidfuzz)
├── llm.py            — LLMEngine + OllamaClient + token budget
├── llm_router.py     — TaskType → model/temperature/tokens
│
├── agent_graph.py    — Graf agent (Planner→Router→Executor→Critic)
├── agent_react.py    — ReAct agent (Thought→Action→Observation)
├── agent_tools.py    — ToolRegistry (16+ nástrojů)
│
├── memory.py         — SQLite + EmbeddingEngine + DailySummarizer
├── user_profile.py   — permanentní fakta, auto-extrakce z textu
│
├── plugin_system.py  — sandbox (AST), lazy loading
├── plugin_marketplace.py — REGISTRY, builtin + GitHub ZIP install
│
├── tts.py            — edge-tts streaming + pyttsx3 fallback
├── stt.py            — Google STT + VoskSTT offline
├── vision.py         — OCR, screen describe, webcam + LLaVA
├── wake_word_detector.py — detekce „JARVISe", pause/resume
│
├── security_v2.py    — AuditLog, 5 úrovní, confirmation dialog
├── mcp_bridge.py     — MCP klient (9 serverů)
│
├── health_check.py   — monitoring Ollama, RAM, disk, CPU
├── cache_manager.py  — LRU + disk cache
├── offline_mode.py   — fronta příkazů + fallback KB
├── async_utils.py    — AsyncEngine, prioritní fronta
├── event_bus.py      — PUB/SUB, daemon callbacky 5s timeout
├── agents.py         — background monitoring (CPU/RAM/disk)
├── scheduler.py      — at/after/every (formát: 1d/1h/5m/30s)
│
├── dashboard.py      — FastAPI web UI + /ws/chat (localhost:8002)
├── api.py            — REST API pro integraci
│
├── commands/         — 40+ akcí (system, apps, files, media, utils)
│
└── web/              — React frontend (Vite + Three.js + Framer Motion)
    ├── src/App.jsx
    ├── src/store/jarvis.js    — Zustand, persistent WS chat
    └── src/components/
        ├── AIOrb.jsx          — GLSL vertex shader, 4 stavy
        ├── ChatPanel.jsx      — streaming, markdown, historie příkazů ↑↓
        ├── SystemPanel.jsx    — SVG arc ringly CPU/RAM/disk
        ├── PluginStore.jsx    — marketplace UI
        └── StatusBar.jsx      — Ollama status, model, connection
```

---

## Troubleshooting

| Problém | Řešení |
|---|---|
| Desktop app se neotevře | `pip install pywebview` |
| React se nesestaví | `cd web && npm install --legacy-peer-deps && npm run build` |
| Ollama nespustí | `ollama serve && ollama pull qwen2.5:3b` |
| JARVIS neslyší | `sudo usermod -a -G audio $USER` + logout |
| TTS nefunguje | `sudo apt install ffmpeg && pip install edge-tts` |
| MCP nefunguje | `node --version` (18+), `pip install mcp` |
| OCR nefunguje | `sudo apt install tesseract-ocr tesseract-ocr-ces` |
| Embeddingy | `pip install sentence-transformers` |
| Fuzzy matching | `pip install rapidfuzz` |
| Vosk offline STT | `pip install vosk` + model z [alphacephei.com](https://alphacephei.com/vosk/models) |
| Plugin odmítnut sandboxem | Přidej `permissions` do `manifest.json` |

---

## Roadmapa

- [ ] `pip install jarvis-assistant` — PyPI package
- [ ] Webové GUI (React frontend přes dashboard `/app`)
- [ ] OfflineManager integrace do routing pipeline
- [ ] Spotify Web API
- [ ] Plugin autoupdate (sémantické verzování)
- [ ] Kontext aktivního okna v system promptu

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP + sestavení React)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`
- Linux (Ubuntu 22.04+ / Arch) — macOS experimentálně

---

## Licence

MIT — volně šiřitelný a upravitelný.
