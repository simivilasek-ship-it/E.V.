# JARVIS v4.6 — Lokální AI asistent

> Ovládej celý počítač hlasem nebo textem. Běží **100 % lokálně** — žádný cloud, žádný API klíč.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-519%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.6.0-orange)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Co je nového v v4.6

| Změna | Detail |
|---|---|
| **Hero Panel** | Prázdný chat = dashboard: pozdrav, hodiny, CPU/RAM/model, 8 quick akcí, agenti |
| **Alt+Space Spotlight** | Inline widgets — počasí, sport, systém, hodiny, kalkulačka bez otevření chatu |
| **ContextOrchestrator v2** | JARVIS vidí okna přes ewmh (python-xlib) — bez xdotool/wmctrl |
| **MCP +6 serverů** | GitHub, Google Maps, Slack, YouTube Transcript, SQLite, Everything |
| **Grid opacity fix** | Mřížka v pozadí snížena na opacity 0.015 — méně dominantní |
| **System prompt fix** | Model ví že vidí okna/clipboard, nepíše "nemám přístup" |
| **LLM cache** | LRU cache TTL 10 min — opakované dotazy okamžitě |
| **Paralelní agenti** | `run_parallel()` — kroky ve 2 vlnách přes ThreadPoolExecutor |
| **519 testů** | 0 failed, TypeScript build OK |

---

## Quickstart

### Desktop app (doporučeno)
```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_desktop.sh   # pywebview okno
```

### Web UI — Next.js (localhost:3000)
```bash
# Terminál 1 — Python backend
source ~/Stažené/jarvis-env/bin/activate && python dashboard.py

# Terminál 2 — Next.js frontend
cd web && npm install && npm run dev
```

### Klasická Tkinter GUI
```bash
source ~/Stažené/jarvis-env/bin/activate
bash start_jarvis.sh
```

### Volitelné závislosti
```bash
pip install vosk              # Offline STT (~50 MB model)
pip install faster-whisper    # Přesnější offline STT (GPU)
pip install pynput            # Global Hotkey (Alt+Space)
pip install sentence-transformers  # Lepší paměť (embeddingy)
pip install pytesseract opencv-python  # OCR + webcam
ollama pull llava:7b          # Vision — popis obrazovky
```

---

## Rozhraní

### Next.js Web UI — `http://localhost:3000`
```
Sidebar        │  Main panel
─────────────  │  ──────────────────────────────────────
KOMUNIKACE     │  Chat s JARVIS (streaming, markdown)
System         │  SystemPanel (CPU/RAM arc rings, sparklines)
Pluginy        │  Plugin marketplace + health check
Agent          │  AgentGraph vizualizace
Timeline       │  Agent kroky v čase
Paměť          │  MemoryGraph — znalostní graf
Skill Gen      │  AI generátor pluginů
Dashboard      │  Monitoring, logy, audit
```

### Global Hotkey — `Alt+Space`
Kdekoliv v OS → minimalistické okno (Spotlight styl):
- Přímý chat s JARVIS
- Mini-widgets: počasí, sport výsledky, systém info
- Rychlé akce: screenshot, timer, poznámka

### API backend — `http://localhost:8002`
```
GET  /health              → {"status":"healthy","ws":"running","version":"4.6.0"}
GET  /api/system          → CPU, RAM, disk, temp, síť, GPU
GET  /api/plugins         → 15 skills s health statusem
POST /api/command         → {"command": "..."} → {"response": "..."}
POST /api/config          → {"ollama_model": "..."} → uloží do config.json
GET  /ws/logs             → WebSocket live logy
GET  /ws/agents           → WebSocket CPU/RAM každé 2s
GET  /ws/chat             → WebSocket streaming chat
```

---

## Co umí

### Ovládání PC
| Příkaz | Akce |
|---|---|
| „Otevři Chrome / Discord / Spotify" | Spustí aplikaci |
| „Zavři Chrome" | Ukončí proces |
| „Nainstaluj vlc" | `apt install` |
| „Smaž soubor test.txt" | Přesune do koše |
| „Vytvoř soubor notes.md" | `touch` |
| „Přesuň a.txt do b.txt" | `mv` |
| „Spusť skript setup.py" | `python/bash` |
| „Otevři ve VS Code ~/projekt" | `code .` |
| „Klikni na 500 300" | Computer Control MCP |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Hardware & systém
| Příkaz | Akce |
|---|---|
| „Jaký mám hardware" | CPU, RAM, GPU, disk, OS |
| „Kolik mám místa na disku" | Přehled všech oddílů |
| „Co mám na ploše" | Obsah ~/Plocha s velikostmi |
| „Obsah složky ~/Dokumenty" | Libovolná cesta |
| „Info o systému" | CPU/RAM/Disk využití real-time |

