# JARVIS v4.5 — Lokální AI asistent

> Ovládej celý počítač hlasem nebo textem. Běží **100 % lokálně** — žádný cloud, žádný API klíč (kromě volitelného Brave Search).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-4.5.0-orange)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Co je nového v v4.5

| Změna | Detail |
|---|---|
| **Web-first launcher** | `python jarvis.py` → backend + prohlížeč na `/app`. Tkinter přes `--gui` |
| **desktop/ + scripts/** | Izolovaný shell wrapper, `scripts/start.sh`, `dev.sh`, `build.sh` |
| **Open-Meteo počasí** | Přepsáno z wttr.in na Open-Meteo (free, bez API klíče, WMO emoji) |
| **Hardware info** | `cmd_hardware_info()` — CPU, RAM, disk, GPU ze systémových příkazů |
| **CriticAgent plausibility** | Heuristická detekce halucinovaných čísel před LLM voláním |
| **Silero VAD** | Opt-in voice activity detection (torch) — přesné zachycení řeči v hluku |
| **Memory conflict resolution** | Detekce protichůdných vzpomínek, automatická degradace starých |
| **Undo stack** | `CommandExecutor` pamatuje 20 posledních souborových akcí |
| **OllamaClient.call_json()** | Strukturované výstupy přes Ollama `format:"json"` |
| **System tray** | `python jarvis.py --tray` nebo `desktop/tray.py` |
| **Vite base=/app/ fix** | React build správně servírovaný přes FastAPI na `/app` |
| **WS proxy fix** | Dev mode WebSocket přes Vite proxy (`:3000`) místo přímého `:8002` |
| **Offline KB live sync** | `.offline_kb.json` se obohacuje živými záznamy z SQLite |
| **MCP startup warnings** | Varování pro MCP servery jejichž příkaz (npx/uvx) není na PATH |

---

## Quickstart

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
chmod +x install.sh && ./install.sh
bash start_jarvis.sh          # → http://localhost:8002/app
```

### Způsoby spuštění

```bash
bash start_jarvis.sh           # backend + prohlížeč (doporučeno)
python jarvis.py               # totéž přímé
python jarvis.py --webview     # nativní pywebview okno
python jarvis.py --tray        # minimalizovat do systémového traye
python jarvis.py --gui         # klasické Tkinter okno
python jarvis.py --dashboard   # jen backend bez otevírání UI

# Dev mode s hot-reload
bash scripts/dev.sh            # backend (reload) + Vite HMR → :3000
cd web && npm run dev          # jen frontend (backend musí běžet zvlášť)
bash scripts/build.sh          # sestaví React build do web_dist/
```

### Volitelné závislosti

```bash
pip install vosk                   # Offline STT (~50 MB, stáhne se automaticky)
pip install sentence-transformers  # Lokální embeddingy — lepší paměť (~400 MB)
pip install rapidfuzz              # Fuzzy matching příkazů (překlepy)
pip install torch                  # Silero VAD — přesná detekce řeči v hluku
pip install pystray pillow         # Systémový tray (--tray mód)
ollama pull llava:7b               # Vision — popis obrazovky, webcam
sudo apt install tesseract-ocr tesseract-ocr-ces  # OCR
```

---

## Architektura

```
jarvis.py               — vstupní bod (výchozí: web launcher)
config.py               — konfigurace, __version__ = "4.5.0"

# Shell vrstvy
desktop/
  launcher.py           — pywebview / browser / tray shell
  tray.py               — standalone systémový tray daemon
scripts/
  start.sh              — produkční spuštění
  dev.sh                — backend reload + Vite HMR (:3000)
  build.sh              — npm build → web_dist/

# AI Engine
llm.py                  — LLMEngine + OllamaClient (+ call_json structured outputs)
local_router.py         — LocalRouter (regex + fuzzy + DSL, 95%+ bez LLM)
llm_router.py           — výběr modelu dle typu úkolu (code/math/translate/chat)
router_dsl.py           — mini DSL: "nastav hlasitost {num}" → action + coerce
context_orchestrator.py — aktivní okno, clipboard, systém → system prompt

# Agenti
agent_react.py          — ReAct smyčka (Thought→Action→Observation)
agent_graph.py          — Graf agent (Planner→Router→Executor→Critic)
agent_roles.py          — Multi-agent role + CriticAgent plausibility check
agent_tools.py          — ToolRegistry (12 nástrojů)

# Web
web/                    — React + Vite (base=/app/, proxy na :8002)
  src/store/jarvis.js   — Zustand, WS backoff, dev proxy / prod same-host
dashboard.py            — FastAPI backend port 8002 (/app, /api/*, /ws/*)
app_desktop.py          — shim → desktop/launcher.py

# Commands
commands/
  system.py             — shutdown, hlasitost, jas, hardware_info, disk_space
  apps.py               — open/kill/install aplikace
  media.py              — YouTube, screenshot, klávesnice, vision
  files.py              — soubory, clipboard, web
  utils.py              — kalkulačka, překlad, počasí (Open-Meteo), wiki
  __init__.py           — CommandExecutor + undo stack (20 kroků)

# Infrastructure
tts.py                  — edge-tts streaming + pyttsx3, queue worker
stt.py                  — Google STT + VoskSTT + Silero VAD (opt-in)
memory.py               — SQLite + EmbeddingEngine + TTL/priority + conflict resolution
plugin_system.py        — ManifestValidator + sandbox + health_check
plugin_marketplace.py   — GitHub ZIP + rating + auto-update
mcp_bridge.py           — MCPBridge (9 serverů) + PATH check při startu
security_v2.py          — SAFE/STANDARD/ELEVATED + audit log
agents.py               — CPU/RAM monitor, idle detector, get_instance() singleton
offline_mode.py         — offline fallback + live sync z SQLite KB
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes       (15 skills, sandbox timeout)
  ├─ 2. Lokální router     (regex + fuzzy + DSL)
  ├─ 3. ReAct / Graf       (vícesvůlové úkoly)
  └─ 4. Ollama stream      (AI konverzace)
           │
           ├─ UserProfile kontext
           ├─ Memory kontext (TTL/priority + embeddings + conflict resolution)
           └─ Context Orchestrator (aktivní okno, clipboard, systém)
  │
  ▼
Security check → CommandExecutor (+ undo stack) / MCP / Vision → TTS
```

---

## Co umí

### Ovládání PC
| Příkaz | Akce |
|---|---|
| „Otevři Chrome / Discord / Spotify" | Spustí aplikaci |
| „Zavři Chrome" | Ukončí proces |
| „Nainstaluj vlc" | `apt install` |
| „Smaž / Vytvoř soubor nebo složku" | Souborové operace + undo stack |
| „Vrať poslední akci" | Undo (složka/soubor/schránka, 20 kroků) |
| „Jaké máš komponenty / hardware info" | CPU, RAM, GPU, disk ze systému |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Počasí (Open-Meteo)
| Příkaz | Výstup |
|---|---|
| „počasí Ostrava" nebo „Ostrava počasí" | `🌧️ Ostrava, Česko: Slabý déšť 🌡️ 15°C 💧 80% 💨 6 km/h` |
| „počasí Praha" | aktuální podmínky s WMO emoji |
| „počasí" bez města | automatická geolokace |

### Vision — Multi-modalita
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA |
| „Přečti text / OCR" | pytesseract OCR |
| „Zapni kameru" | cv2 záběr + LLaVA |

### Audio & klávesnice
| Příkaz | Akce |
|---|---|
| „Hlasitost na 60 / Ztlum" | PulseAudio / ALSA |
| „Jas na 70" | brightnessctl / xrandr |
| „Screenshot" | PNG na plochu |
| „Napiš Hello World" | Simulace klávesnice |

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
| „Počasí Praha / Ostrava" | Open-Meteo (bez API klíče) |
| „Co je Python?" | Wikipedia |
| „Přelož hello world do angličtiny" | Ollama překlad |
| „Vypočítej 15% z 200" | AST sandbox kalkulačka |
| „100 USD na CZK" | Měnový konvertor |
| „Zapamatuj si X" | SQLite memory (TTL/priority + conflict check) |
| „Vrať poslední akci" | Undo stack |
| Obecná otázka / kód | Ollama LLM (structured outputs) |
| „PSG vs Arsenal výsledek" | DuckDuckGo → výsledek přímo v chatu |
| „tabulka premier league" | DuckDuckGo → živá tabulka |
| „bitcoin cena" / „kurz eura" | DuckDuckGo → aktuální kurz |

### ReAct + Multi-agent
```
„Najdi cenu RTX 4090 a ulož ji do poznámky"
→ Plan → Search → Note → Done
  CriticAgent: plausibility check čísel + LLM hodnocení

multi_agent.run("Porovnej PostgreSQL vs SQLite")
# PlannerAgent → ResearcherAgent → ExecutorAgent → CriticAgent
```

---

## MCP integrace (9 serverů)

> Požadavky: Node.js 18+ · `pip install mcp`
> JARVIS upozorní při startu pokud příkaz (npx/uvx) není na PATH.

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
| **Brave Search** | „vyhledej X" | ✅ BRAVE_API_KEY |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
```

---

## Plugin systém — 15 skills

```
plugins/custom/
├── calculator/    ├── clipboard/     ├── greeting/
├── marketplace/   ├── timer/
├── mcp_brave/     ├── mcp_computer_control/  ├── mcp_fetch/
├── mcp_filesystem/├── mcp_git/       ├── mcp_memory/
├── mcp_puppeteer/ ├── mcp_sequential_thinking/
├── mcp_time/      └── [system]
```

### Přidání vlastního pluginu

```json
{ "name": "muj_skill", "version": "1.0.0",
  "permissions": ["answer"], "triggers": ["klíčové slovo"] }
```

```python
import re
_RE = re.compile(r"\b(klicove\s+slovo)\b", re.IGNORECASE)
def _handle(text): return "Odpověď!", {"action": "answer", "params": {}}
def get_routes():   return [{"pattern": _RE, "handler": _handle}]
def get_actions():  return {}
```

---

## Smart Memory

```python
mem.store("dočasná info", ttl_seconds=3600)    # expiruje za 1h
mem.store("kritická info", priority=2)          # 0=normal, 1=high, 2=critical
mem.store_with_conflict_check("jmenuji se Petr") # nahradí starý záznam
mem.run_maintenance()  # → {"deleted_expired": 3, "total": 45}
```

**Context Orchestrator** — každý LLM dotaz automaticky obsahuje:
aktivní okno, obsah schránky, aktuální čas, CPU/RAM.

---

## Konfigurace

### config.json
```json
{
  "ollama_url":   "http://localhost:11434/api/chat",
  "ollama_model": "qwen2.5:3b",
  "tts_enabled":  true,
  "tts_voice":    "cs-CZ-AntoninNeural",
  "stt_language": "cs-CZ",
  "wake_word":    "jarvis"
}
```

| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | Výchozí — rychlý |
| `llama3.1:8b` | ~8 GB | Lepší kvalita |
| `llava:7b`    | ~8 GB | Vision |

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ test_jarvis.py -v
ruff check . --select F821,F811,E711,E712
```

### Přidání nové akce
1. Pattern do `local_router.py` nebo `router_dsl.py`
2. Implementace `cmd_nazev()` v `commands/`
3. Export z `commands/__init__.py`
4. Oprávnění do `security_v2.py`
5. Test do `tests/`

---

## Troubleshooting

```bash
# Backend
curl http://localhost:8002/health
python jarvis.py --dashboard

# npm run dev — musí běžet z web/ složky!
cd web && npm run dev

# Ollama
ollama serve && ollama pull qwen2.5:3b

# TTS / STT
sudo apt install ffmpeg mpg123 && pip install edge-tts
pip install vosk   # offline STT

# Vision
ollama pull llava:7b
sudo apt install tesseract-ocr && pip install pytesseract opencv-python

# Silero VAD / Tray
pip install torch
pip install pystray pillow

# Pluginy
python -c "from plugin_system import create_plugin_manager as c; pm=c(); pm.load_all_plugins(); print(pm.health_check())"

# MCP
node --version  # Node.js 18+
pip install mcp
```

---

## Požadavky

- **Python** 3.11+
- **Node.js** 18+ (MCP, web build)
- **[Ollama](https://ollama.com)** — `ollama pull qwen2.5:3b`
- **ffmpeg** — `sudo apt install ffmpeg`

```bash
pip install -r requirements.txt
```

---

## Licence

MIT — volně šiřitelný a upravitelný.
