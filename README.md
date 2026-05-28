# JARVIS v4.3 — Lokální AI asistent pro Linux

> Ovládej celý počítač hlasem nebo textem. Běží 100 % lokálně, žádný cloud, žádný API klíč.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-390%2B%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.3.0-orange)]()

---

## Demo

> 📹 **[Video ukázka — nahrání připraveno]**
> 30 s: hlas → příkaz → PC akce → odpověď
>
> Pro nahrání spusť: `python jarvis.py` a nahraj obrazovku nástrojem jako OBS nebo `recordmydesktop`.

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

## Quickstart — 3 kroky

```bash
# 1. Naklonuj a nainstaluj
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh

# 2. Spusť Ollama (LLM engine)
ollama serve & ollama pull qwen2.5:3b

# 3. Spusť JARVIS
bash start_jarvis.sh
```

**Nebo s průvodcem (doporučeno pro první spuštění):**
```bash
python setup_wizard.py
```

Průvodce automaticky:
- ✅ Ověří Python, Ollama, ffmpeg
- ✅ Stáhne doporučený model
- ✅ Nastaví mikrofon a TTS hlas
- ✅ Spustí JARVIS

---

## Co JARVIS umí

### Ovládání PC (bez LLM — okamžitě)
```
"Otevři Chrome"          → spustí aplikaci
"Zavři Discord"          → ukončí proces
"Hlasitost na 60"        → nastaví zvuk
"Jas na 80"              → nastaví jas
"Screenshot"             → uloží PNG na plochu
"Vytvoř složku projekt"  → mkdir
"Vypni počítač"          → shutdown
```

### Vision — vidí obrazovku
```
"Co vidíš na obrazovce?" → Screenshot + LLaVA popis
"Přečti text z okna"     → OCR (pytesseract)
"Zapni kameru"           → webcam + LLaVA
```

### YouTube & média
```
"Zahraj Bohemian Rhapsody"  → yt-dlp + ffplay
"Stáhni video X"            → yt-dlp download
"Play / pauza / další"      → mediální klávesy
```

### AI odpovědi
```
"Co je to strojové učení?"  → Wikipedia + Ollama
"Přelož hello world"        → Ollama překlad
"Vypočítej 15 % z 3 400"    → AST kalkulátor
"Napiš Python funkci pro X" → Ollama kód
"100 USD na CZK"            → měnový konvertor
```

### Paměť
```
"Zapamatuj si mám rád kávu"    → uloží do SQLite
"Co víš o mně?"                → sémantický recall
"Koho jsem zmínil minule?"     → embedding search
```

---

## Architekturní diagram

```
╔══════════════════════════════════════════════════════════════╗
║                    VSTUP: Hlas / Text                       ║
╚══════════════════════╦═══════════════════════════════════════╝
                       │
                  ┌────▼────┐
                  │   STT   │  Google STT + Vosk offline
                  └────┬────┘
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
          └──────┬──────┘        │  ┌─────────────────────┐  │
                 │               │  │  Graf agent          │  │
                 │               │  │  Planner→Router      │  │
                 │               │  │  →Executor→Critic    │  │
                 │               │  └──────────┬──────────┘  │
                 │               │             │ složité      │
                 │               │  ┌──────────▼──────────┐  │
                 │               │  │  ReAct agent        │  │
                 │               │  │  Thought→Action→Obs │  │
                 │               │  └──────────┬──────────┘  │
                 │               │             │ vícesvůlové  │
                 │               │  ┌──────────▼──────────┐  │
                 │               │  │  LLMEngine          │  │
                 │               │  │  + LLMRouter        │  │
                 │               │  │  (model dle TaskType│  │
                 │               │  └──────────┬──────────┘  │
                 │               └─────────────┼─────────────┘
                 │                             │
          ┌──────▼─────────────────────────────▼──────┐
          │              SECURITY v2                  │
          │  SAFE → STANDARD → ELEVATED → FORBIDDEN   │
          │  AuditLog + Confirmation dialog           │
          └──────────────────────┬────────────────────┘
                                 │
          ┌──────────────────────▼────────────────────┐
          │           CommandExecutor (40+ akcí)      │
          │  system · apps · files · media · utils    │
          └──────────────────────┬────────────────────┘
                                 │
                  ┌──────────────▼──────────┐
                  │   TTS Streaming         │
                  │   edge-tts → ffplay     │
                  │   ~1 s první odezva     │
                  └─────────────────────────┘
```

