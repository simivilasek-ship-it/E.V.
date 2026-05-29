# JARVIS v4.4 — Lokální AI asistent

> Ovládej celý počítač hlasem nebo textem. Běží **100 % lokálně** — žádný cloud, žádný API klíč (kromě volitelného Brave Search).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-448%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.4.0-orange)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Co je nového v v4.4

| Změna | Detail |
|---|---|
| **Context Orchestrator** | Aktivní okno, clipboard, čas, systém → automaticky v každém LLM dotazu |
| **Multi-agent role** | PlannerAgent, ResearcherAgent, ExecutorAgent, CriticAgent |
| **Plugin health check** | `health_check()` — status/routes/actions pro každý plugin |
| **Advanced metrics** | CPU teplota, síťová aktivita KB/s, GPU usage % |
| **Router DSL** | Mini DSL: `"nastav hlasitost {num}"` → action + coerce |
| **Memory TTL/priority** | `ttl_seconds`, `priority` — expirující a prioritní vzpomínky |
| **Marketplace rating** | ★ rating, verze, auto-update, check_updates() |
| **Agent Graph viz** | 4. tab AGENT — SVG vizualizace Planner→Router→Executor→Critic |
| **Toast notifikace** | WS events → UI toasty (success/warning/error) |
| **Sandbox fix** | `re.compile()` povoleno, jen bare `compile()` zakázáno. 15/15 healthy |

---

## Quickstart

### Desktop app (doporučeno — nativní okno se sci-fi HUD)
```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_desktop.sh
```

### Web UI (prohlížeč)
```bash
cd web && npm install && npm run dev   # → http://localhost:3000
python dashboard.py                    # backend API → port 8002
```

### Klasická Tkinter GUI
```bash
source ~/Stažené/jarvis-env/bin/activate
bash start_jarvis.sh
```

### Volitelné závislosti
```bash
# Offline STT (Vosk)
pip install vosk
# Model stáhne JARVIS automaticky (~50 MB)

# Vision / OCR
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python

# Fuzzy matching příkazů
pip install rapidfuzz

# Lokální embeddingy (lepší paměť)
pip install sentence-transformers
```

---

## Rozhraní

### Desktop app — React HUD (`app_desktop.py`)

Nativní okno pywebview + FastAPI backend + React frontend.

```
┌─────────────────────────────────────────────────────────┐
│  J JARVIS v4.4  [CHAT] [PLUGINS] [SYSTEM] [AGENT]  ● CONNECTED │
├──────────────────────────────────────────────────────────┤
│                    │              │  SYSTEM METRICS       │
│   COMMUNICATION    │  🌐 Orb      │  CPU ████░ 23%       │
│                    │  (animated)  │  RAM ███░░ 31%       │
│   [chat messages]  │              │  DISK █░░░ 8%        │
│                    │  ○ IDLE      │                       │
│                    │              │  CPU HISTORY (60s)   │
│   ENTER COMMAND... │  [SHORTCUTS] │  ~~~~~~~~~~~~~~~~~   │
└──────────────────────────────────────────────────────────┘
```

Spuštění:
```bash
bash start_desktop.sh        # sestaví React + spustí okno
python app_desktop.py        # přímo (předpokládá web_dist/)
```

### Web dashboard (`dashboard.py`)
```bash
python dashboard.py          # localhost:8002
```

WebSocket `/ws/chat` — streaming LLM odpovědí chunk po chunku.

---

## Co umí

### Ovládání PC
| Příkaz | Akce |
|---|---|
| „Otevři Chrome / Discord / Spotify" | Spustí aplikaci |
| „Zavři Chrome" | Ukončí proces |
| „Nainstaluj vlc" | `apt install` |
| „Smaž soubor test.txt" | Přesune do koše |
| „Vytvoř složku projekt" | `mkdir` |
| „Klikni na 500 300" | Computer Control MCP |
| „Seznam oken" | Otevřená okna |
| „Přepni na okno Chrome" | Aktivace okna |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Vision — Multi-modalita
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA |
| „Přečti text / OCR" | pytesseract OCR |
| „Zapni kameru / Webcam" | cv2 záběr + LLaVA |

