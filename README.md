# JARVIS v4.5 — Lokální AI asistent

> Ovládej celý počítač hlasem nebo textem. Běží **100 % lokálně** — žádný cloud, žádný API klíč.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-456%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.5.0-orange)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Co je nového v v4.5

| Změna | Detail |
|---|---|
| **Sidebar redesign** | Nav skupiny (NÁSTROJE / INTELIGENCE / MONITOR), live CPU, New Chat, Ctrl+K paleta |
| **Sport & zprávy v chatu** | ESPN API výsledky, novinky přes DuckDuckGo — bez otevírání prohlížeče |
| **Pulsující orb** | Animovaný orb na prázdné chat stránce se suggestion chipsami |
| **Chat redesign** | Centrovaný ChatGPT styl, zprávy od spodu, plynulé bubliny |
| **Memory Graph** | Force-directed SVG graf paměti — uzly, hrany, fyzika, hledání |
| **Whisper STT** | `faster-whisper` — přesnější než Vosk, tiny/base/small/medium |
| **Agent Timeline** | Unified timeline: plan→route→execute→critic, expandovatelné kroky |
| **Auto-skill gen** | Prompt → LLM → `skill.py` + `manifest.json` → uložení do `plugins/custom/` |
| **Docker headless** | `docker compose up -d` — Ollama + JARVIS backend + web UI |
| **Open-Meteo počasí** | WMO emoji, bez API klíče, automatická geolokace |
| **Hardware info** | `cmd_hardware_info()` — CPU, RAM, disk, GPU |
| **Silero VAD** | Opt-in voice activity detection (torch) — přesné zachycení řeči |
| **Memory TTL/priority** | Expirující a prioritní vzpomínky |
| **OllamaClient.call_json()** | Strukturované výstupy přes `format:"json"` |

---

## Quickstart — 3 kroky

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_jarvis.sh          # → http://localhost:8002/app
```

### Způsoby spuštění

```bash
python jarvis.py               # backend + prohlížeč (výchozí)
python jarvis.py --webview     # nativní pywebview okno
python jarvis.py --tray        # systémový tray
python jarvis.py --gui         # klasické Tkinter okno
python jarvis.py --dashboard   # jen backend

# Dev mode (hot-reload)
cd web && npm run dev          # Vite → localhost:3000 (proxy na :8002)
python dashboard.py            # backend
```

### Volitelné závislosti

```bash
pip install vosk                   # Offline STT — Czech model ~50 MB
pip install faster-whisper         # Whisper STT — přesnější, offline
pip install sentence-transformers  # Sémantická paměť — embeddingy ~400 MB
pip install rapidfuzz              # Fuzzy matching překlepů
pip install torch                  # Silero VAD — detekce řeči v hluku
pip install pystray pillow         # Systémový tray (--tray mód)
ollama pull llava:7b               # Vision — popis obrazovky, webcam
sudo apt install tesseract-ocr tesseract-ocr-ces  # OCR
```

---

## Web UI — React (`localhost:3000` / `localhost:8002/app`)

```
┌─────────────────────────────────────────────────────────────┐
│ J JARVIS  Lokální AI asistent          ⌘K   ● Připojeno    │
├─────────────────┬───────────────────────────────────────────┤
│ + Nový chat     │                                           │
│                 │                                           │
│ ─ NÁSTROJE ─    │           [pulsující orb]                 │
│   Systém        │                                           │
│   Pluginy       │    Co pro tebe mohu udělat?               │
│   Skill Gen     │                                           │
│                 │   [sport výsledky] [zprávy] [počasí]      │
│ ─ INTELIGENCE ─ │   [screenshot] [kalkulačka] [překlad]     │
│   Agent         │                                           │
│   Timeline      │   ┌─────────────────────────────────┐    │
│   Paměť         │   │ Napiš příkaz nebo otázku...   ↑ │    │
│                 │   └─────────────────────────────────┘    │
│ ─ MONITOR ─     │                                           │
│   Dashboard     │                                           │
└─────────────────┴───────────────────────────────────────────┘
```

### Taby a jejich funkce

| Tab | Popis |
|---|---|
| **Chat** | Hlavní konverzace, streaming, markdown, historie |
| **Systém** | CPU / RAM / disk arc ringly, sparklines, Ollama status |
| **Pluginy** | Plugin marketplace — instalace, stav, rating |
| **Skill Gen** | Prompt → LLM → vygenerovaný plugin, uložení jedním kliknutím |
| **Agent** | SVG vizualizace Planner→Router→Executor→Critic pipeline |
| **Timeline** | Historie agentních runů — kroky, výsledky, timing |
| **Paměť** | Force-directed SVG knowledge graph, hledání, detail uzlu |
| **Dashboard** | CPU / RAM / disk, Ollama, agenti, scheduler, audit log, logy |

### Klávesové zkratky

| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat |
| `Shift+Enter` | Nový řádek |
| `Ctrl+K` | Command palette |
| `Ctrl+L` | Vymazat chat |
| `1`–`8` | Přejít na tab (při focus mimo input) |

---

## Co JARVIS umí

### Ovládání PC (bez LLM — okamžitě)

```
"Otevři Chrome / Discord / Spotify"   → spustí aplikaci
"Zavři Discord"                        → ukončí proces
"Hlasitost na 60 / Ztlum"             → zvuk
"Jas na 70"                           → jas obrazovky
"Screenshot"                           → PNG na plochu
"Vytvoř / Smaž složku X"              → souborové operace + undo stack
"Vrať poslední akci"                   → undo (20 kroků)
"Jaké máš komponenty"                  → CPU, RAM, GPU, disk
"Vypni / Restartuj počítač"            → shutdown / restart
```

### Sport & zprávy přímo v chatu

```
"Fotbal výsledky"           → ESPN API, živé skóre
"Premier League"            → tabulka + výsledky
"Champions League dnes"     → dnešní zápasy
"Hokej NHL"                 → výsledky ze zámoří
"Zprávy tech"               → DuckDuckGo novinky bez prohlížeče
"Kurzy bitcoin"             → kryptoměny
"Novinky Česko"             → aktuální zprávy
```

### Počasí (Open-Meteo, bez API klíče)

```
"Počasí Praha"     → 🌧️ Praha: Slabý déšť 🌡️ 15°C 💧 80% 💨 6 km/h
"Počasí Brno"      → WMO emoji + teplota + vlhkost + vítr
"Počasí"           → automatická geolokace
```

### Vision & AI

```
"Co vidíš na obrazovce?"   → Screenshot + LLaVA popis
"Přečti text z okna"       → OCR (pytesseract)
"Zapni kameru"             → webcam + LLaVA
"Přelož hello world"       → Ollama překlad
"Vypočítej 15 % z 3 400"   → AST sandbox kalkulátor
"Co je strojové učení?"    → Wikipedia + Ollama
"100 USD na CZK"           → měnový konvertor
```

### ReAct & Graf agent

```
"Najdi cenu RTX 4090 a ulož ji do poznámky"
→ Thought → Action: web_search → Observation → note_add → Answer