**Podpůrné systémy (běží na pozadí):**
```
Memory (SQLite + embeddingy)  ←→  UserProfile (permanentní fakta)
EventBus (PUB/SUB)            ←→  Scheduler (at/after/every)
AgentManager (CPU/RAM/disk)   ←→  HealthCheck (Ollama, RAM, disk)
AsyncEngine (prioritní fronta)←→  OfflineMode (queue + KB)
```

---

## Plugin systém

### Jak funguje za 30 sekund

```
plugins/custom/muj_plugin/
  ├── manifest.json   ← metadata + permissions
  └── skill.py        ← handler
```

### Příklad 1 — jednoduchý plugin

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
import re
import requests

_RE = re.compile(r"\b(pocasi\s+brno|jak\s+je\s+venku)\b", re.IGNORECASE)

def _handle(text: str):
    try:
        r = requests.get("https://wttr.in/Brno?format=3", timeout=5)
        return r.text.strip(), {"action": "answer", "params": {}}
    except Exception:
        return "Počasí nedostupné.", {"action": "answer", "params": {}}

def get_routes():
    return [{"pattern": _RE, "handler": _handle}]

def get_actions():
    return {}
```

### Příklad 2 — plugin s akcí

**`skill.py`** — přidá zkratku pro otevření projektu
```python
import re
import subprocess

_RE = re.compile(r"\b(otevri\s+projekt|open\s+project)\b", re.IGNORECASE)

def _handle(text: str):
    subprocess.Popen(["code", "/home/user/projekt"])
    return "Projekt otevřen ve VSCode.", {"action": "answer", "params": {}}

def get_routes():
    return [{"pattern": _RE, "handler": _handle}]

def get_actions():
    return {}
```

**`manifest.json`** — tento plugin potřebuje `subprocess`
```json
{
  "name": "open_project",
  "version": "1.0.0",
  "description": "Otevře projekt ve VSCode",
  "author": "ja",
  "permissions": ["subprocess"],
  "triggers": ["otevři projekt"]
}
```

### Sandbox — povolené permissions

| Permission | Odemkne |
|---|---|
| *(žádná)* | stdlib utility, requests, numpy, pandas |
| `os` | `os`, `os.path` |
| `subprocess` | `subprocess` |
| `socket` | `socket`, `ssl`, `asyncio` |
| `filesystem` | `shutil`, `glob`, `tempfile` |
| `system` | `psutil`, `platform` |
| `database` | `sqlite3`, `sqlalchemy` |
| `crypto` | `cryptography`, `hmac`, `secrets` |

### Plugin marketplace

```bash
python jarvis.py
# nebo přímo:
"marketplace seznam"
"nainstaluj plugin calculator"
"nainstaluj z github tvuj-user/tvuj-plugin"
```

---

## Konfigurace

### `config.json` — všechny klíče s výchozími hodnotami

```json
{
  "ollama_url":              "http://localhost:11434/api/chat",
  "ollama_model":            "qwen2.5:3b",
  "tts_enabled":             true,
  "tts_voice":               "cs-CZ-AntoninNeural",
  "tts_rate":                170,
  "tts_streaming":           true,
  "stt_language":            "cs-CZ",
  "stt_energy_threshold":    300,
  "history_size":            20,
  "wake_word":               "jarvis",
  "wake_word_enabled":       true,
  "plugins_enabled":         true,
  "audit_enabled":           true,
  "mcp_filesystem_enabled":  true,
  "mcp_brave_enabled":       false,
  "agent_max_steps":         8,
  "agent_max_retries":       2,
  "agent_timeout":           120,
  "agent_llm_tokens":        500
}
```

### Modely Ollama

| Model | RAM | Nejlepší pro |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | výchozí — rychlý, česky dobře |
| `qwen2.5-coder:1.5b-base` | ~2 GB | kód (LLMRouter auto-vybere) |
| `llama3.1:8b` | ~8 GB | složité analýzy, lepší kvalita |
| `llava:7b` | ~8 GB | vision — popis obrazovky, webcam |

### `.env` — tajné klíče

```bash
BRAVE_API_KEY=tvůj_klíč   # Brave Search MCP
```

---

## MCP integrace (9 serverů)

> **Požadavky:** `node --version` ≥ 18, `pip install mcp`

| Server | Příkaz | API klíč |
|---|---|---|
| Filesystem | „přečti soubor X", „seznam ~/Dokumenty" | ❌ |
| Fetch | „načti stránku github.com" | ❌ |
| Git | „git log", „co se změnilo" | ❌ |
| Memory Graph | „zapamatuj si X", „co víš o Y" | ❌ |
| Time | „kolik je hodin v Tokiu" | ❌ |
| Sequential Thinking | „rozmysli jak X" | ❌ |
| Puppeteer | „screenshot webu X" | ❌ |
| Computer Control | klikání, psaní, okna | ❌ |
| Brave Search | „vyhledej novinky o X" | ✅ |

---

## Web dashboard (Python)

```bash
python dashboard.py        # spustí na localhost:8002
# nebo automaticky při startu JARVIS
```

Zobrazí: stav systému, živé logy, audit trail, scheduler, stav agentů.

---

## React Web UI

Moderní frontend s 3D orbem, real-time chatem a monitoringem systému.

```bash
cd web
npm install
npm run dev          # vývojový server — http://localhost:5173