### Vision — Multi-modalita
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA (uvolní VRAM po analýze) |
| „Přečti text / OCR" | pytesseract OCR |
| „Zapni kameru" | cv2 záběr + LLaVA |

### Sport & novinky (DuckDuckGo inline)
| Příkaz | Akce |
|---|---|
| „PSG vs Arsenal výsledek" | Výsledek přímo v chatu |
| „Tabulka premier league" | Živá tabulka |
| „Bitcoin cena" | Aktuální kurz |
| „Kdo vyhrál ligu mistrů" | DuckDuckGo odpověď |

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Kolik je hodin v Tokiu" | MCP Time server |
| „Počasí Praha" | Open-Meteo (offline) |
| „Co je Python?" | Wikipedia |
| „Přelož hello world" | Ollama překlad |
| „Vypočítej 15% z 200" | AST sandbox |
| „100 USD na CZK" | Měnový konvertor |
| „Zapamatuj si X" | SQLite memory (TTL/priority) |

### ReAct & Multi-agent
```
„Najdi cenu RTX 4090 a ulož do poznámky"
→ PlannerAgent → ResearcherAgent → ExecutorAgent → CriticAgent → Done
```

### GUI zkratky
| Zkratka | Akce |
|---|---|
| `Alt+Space` | Global Spotlight (kdekoliv v OS) |
| `Ctrl+K` | Command Palette v web UI |
| `↑ ↓` | Historie příkazů |
| `Enter` | Odeslat |
| `Shift+Enter` | Nový řádek |

---

## LLM Router v2 — automatický výběr modelu

| Typ úkolu | Detekce | Model |
|---|---|---|
| FAST | překlad, čas, datum | qwen2.5:1.5b |
| STANDARD | obecné dotazy | qwen2.5:3b |
| CODE | python, funkce, bug | deepseek-coder, qwen2.5:7b |
| MATH | integrál, rovnice | qwen2.5:7b |
| REASONING | analyzuj, porovnej | llama3.1:8b |
| VISION | obrazovka, kamera | llava:7b |
| AGENT | „najdi a ulož" | llama3.1:8b |

---

## MCP integrace (10 serverů)

> Požadavky: Node.js 18+ · `pip install mcp`

| Server | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | „přečti soubor X", „strom ~/Projekty" | ❌ |
| **Fetch** | „načti stránku github.com" | ❌ |
| **Git** | „git log", „git status", „git diff" | ❌ |
| **Memory Graph** | „zapamatuj si X", „co víš o X" | ❌ |
| **Time** | „kolik je hodin v Tokiu" | ❌ |
| **Sequential Thinking** | „rozlož na kroky X" | ❌ |
| **Puppeteer** | „screenshot webu X" | ❌ |
| **Computer Control** | klikání, psaní, okna | ❌ |
| **YouTube Transcript** | „titulky z videa X" | ❌ |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |

---

## Plugin systém — 15 skills

```
plugins/custom/
├── calculator/              — AST sandbox kalkulačka
├── clipboard/               — xclip / pyperclip
├── greeting/                — pozdravy dle denní doby
├── marketplace/             — GitHub marketplace + rating
├── timer/                   — odpočet + hlasová notifikace
├── mcp_brave/               — Brave Search
├── mcp_computer_control/    — klikání, psaní, okna
├── mcp_fetch/               — DuckDuckGo + URL fetch
├── mcp_filesystem/          — čtení souborů, strom
├── mcp_git/                 — git log/status/diff
├── mcp_memory/              — knowledge graph
├── mcp_puppeteer/           — browser automation
├── mcp_sequential_thinking/ — krok-za-krokem plánování
├── mcp_time/                — časová pásma (40+ měst)
└── [system]                 — vestavěný systémový plugin
```

### Plugin permissions (sandbox v2)

| Permission | Co povoluje |
|---|---|
| `answer` | Jen stdlib |
| `safe_eval` | AST-sandboxed eval |
| `files.read` | os.path, pathlib, glob |
| `files.write` | shutil, tempfile |
| `network.fetch` | requests.get |
| `system.exec` | subprocess ⚠️ |
| `vision.capture` | cv2, screenshot |
| `mcp` | mcp_bridge |

---

## Smart Memory

### SQLite Memory + TTL/Priority
```python
mem.store("dočasná info", ttl_seconds=3600)   # expiruje za 1h
mem.store("kritická info", priority=2)         # 0=normal, 2=critical
mem.run_maintenance()                          # smaže expirované
```

