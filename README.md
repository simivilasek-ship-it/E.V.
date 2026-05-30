# JARVIS v4.4 — Lokální AI asistent

> Ovládej celý počítač hlasem nebo textem. Běží **100 % lokálně** — žádný cloud, žádný API klíč (kromě volitelného Brave Search).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-454%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.4.0-orange)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Co je nového v v4.4

| Změna | Detail |
|---|---|
| **Hardware detekce** | „jaký mám hardware" → CPU, RAM, GPU, disk, OS |
| **Disk space** | „kolik mám místa na disku" → přehled všech oddílů |
| **Procházení souborů** | „co mám na ploše" → seznam s emoji, velikostmi |
| **LLM Router v2** | 7 typů úkolů → automatický výběr nejlepšího modelu |
| **Command Palette** | `Ctrl+K` overlay — fuzzy search příkazů jako VS Code |
| **Plugin sandbox v2** | Granulární permissions: `files.read`, `network.fetch`, `system.exec`... |
| **Context Orchestrator** | Aktivní okno, clipboard, čas → každý LLM dotaz |
| **Multi-agent role** | PlannerAgent, ResearcherAgent, ExecutorAgent, CriticAgent |
| **Advanced metrics** | CPU teplota, síťová aktivita KB/s, GPU usage % |
| **Memory TTL/priority** | Expirující a prioritní vzpomínky |
| **Memory Graph** | Vizualizace znalostního grafu v UI |
| **Agent Timeline** | Kroky agentů v čase |
| **Skill Generator** | Generování nových skills přes AI |
| **Whisper STT** | Opt-in přesné offline STT (faster-whisper) |
| **Auto-update cron** | Plugin aktualizace 1× denně na pozadí |

---

## Quickstart

### Desktop app (doporučeno)
```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_desktop.sh   # spustí backend + React okno
```

### Web UI (prohlížeč)
```bash
# Terminál 1 — backend
source ~/Stažené/jarvis-env/bin/activate && python dashboard.py

# Terminál 2 — frontend
cd web && npm install && npm run dev   # → http://localhost:3000
```

### Klasická Tkinter GUI
```bash
source ~/Stažené/jarvis-env/bin/activate
bash start_jarvis.sh
```

### Volitelné závislosti
```bash
# Offline STT — Vosk (~50 MB, stáhne se automaticky)
pip install vosk

# Offline STT — Whisper (přesnější, GPU akcelerace)
pip install faster-whisper

# Vision / OCR
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python

# Fuzzy matching příkazů
pip install rapidfuzz

# Lokální embeddingy (lepší recall paměti)
pip install sentence-transformers
```

---

## Rozhraní

### Desktop app — React HUD (`app_desktop.py`)

Nativní okno pywebview + FastAPI backend + React frontend.

```
┌─────────────────────────────────────────────────────────────────┐
│  J JARVIS v4.4  [CHAT][PLUGINS][SYSTEM][AGENT][MEMORY][⌘K]  ●  │
├──────────────────────────────────────────────────────────────────┤
│                    │              │  SYSTEM METRICS              │
│   COMMUNICATION    │  🌐 AI Orb   │  ◯ CPU  ◯ RAM  ◯ DISK      │
│                    │  (3D GLSL)   │  ≈≈≈≈≈ CPU history          │
│   [chat messages]  │              │  ≈≈≈≈≈ RAM history          │
│   [suggestion]     │  ○ IDLE      │  ↓3.2 KB/s ↑0.8 KB/s       │
│   [chips]          │              │  OLLAMA ● ONLINE            │
│   ENTER COMMAND... │  [SHORTCUTS] │  LIVE LOG                   │
└──────────────────────────────────────────────────────────────────┘
```

### Command Palette — `Ctrl+K`
VS Code style overlay s fuzzy search:
- Navigace mezi taby
- Přepínání modelů (qwen/llama/llava)
- Rychlé příkazy (screenshot, disk, hardware, počasí)
- Spuštění pluginů