# nebo build pro produkci:
npm run build        # výstup do web/dist/
```

**Konfigurace (volitelné):**
```bash
# web/.env
VITE_API_URL=http://localhost:8002   # výchozí, změň pokud backend běží jinde
```

**Co Web UI obsahuje:**

| Komponenta | Popis |
|---|---|
| `OrbScene` | 3D orb (Three.js / @react-three/fiber) — animuje se při přemýšlení |
| `ChatPanel` | Chat s WebSocket streamingem (`/ws/chat`) + REST fallback |
| `StatusBar` | Stav Ollamy, aktivní model, CPU / RAM / disk v reálném čase |
| `ParticleBackground` | Animované hvězdné pole (1 500 částic) |
| `PluginStore` | Přehled a instalace pluginů přímo z UI |
| `SystemPanel` | Metriky a živé logy backendu |

**WebSocket streaming:**
Backend (`dashboard.py`) vystavuje `/ws/chat` — odpovědi se streamují po chunkcích, bez čekání na celou odpověď. Fallback na REST (`/api/chat`) pokud WebSocket není dostupný.

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 390+ testů, 0 failed
```

### Testovací sady

| Soubor | Počet | Pokrývá |
|---|---|---|
| `test_jarvis.py` | 108 | Integrace — celý stack |
| `tests/test_agent_graph.py` | 27 | Graf agent — uzly, retry, timeout |
| `tests/test_integration.py` | 30 | Security pipeline, sandbox, path |
| `tests/test_commands.py` | 24 | CommandExecutor — 40+ akcí |
| `tests/test_security.py` | 22 | Oprávnění, audit log |
| `tests/test_new_modules.py` | 23 | Health check, cache, offline, async |
| `tests/test_async_utils.py` | 16 | AsyncEngine — priority, cleanup |
| `tests/test_react_agent.py` | 17 | ReAct — parsing, tool calls |
| `tests/test_event_bus.py` | 13 | EventBus — subscribe, timeout |
| `tests/test_vision.py` | 15 | OCR, screen describe |
| ostatní | ~95 | STT, TTS, marketplace, embeddingy… |

### Přidání nové akce (5 kroků)

```python
# 1. Pattern v local_router.py
re.compile(r"\b(muj\s+prikaz)\b")  →  ("muj_akce", args)

# 2. Handler v commands/utils.py
def cmd_muj_prikaz(param: str) -> str: ...

# 3. Export z commands/__init__.py
from .utils import cmd_muj_prikaz

# 4. Security level v security_v2.py
"muj_prikaz": PermissionLevel.STANDARD

# 5. Test v tests/test_commands.py
def test_muj_prikaz(): ...
```

---

## Troubleshooting