"Sestav report o cenách GPU"
→ Planner → Router → Executor → Critic (×N) → Answer
```

---

## MCP integrace (9 serverů)

> `node --version` ≥ 18 · `pip install mcp`

| Server | Příkaz | API klíč |
|---|---|---|
| Filesystem | „přečti soubor X", „strom ~/Projekty" | ❌ |
| Fetch | „načti stránku github.com" | ❌ |
| Git | „git log", „git status" | ❌ |
| Memory Graph | „zapamatuj si X", „co víš o X" | ❌ |
| Time | „kolik je hodin v Tokiu" | ❌ |
| Sequential Thinking | „rozmysli jak X" | ❌ |
| Puppeteer | „screenshot webu X" | ❌ |
| Computer Control | klikání, psaní, okna | ❌ |
| Brave Search | „vyhledej novinky o X" | ✅ `BRAVE_API_KEY` |

---

## Plugin systém

```
plugins/custom/muj_plugin/
  ├── manifest.json    ← metadata + permissions
  └── skill.py         ← handler (sandbox: AST kontrola importů)
```

### Rychlé vytvoření pluginu — Skill Gen tab

1. Otevři tab **Skill Gen** v web UI
2. Napiš co má plugin dělat (nebo vyber příklad)
3. Klikni **Generovat** → LLM vygeneruje `skill.py` + `manifest.json`
4. Klikni **Uložit plugin** → uloží do `plugins/custom/`

### Ručně

```json
{
  "name": "muj_skill", "version": "1.0.0",
  "description": "Co dělá", "permissions": ["answer"],
  "triggers": ["klíčové slovo"]
}
```

```python
import re
_RE = re.compile(r"\b(klicove\s+slovo)\b", re.IGNORECASE)
def _handle(text): return "Odpověď!", {"action": "answer", "params": {}}
def get_routes():   return [{"pattern": _RE, "handler": _handle}]
def get_actions():  return {}
```

### Sandbox permissions

| Permission | Odemkne |
|---|---|
| `answer` | stdlib — jen text odpovědi |
| `system` | os, subprocess, psutil, pyautogui |
| `files` | os.path, shutil, glob, pathlib |
| `media` | subprocess, webbrowser, yt_dlp |
| `mcp` | mcp_bridge, config, memory |
| `internal` | interní JARVIS moduly |

---

## Docker (headless server / NAS)

```bash
# Spuštění
docker compose up -d