### Audio & klávesnice
| Příkaz | Akce |
|---|---|
| „Hlasitost na 60 / Ztlum" | PulseAudio / ALSA |
| „Jas na 70" | brightnessctl / xrandr |
| „Screenshot" | PNG na plochu |
| „Napiš Hello World" | Simulace klávesnice |
| „Stiskni Ctrl+C" | pyautogui |

### YouTube & média
| Příkaz | Akce |
|---|---|
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay streaming |
| „Stáhni video X" | yt-dlp download |
| „Info o videu X" | Metadata bez stažení |

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Kolik je hodin v Tokiu" | MCP Time server |
| „Počasí Praha" | wttr.in |
| „Co je Python?" | Wikipedia |
| „Přelož hello world" | Ollama překlad |
| „Vypočítej 15% z 200" | AST sandbox kalkulačka |
| „100 USD na CZK" | Měnový konvertor |
| „Zapamatuj si X" | SQLite memory (TTL/priority) |
| Obecná otázka / kód | Ollama LLM |

### ReAct agent (vícesvůlové úkoly)
```
„Najdi cenu RTX 4090 a ulož ji do poznámky"
→ Plan → Search → Note → Done
```

### Multi-agent role
```python
multi_agent.run("Najdi alternativy k PostgreSQL a porovnej je")
# PlannerAgent:    1. Vyhledej alternativy  2. Porovnej  3. Shrň
# ResearcherAgent: MySQL, SQLite, MongoDB, Redis...
# ExecutorAgent:   Provede kroky
# CriticAgent:     SUCCESS/RETRY hodnocení
```

### Plugin Marketplace
| Příkaz | Akce |
|---|---|
| „marketplace seznam" | Pluginy s ratingem ★ |
| „nainstaluj plugin X" | ZIP z GitHubu |
| „nainstaluj z github user/repo" | Přímá instalace |
| „zkontroluj aktualizace pluginů" | check_updates() |
| „aktualizuj všechny pluginy" | auto_update_all() |

### GUI klávesové zkratky
| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat |
| `Shift+Enter` | Nový řádek |
| `↑ ↓` | Historie příkazů |
| `Mezerník` | Mikrofon |
| `Ctrl+L` | Vymazat chat |
| `Ctrl+E` | Export `.md` |
| `Esc` | Focus input |

---

## MCP integrace (9 serverů)

> Požadavky: Node.js 18+ · `pip install mcp`

| Server | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | „přečti soubor X", „strom ~/Projekty" | ❌ |
| **Fetch** | „načti stránku github.com" | ❌ |
| **Git** | „git log", „git status", „git diff" | ❌ |
| **Memory Graph** | „zapamatuj si X", „co víš o X" | ❌ |
| **Time** | „kolik je hodin v Tokiu", „14:00 z Prahy" | ❌ |
| **Sequential Thinking** | „přemýšlej jak X", „rozlož na kroky X" | ❌ |
| **Puppeteer** | „screenshot webu X", „klikni na #id" | ❌ |
| **Computer Control** | klikání, psaní, okna, OCR | ❌ |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
# Klíč zdarma: https://api.search.brave.com/
```

---

## Plugin systém — 15 skills

```
plugins/custom/
├── calculator/              — AST sandbox kalkulačka (safe_eval)
├── clipboard/               — xclip / pyperclip
├── greeting/                — pozdravy dle denní doby
├── marketplace/             — stahování pluginů z GitHubu + rating
├── timer/                   — odpočet + hlasová notifikace
├── mcp_brave/               — Brave Search
├── mcp_computer_control/    — klikání, psaní, okna, OCR
├── mcp_fetch/               — DuckDuckGo + URL fetch
├── mcp_filesystem/          — čtení souborů, strom, hledání
├── mcp_git/                 — git log/status/diff/blame
├── mcp_memory/              — knowledge graph
├── mcp_puppeteer/           — browser automation
├── mcp_sequential_thinking/ — krok-za-krokem plánování
├── mcp_time/                — časová pásma (40+ měst)
└── [system]                 — vestavěný systémový plugin
```

### Přidání vlastního pluginu

```json
// plugins/custom/muj_skill/manifest.json
{
  "name": "muj_skill",
  "version": "1.0.0",
  "description": "Co skill dělá",
  "permissions": ["answer"],
  "triggers": ["klíčové slovo"]
}
```

**Permissions:** `answer` · `system` · `media` · `files` · `mcp` · `internal` · `safe_eval`

```python
# skill.py
import re
_RE = re.compile(r"\b(klicove\s+slovo)\b", re.IGNORECASE)
def _handle(text): return "Odpověď!", {"action": "answer", "params": {}}
def get_routes():   return [{"pattern": _RE, "handler": _handle}]
def get_actions():  return {}
```

---

## Smart Memory

### User Profile (`~/.jarvis_user_profile.json`)
- „jmenuji se Petr" → `jméno: Petr`
- Vkládá se do každého LLM dotazu

### SQLite Memory (`memory_data/memories.db`)
```python
# TTL — expirující vzpomínky
mem.store("dočasná info", ttl_seconds=3600)   # expiruje za 1h