| Problém | Řešení |
|---|---|
| Ollama nespustí | `ollama serve && ollama pull qwen2.5:3b` |
| JARVIS neslyší | `sudo usermod -a -G audio $USER` + logout |
| TTS nefunguje | `sudo apt install ffmpeg && pip install edge-tts` |
| MCP nefunguje | `node --version` (18+), `pip install mcp` |
| Brave Search | `cat .env \| grep BRAVE`, `pip install python-dotenv` |
| OCR nefunguje | `sudo apt install tesseract-ocr tesseract-ocr-ces` |
| Vision / LLaVA | `ollama pull llava:7b && pip install opencv-python` |
| Embeddingy | `pip install sentence-transformers` |
| Fuzzy matching | `pip install rapidfuzz` |
| Vosk offline STT | `pip install vosk` + model z [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) do `~/.vosk/` |
| Plugin odmítnut | Přidej `permissions` do `manifest.json` |
| Health check offline | `curl http://localhost:11434/api/tags` |

---

## Roadmapa

- [ ] `pip install jarvis-assistant` — instalace jedním příkazem
- [ ] Docker image (headless server mód)
- [x] Webové GUI (React + Three.js, WebSocket streaming) ✓
- [ ] Plugin autoupdate (verze v manifestu)
- [ ] OfflineManager integrace do routing pipeline
- [ ] Spotify Web API (aktuálně fallback na `xdg-open`)
- [ ] Rate limiting LLM
- [ ] Kontext aktivního okna v system promptu

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP servery)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`
- Linux (Ubuntu 22.04+ nebo Arch) — macOS experimentálně

---

## Licence

MIT — volně šiřitelný a upravitelný.

---

<details>
<summary>📋 Kompletní architekturní přehled modulů</summary>

```
jarvis.py               — bootstrap, entry point
app_core.py             — orchestrátor, lazy init, lifecycle
config.py               — centrální konfigurace (v4.2.0)

── Routing ──────────────────────────────────────────
local_router.py         — LocalRouter: regex + fuzzy, 95% bez LLM
llm.py                  — LLMEngine: history, token budget, streaming
llm_router.py           — LLMRouter: TaskType → model/temperature/tokens

── Agenti ───────────────────────────────────────────
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_react.py          — ReAct agent (Thought→Action→Observation)
agent_tools.py          — ToolRegistry (16+ nástrojů pro agenty)

── Paměť & Personalizace ────────────────────────────
memory.py               — SQLite + EmbeddingEngine + DailySummarizer
user_profile.py         — permanentní fakta (jméno, město, zájmy)

── Pluginy ──────────────────────────────────────────
plugin_system.py        — ManifestValidator + sandbox (AST) + lazy loading
plugin_marketplace.py   — 7 pluginů v REGISTRY, builtin + GitHub ZIP

── Vstup/Výstup ─────────────────────────────────────
tts.py                  — streaming TTS (edge-tts → ffplay stdin) + pyttsx3
stt.py                  — Google STT + VoskSTT offline fallback
vision.py               — OCR, screen describe, webcam + LLaVA
wake_word_detector.py   — detekce „JARVISe", pause/resume s STT

── Bezpečnost ───────────────────────────────────────
security_v2.py          — AuditLog, 5 úrovní oprávnění, confirmation dialog
mcp_bridge.py           — MCP klient (9 serverů)

── Infrastruktura ───────────────────────────────────
health_check.py         — monitoring Ollama, RAM, disk, CPU
cache_manager.py        — LRU + disk cache pro LLM a API
offline_mode.py         — fronta příkazů + fallback knowledge base
async_utils.py          — AsyncEngine: prioritní fronta (4 workers)
event_bus.py            — PUB/SUB, daemon callbacky s 5s timeoutem
agents.py               — background monitoring (CPU/RAM/disk)
scheduler.py            — at/after/every/every_day_at
error_handling.py       — centrální error handler + recovery

── Příkazy ──────────────────────────────────────────
commands/system.py      — čas, datum, hlasitost, jas, shutdown
commands/apps.py        — open/kill/install aplikace
commands/files.py       — soubory, web, clipboard
commands/media.py       — screenshot, youtube, timer, klávesnice
commands/utils.py       — kalkulačka, překlad, poznámky, wiki, počasí

── Web & GUI ────────────────────────────────────────
dashboard.py            — FastAPI web UI (localhost:8002)
gui/app_window.py       — Tkinter: chat, orb, settings
gui/settings.py         — SettingsDialog (STT, TTS, MCP, logy)
```
</details>