### Web dashboard — `python dashboard.py`
```
http://localhost:8002/health   → {"status":"healthy","ws":"running"}
http://localhost:8002/         → klasický monitoring dashboard
http://localhost:3000/         → React HUD (npm run dev)
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
| „Vytvoř složku projekt" | `mkdir` |
| „Klikni na 500 300" | Computer Control MCP |
| „Seznam oken" | Otevřená okna |
| „Přepni na okno Chrome" | Aktivace okna |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Hardware & systém
| Příkaz | Akce |
|---|---|
| „Jaký mám hardware" | CPU, RAM, GPU, disk, OS |
| „Kolik mám místa na disku" | Přehled všech oddílů |
| „Co mám na ploše" | Obsah ~/Plocha |
| „Co mám ve Stažených" | Obsah ~/Stažené |
| „Obsah složky ~/Dokumenty" | Libovolná cesta |
| „Info o systému" | CPU/RAM/Disk využití |

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

### ReAct & Multi-agent
```
„Najdi cenu RTX 4090 a ulož ji do poznámky"
→ PlannerAgent → ResearcherAgent → ExecutorAgent → CriticAgent → Done
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
| `Ctrl+K` | Command Palette |
| `Enter` | Odeslat |
| `Shift+Enter` | Nový řádek |
| `↑ ↓` | Historie příkazů |
| `Mezerník` | Mikrofon |
| `Ctrl+L` | Vymazat chat |
| `Ctrl+E` | Export `.md` |
| `Esc` | Zavřít palette / focus input |

---

## LLM Router v2 — automatický výběr modelu

| Typ úkolu | Detekce | Preferovaný model |
|---|---|---|
| FAST | krátký překlad, čas, datum | qwen2.5:1.5b, phi3:mini |
| STANDARD | obecné dotazy | qwen2.5:3b (výchozí) |
| CODE | python, funkce, kód, bug | deepseek-coder, qwen2.5:7b |
| MATH | integrál, rovnice, matice | qwen2.5:7b |
| REASONING | porovnej, analyzuj, proč | llama3.1:8b, qwen2.5:7b |
| VISION | obrazovka, kamera, screenshot | llava:7b |
| AGENT | „najdi a ulož", multi-step | llama3.1:8b |

Router automaticky zvolí nejlepší **dostupný** model z Ollama — pokud preferovaný není stažen, použije výchozí.

---

## MCP integrace (9 serverů)

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
| **Computer Control** | klikání, psaní, okna, OCR | ❌ |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
```

---

## Plugin systém — 15 skills

```
plugins/custom/
├── calculator/              — AST sandbox kalkulačka (safe_eval)
├── clipboard/               — xclip / pyperclip
├── greeting/                — pozdravy dle denní doby
├── marketplace/             — GitHub marketplace + rating ★ + auto-update
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

### Plugin permissions (sandbox v2)

| Permission | Co povoluje |
|---|---|
| `answer` | Jen stdlib, žádné extra moduly |
| `safe_eval` | AST-sandboxed eval (kalkulátor) |
| `files.read` | os.path, pathlib, glob |
| `files.write` | shutil, tempfile, open write |
| `network.fetch` | requests.get |
| `network.full` | Plný síťový přístup |
| `system.exec` | subprocess, os |
| `system.info` | psutil, platform (read-only) |
| `vision.capture` | cv2, pyautogui screenshot |
| `keyboard.input` | pyautogui, pyperclip |
| `mcp` | mcp_bridge přístup |
| `internal` | Interní JARVIS moduly |

### Přidání vlastního pluginu

```json
{
  "name": "muj_skill",
  "version": "1.0.0",
  "description": "Co skill dělá",
  "permissions": ["answer"],
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

Plugin se automaticky načte při startu. Sandbox s timeoutem zabrání zablokování JARVIS.

---

## Smart Memory

### User Profile (`~/.jarvis_user_profile.json`)
- „jmenuji se Petr" → `jméno: Petr`
- Vkládá se do každého LLM dotazu

### SQLite Memory + TTL/Priority
```python
mem.store("dočasná info", ttl_seconds=3600)  # expiruje za 1h
mem.store("kritická info", priority=2)        # 0=normal, 1=high, 2=critical
mem.run_maintenance()                         # smaže expirované
```

### Context Orchestrator
```
Každý LLM dotaz automaticky obsahuje:
  Aktuální čas: 14:32, Friday 30.05.2026
  Aktivní okno: VS Code — app_core.py
  Obsah schránky: def my_function()...
  Systém: CPU 23%, RAM 38%
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
llm_router.py           — v2: FAST/CODE/MATH/REASONING/VISION/AGENT routing
router_dsl.py           — mini DSL pro patterns
context_orchestrator.py — aktivní okno, clipboard → system prompt

# Agenti
agent_react.py          — ReAct smyčka
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_roles.py          — Multi-agent role
agent_tools.py          — ToolRegistry

# Vision
vision.py               — VisionEngine (OCR, screen describe, webcam)