# Priority — důležité vzpomínky dřív ve výsledcích
mem.store("kritická info", priority=2)         # 0=normal, 1=high, 2=critical

# Maintenance — smaže expirované
mem.run_maintenance()  # → {"deleted_expired": 3, "total": 45}
```

### MCP Knowledge Graph (`~/.jarvis_mcp_memory/`)
- Entity a vztahy přes `@modelcontextprotocol/server-memory`

### Context Orchestrator
```
Každý LLM dotaz automaticky obsahuje:
  Aktuální čas: 14:32, Friday 29.05.2026
  Aktivní okno: VS Code — app_core.py
  Obsah schránky: def my_function()...
  Systém: CPU 23%, RAM 31%
```

---

## Architektura

```
jarvis.py               — bootstrap + CLI args
app_core.py             — orchestrátor (EventBus, Agents, MCP, GUI)
config.py               — konfigurace, __version__ = "4.4.0"

# AI Engine
llm.py                  — LLMEngine + OllamaClient
local_router.py         — LocalRouter (95% příkazů bez LLM)
llm_router.py           — výběr modelu dle typu úkolu
router_dsl.py           — mini DSL pro čitelné patterns
context_orchestrator.py — aktivní okno, clipboard, systém → system prompt

# Agenti
agent_react.py          — ReAct smyčka (Thought→Action→Observation)
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_roles.py          — Multi-agent role (Planner/Researcher/Executor/Critic)
agent_tools.py          — ToolRegistry (12 nástrojů)

# Vision
vision.py               — VisionEngine (OCR, screen describe, webcam)

# GUI
gui/                    — Tkinter/customtkinter OpenCode styl
  app_window.py         — JarvisGUI hlavní okno
  orb.py                — animovaný orb + MiniOrbCanvas
  chat.py               — chat panel, export
  settings.py           — SettingsDialog
  constants.py          — barvy, fonty

# Web
web/                    — React + Three.js + Vite
  src/components/
    AIOrb.jsx           — 3D GLSL shader orb
    ChatPanel.jsx       — streaming, markdown, history, suggestions
    SystemPanel.jsx     — arc rings, sparklines, Ollama status, advanced metrics
    AgentGraph.jsx      — SVG vizualizace agent pipeline
    PluginStore.jsx     — marketplace UI s health statusem
    Toast.jsx           — notifikace (success/warning/error)
  src/store/jarvis.js   — Zustand (WS backoff, REST fallback, toasts)
dashboard.py            — FastAPI backend (port 8002)
app_desktop.py          — pywebview nativní okno

# Commands
commands/
  system.py             — shutdown, hlasitost, jas, systém info
  apps.py               — open/kill/install aplikace
  media.py              — YouTube, screenshot, klávesnice, vision
  files.py              — soubory, clipboard, web
  utils.py              — kalkulačka, překlad, počasí + safe_run()