# Web UI dostupné na
http://localhost:8002/app
```

`docker-compose.yml` spustí dvě služby:
- **ollama** — Ollama server s health checkem
- **jarvis** — FastAPI backend + React web UI (port 8002)

---

## Architektura souborů

```
jarvis.py               — vstupní bod (výchozí: web launcher)
config.py               — konfigurace, __version__ = "4.5.0"
dashboard.py            — FastAPI backend (port 8002, /app, /api/*, /ws/*)
routing.py              — CommandRouter — routing pipeline

# AI Engine
llm.py                  — LLMEngine + OllamaClient (+ call_json)
local_router.py         — LocalRouter — 95%+ příkazů bez LLM
llm_router.py           — výběr modelu dle typu úkolu
context_orchestrator.py — aktivní okno, clipboard → system prompt

# Agenti
agent_react.py          — ReAct (Thought→Action→Observation)
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_roles.py          — Multi-agent role + CriticAgent
agent_tools.py          — ToolRegistry (16+ nástrojů)

# Vstup/Výstup
tts.py                  — edge-tts streaming + pyttsx3
stt.py                  — Google STT + VoskSTT + WhisperSTT + Silero VAD
vision.py               — OCR, screen describe, webcam + LLaVA

# Paměť
memory.py               — SQLite + EmbeddingEngine + TTL/priority + conflict
user_profile.py         — permanentní fakta o uživateli

# Pluginy
plugin_system.py        — sandbox (AST) + health_check
plugin_marketplace.py   — REGISTRY + GitHub ZIP + auto-update

# Infrastruktura
security_v2.py          — AuditLog, 5 úrovní, confirmation
mcp_bridge.py           — MCP klient (9 serverů)
health_check.py         — monitoring Ollama, RAM, disk, CPU
event_bus.py            — PUB/SUB, daemon callbacky s 5s timeoutem
scheduler.py            — at/after/every (formát: 1d/1h/5m)
offline_mode.py         — fronta příkazů + fallback KB

# Commands (54 akcí)
commands/system.py      — čas, datum, hlasitost, jas, hardware, shutdown
commands/apps.py        — open/kill/install aplikace
commands/files.py       — soubory, web, clipboard, undo stack
commands/media.py       — screenshot, youtube, timer, klávesnice, vision
commands/utils.py       — kalkulačka, překlad, počasí, wiki, sport, zprávy

# Web (React + Vite)
web/src/App.jsx              — sidebar nav skupiny, taby
web/src/store/jarvis.js      — Zustand, WS, REST fallback, toasty
web/src/components/
  ChatPanel.jsx             — chat, streaming, markdown, orb animace
  SystemPanel.jsx           — arc ringly, sparklines, advanced metriky
  AgentGraph.jsx            — SVG pipeline vizualizace
  AgentTimeline.jsx         — unified agent timeline
  MemoryGraph.jsx           — force-directed SVG knowledge graph
  SkillGenerator.jsx        — auto-skill gen UI
  DashboardPanel.jsx        — full monitoring panel
  CommandPalette.jsx        — Ctrl+K rychlé příkazy
  PluginStore.jsx           — marketplace UI
  AIOrb.jsx                 — GLSL orb + Canvas 2D fallback
```

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 456 testů, 0 failed
```

### Přidání nové akce

```python
# 1. Pattern v local_router.py
re.compile(r"\b(muj\s+prikaz)\b") → ("muj_akce", args)

# 2. Handler v commands/utils.py
def cmd_muj_prikaz(param: str) -> str: ...

# 3. Export z commands/__init__.py
from .utils import cmd_muj_prikaz

# 4. Security level v security_v2.py
# 5. Test v tests/test_commands.py
```

---

## Troubleshooting

| Problém | Řešení |
|---|---|
| Backend neodpovídá | `curl http://localhost:8002/health` → `python dashboard.py` |
| Ollama nespustí | `ollama serve && ollama pull qwen2.5:3b` |
| Agent tab OFFLINE | Backend musí běžet (`python dashboard.py`) |
| TTS nefunguje | `sudo apt install ffmpeg && pip install edge-tts` |
| JARVIS neslyší | `sudo usermod -a -G audio $USER` + logout |
| MCP nefunguje | `node --version` ≥ 18, `pip install mcp` |
| OCR nefunguje | `sudo apt install tesseract-ocr tesseract-ocr-ces` |
| Embeddingy | `pip install sentence-transformers` |
| Whisper STT | `pip install faster-whisper` |

---

## Požadavky

- Python 3.11+
- Node.js 18+ (web frontend)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Licence

MIT — volně šiřitelný a upravitelný.