# GUI
gui/                    — Tkinter OpenCode styl
web/                    — React + Three.js + Vite
  src/components/
    AIOrb.jsx           — 3D GLSL shader orb
    ChatPanel.jsx       — streaming, markdown, history, suggestions
    SystemPanel.jsx     — arc rings, sparklines, advanced metrics
    AgentGraph.jsx      — SVG agent pipeline vizualizace
    AgentTimeline.jsx   — kroky agentů v čase
    MemoryGraph.jsx     — vizualizace znalostního grafu
    PluginStore.jsx     — marketplace UI s health statusem
    CommandPalette.jsx  — Ctrl+K fuzzy command palette
    SkillGenerator.jsx  — AI generování nových skills
    Toast.jsx           — notifikace (success/warning/error)
  src/store/jarvis.js   — Zustand (WS backoff, REST fallback, toasts)
dashboard.py            — FastAPI backend (port 8002)
app_desktop.py          — pywebview nativní okno

# Commands
commands/
  system.py    — shutdown, hlasitost, jas, hardware_info, disk_space, list_directory
  apps.py      — open/kill/install
  media.py     — YouTube, screenshot, klávesnice, vision
  files.py     — soubory, clipboard
  utils.py     — kalkulačka, překlad, počasí + safe_run()

# Infrastructure
tts.py                  — edge-tts streaming + pyttsx3
stt.py                  — Google STT + VoskSTT + WhisperSTT
memory.py               — SQLite + EmbeddingEngine + TTL/priority
plugin_system.py        — ManifestValidator + sandbox v2 + health_check
plugin_marketplace.py   — GitHub ZIP + rating + auto-update + cron
mcp_bridge.py           — MCPBridge (9 serverů)
security_v2.py          — SAFE/STANDARD/ELEVATED + audit log
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes       (15 skills, sandbox v2, 3s timeout)
  ├─ 2. Lokální router     (přesná shoda → fuzzy → regex)
  │     └─ Router DSL      (čitelné patterns)
  ├─ 3. ReAct / Graf       (vícesvůlové úkoly)
  └─ 4. Ollama stream      (AI konverzace)
           │
           ├─ LLM Router v2 (výběr modelu dle úkolu)
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
  "whisper_model":          "small",
  "whisper_device":         "auto",
  "wake_word":              "jarvis",
  "plugin_handler_timeout": 5.0
}
```

### Modely Ollama
| Model | RAM | Typ úkolu |
|---|---|---|
| `qwen2.5:1.5b` | ~1 GB | Rychlé odpovědi (FAST) |
| `qwen2.5:3b` | ~3 GB | Výchozí (STANDARD) |
| `qwen2.5:7b` | ~5 GB | Code, Math, Reasoning |
| `llama3.1:8b` | ~8 GB | Reasoning, Agent |
| `llava:7b` | ~8 GB | Vision |
| `deepseek-coder:latest` | ~4 GB | Code |

---

## Vývoj a testy

```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 454 testů, 0 failed
```

### Plugin health check
```python
from plugin_system import create_plugin_manager
pm = create_plugin_manager()
pm.load_all_plugins()
print(pm.health_check())
# 15/15 healthy
```

### Linter
```bash
ruff check . --select F821,F811,E711,E712
# All checks passed!
```

---

## Troubleshooting

### Backend ECONNREFUSED (port 8002)
```bash
# Frontend potřebuje backend!
source ~/Stažené/jarvis-env/bin/activate && python dashboard.py
# Pak v druhém terminálu:
cd web && npm run dev
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

### STT offline
```bash
pip install vosk           # ~50 MB model
# nebo
pip install faster-whisper # přesnější, GPU
```

### Vision
```bash
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

### Plugin selže
```bash
python -c "
from plugin_system import create_plugin_manager
pm = create_plugin_manager(); pm.load_all_plugins()
for h in pm.health_check():
    print(h['name'], h['status'], h.get('error',''))
"
```

---

## Požadavky

- **Python** 3.11+
- **Node.js** 18+ (web frontend, MCP servery)
- **[Ollama](https://ollama.com)** — `ollama pull qwen2.5:3b`
- **ffmpeg** — `sudo apt install ffmpeg`

```bash
pip install -r requirements.txt
```

---

## Plánované featury

- [ ] Electron wrapper (lepší desktop integrace)
- [ ] FAISS / Chroma vektorový store (lepší paměť)
- [ ] Agent Graph v2 — realtime animace kroků
- [ ] Vision GPU akcelerace (CUDA)
- [ ] Docker image (headless server mód)

---

## Licence

MIT — volně šiřitelný a upravitelný.