# Infrastructure
tts.py                  — edge-tts streaming + pyttsx3, queue worker
stt.py                  — Google STT + VoskSTT offline fallback
memory.py               — SQLite + EmbeddingEngine + TTL/priority
plugin_system.py        — ManifestValidator + sandbox + health_check
plugin_marketplace.py   — GitHub ZIP + rating + auto-update
mcp_bridge.py           — MCPBridge (9 serverů)
security_v2.py          — SAFE/STANDARD/ELEVATED + audit log
agents.py               — CPU/RAM monitor, idle detector
scheduler.py            — plánování úloh
event_bus.py            — pub/sub event systém
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes       (15 skills, sandbox timeout)
  ├─ 2. Lokální router     (95% příkazů bez LLM)
  │     └─ Router DSL      (čitelné patterns)
  ├─ 3. ReAct / Graf       (vícesvůlové úkoly)
  └─ 4. Ollama stream      (AI konverzace)
           │
           ├─ UserProfile kontext
           ├─ Memory kontext (TTL/priority + embedding similarity)
           └─ Context Orchestrator (aktivní okno, clipboard)
  │
  ▼
Security check → CommandExecutor / MCP / Vision → TTS streaming
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
  "tts_rate":               170,
  "tts_streaming":          true,
  "stt_language":           "cs-CZ",
  "wake_word":              "jarvis",
  "wake_word_enabled":      true,
  "plugin_handler_timeout": 5.0,
  "mcp_filesystem_enabled": true,
  "mcp_brave_enabled":      true
}
```

### .env
```bash
BRAVE_API_KEY=tvůj_klíč     # pro Brave Search MCP
```

### Modely Ollama
| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | Výchozí — rychlý |
| `llama3.1:8b` | ~8 GB | Lepší kvalita |
| `llava:7b`    | ~8 GB | Vision (popis obrazovky) |

### Security
- **SAFE** — vždy (čas, počasí, OCR, read-only)
- **STANDARD** — bez potvrzení (soubory, poznámky, webcam)
- **ELEVATED** — dialog (smazat, shutdown, instalace)

---

## Vývoj a testy

```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 448 testů, 0 failed
```

### Linter
```bash
ruff check . --select F821,F811,E711,E712
# All checks passed!
```

### CI/CD
GitHub Actions — Python 3.11 + 3.12, ruff lint + pytest, ubuntu-latest.

### Přidání nové akce
1. Pattern do `LocalRouter.route()` nebo `RouterDSL.rule()` v `local_router.py`
2. Implementace `cmd_nazev()` v `commands/`
3. Export z `commands/__init__.py`
4. Oprávnění do `security_v2.py`
5. Test do `tests/`

---

## Troubleshooting

### Backend neodpovídá
```bash
curl http://localhost:8002/health
# {"status":"healthy","ws":"running",...}
python dashboard.py   # spustí backend
```

### Ollama
```bash
curl http://localhost:11434/api/tags
ollama serve && ollama pull qwen2.5:3b
```

### TTS
```bash
sudo apt install ffmpeg mpg123 && pip install edge-tts
```

### STT offline (Vosk)
```bash
pip install vosk
# JARVIS stáhne model automaticky (~50 MB) při prvním použití
```

### Vision
```bash
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

### Plugin selže
```python
from plugin_system import create_plugin_manager
pm = create_plugin_manager()
pm.load_all_plugins()
print(pm.health_check())  # zobrazí status každého pluginu
```

### MCP nefunguje
```bash
node --version   # potřeba Node.js 18+
pip install mcp
```

---

## Požadavky

- **Python** 3.11+
- **Node.js** 18+ (MCP servery, web frontend)
- **[Ollama](https://ollama.com)** — `ollama pull qwen2.5:3b`
- **ffmpeg** — `sudo apt install ffmpeg`

```bash
pip install -r requirements.txt
```

---

## Plánované featury

- [ ] Docker image (headless server mód)
- [ ] Plugin autoupdate (VERSION check + cron)
- [ ] Rate limiting LLM (token bucket)
- [ ] Lokální Whisper STT (offline, přesný)
- [ ] Electron wrapper (cross-platform desktop)

---

## Licence

MIT — volně šiřitelný a upravitelný.