### Context Orchestrator
```
Každý LLM dotaz obsahuje:
  Aktivní okno: Firefox — GitHub
  Otevřená okna: [VS Code, Terminal]
  Systém: CPU 12%, RAM 38%
  Čas: 15:43, Monday 02.06.2026
```

### Memory Pruning
- Automaticky při >40 konverzacích
- Ollama zkondenzuje staré → fakta do user_profile
- Spouští se v DailySummarizer (každou půlnoc)

---

## Architektura

```
jarvis.py               — bootstrap + CLI
app_core.py             — orchestrátor (EventBus, Agents, MCP, GUI)
config.py               — __version__ = "4.6.0"

# AI
llm.py                  — LLMEngine + OllamaClient + LRU cache
local_router.py         — LocalRouter (95% příkazů bez LLM)
llm_router.py           — FAST/CODE/MATH/REASONING/VISION/AGENT routing
router_dsl.py           — mini DSL pro patterns
context_orchestrator.py — ewmh okna + clipboard → system prompt

# Agenti
agent_react.py          — ReAct smyčka
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_roles.py          — Multi-agent role
global_hotkey.py        — Alt+Space Spotlight (pynput)

# Vision
vision.py               — OCR + LLaVA + webcam (VRAM auto-uvolnění)

# Web — Next.js 16 + TypeScript
web/app/                — Next.js App Router
web/components/         — 14 TypeScript komponent
  JarvisApp.tsx         — hlavní layout + sidebar
  ChatPanel.tsx         — streaming, markdown, history
  SystemPanel.tsx       — arc rings, sparklines, metrics
  AgentGraph.tsx        — SVG pipeline vizualizace
  Spotlight.tsx         — Alt+Space overlay + widgets
  PluginStore.tsx       — marketplace s health check
web/store/jarvis.ts     — Zustand (WS backoff, toasts, model)
dashboard.py            — FastAPI backend (port 8002)
app_desktop.py          — pywebview nativní okno

# Commands
commands/
  system.py    — hardware_info, disk_space, list_directory, volume
  apps.py      — open/kill/install aplikace
  media.py     — YouTube, screenshot (5 fallbacků), klávesnice
  files.py     — soubory, clipboard, web
  utils.py     — kalkulačka, překlad, počasí, memory

# Infrastructure
tts.py                  — edge-tts streaming + pyttsx3
stt.py                  — Google STT + VoskSTT + WhisperSTT
memory.py               — SQLite + EmbeddingEngine + TTL + pruning
plugin_system.py        — ManifestValidator + sandbox v2 + health_check
mcp_bridge.py           — MCPBridge (10 serverů)
security_v2.py          — SAFE/STANDARD/ELEVATED + audit log
```

---

## Konfigurace

### config.json
```json
{
  "ollama_url":             "http://localhost:11434/api/chat",
  "ollama_model":           "qwen2.5:3b",
  "tts_enabled":            true,
  "tts_voice":              "cs-CZ-AntoninNeural",
  "tts_streaming":          true,
  "stt_language":           "cs-CZ",
  "whisper_model":          "small",
  "wake_word":              "jarvis",
  "plugin_handler_timeout": 5.0
}
```

### Modely Ollama
| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:1.5b` | ~1 GB | Rychlé (FAST) |
| `qwen2.5:3b` | ~3 GB | Výchozí |
| `qwen2.5:7b` | ~5 GB | Code, Math |
| `llama3.1:8b` | ~8 GB | Reasoning, Agent |
| `llava:7b` | ~8 GB | Vision |

---

## Vývoj a testy

```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 519 testů, 0 failed
```

### Linter
```bash
ruff check . --select F,E7
# All checks passed!
```

### Plugin health check
```python
from plugin_system import create_plugin_manager
pm = create_plugin_manager(); pm.load_all_plugins()
print(pm.health_check())  # 15/15 healthy
```

---

## Troubleshooting

### WebSocket ECONNREFUSED
```bash
# Backend musí běžet!
source ~/Stažené/jarvis-env/bin/activate && python dashboard.py
# Pak v druhém terminálu:
cd web && npm run dev
```

### Screenshot selže
```bash
sudo apt install gnome-screenshot  # automatický fallback
```

### Ollama
```bash
ollama serve && ollama pull qwen2.5:3b
```

### Vision / OCR
```bash
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

---

## Požadavky

- **Python** 3.11+
- **Node.js** 18+ (web, MCP servery)
- **[Ollama](https://ollama.com)** — `ollama pull qwen2.5:3b`
- **ffmpeg** — `sudo apt install ffmpeg`

```bash
pip install -r requirements.txt
```

---

## Přispívání

Viz [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Licence

MIT — volně šiřitelný a upravitelný.
