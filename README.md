<div align="center">

# JARVIS

**Lokální AI asistent — 100% offline, žádný cloud**

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/tests-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Version](https://img.shields.io/badge/version-4.6.0-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![License](https://img.shields.io/badge/license-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)

*Ovládej celý počítač hlasem nebo textem. Plánování, vize, paměť, workflow — vše lokálně.*

</div>

---

## Rychlý start

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
./install.sh
bash start_desktop.sh     # React HUD v nativním okně
```

**Web UI:**
```bash
python dashboard.py       # backend → :8002
cd web && npm run dev     # frontend → :3000
```

**Produkční build webu (servírováno FastAPI na `/app`):**
```bash
bash scripts/build.sh     # vytvoří ./web_dist (statický export)
python dashboard.py       # UI pak běží na http://localhost:8002/app
```

---

## Co umí

| Oblast | Příkazy |
|--------|---------|
| **PC** | Otevři Chrome · Zavři · Nainstaluj · Vypni · Restartuj |
| **Soubory** | Smaž · Vytvoř · Přesuň · Přejmenuj · Obsah složky |
| **Systém** | Jaký mám hardware · Místo na disku · GPU teplota |
| **Vision** | Popiš obrazovku · OCR · Webcam → LLaVA |
| **Média** | Zahraj X · Stáhni video · YouTube search |
| **AI** | Počasí · Překlad · Kalkulačka · Wikipedia · Kód |
| **Sport/Novinky** | PSG vs Arsenal · Tabulka ligy · Bitcoin → DuckDuckGo |
| **Paměť** | Zapamatuj si X · Co víš o X · SQLite + embeddingy |
| **Workflow** | Když CPU > 90% → screenshot · Každý den v 9:00 → ... |

---

## Architektura

```
JARVIS
├── Python backend          FastAPI :8002 · WebSocket streaming
│   ├── LLM Router v2       7 typů úkolů → správný model automaticky
│   ├── 15 Skills           Plugin sandbox · Health check · Marketplace
│   ├── 10 MCP serverů      Filesystem · Git · Puppeteer · Computer Control · ...
│   ├── Memory              SQLite + embeddingy · TTL/priority · auto-pruning
│   ├── Agents              ReAct 2.0 (Rollback, Introspection) · Hierarchical (Supervisor) · Graph · Multi-role
│   ├── Workflow Engine     Trigger-based automation (CPU · time · app)
│   └── Notifications       Desktop alerts · CPU/RAM monitoring
│
├── Next.js frontend        TypeScript · Tailwind · React
│   ├── Chat                Streaming · markdown · copy button · history
│   ├── SystemPanel         Circular gauges · 60s sparklines · live metrics
│   ├── Agent Graph         SVG pipeline visualization
│   ├── Spotlight           Alt+Space global hotkey · widgets
│   └── Sidebar             Brand · status · nav groups
│
└── Desktop wrapper         pywebview nativní okno
```

### LLM Router — automatický výběr modelu

| Úkol | Model |
|------|-------|
| Překlad, datum | qwen2.5:1.5b |
| Obecné dotazy | qwen2.5:3b *(výchozí)* |
| Kód, matematika | deepseek-coder · qwen2.5:7b |
| Reasoning, Agent | llama3.1:8b |
| Vision | llava:7b *(VRAM auto-uvolnění)* |

---

## Instalace

**Požadavky:** Python 3.11+ · Node.js 18+ · [Ollama](https://ollama.com) · ffmpeg

```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
```

Pozn.: `requirements.txt` je primární seznam runtime+dev závislostí pro lokální instalaci/CI.

**Volitelné:**
```bash
pip install pynput          # Alt+Space global hotkey
pip install faster-whisper  # Offline STT (GPU)
pip install vosk            # Offline STT (lightweight)
pip install piper-tts       # Lokální TTS bez internetu
pip install sentence-transformers  # Lepší paměť
ollama pull llava:7b        # Vision (popis obrazovky)
```

---

## API

```
GET  /health              → {"status":"healthy","ws":"running","version":"4.6.0"}
GET  /api/system          → CPU · RAM · disk · GPU · temp · network
POST /api/command         → {"command":"..."} → {"response":"..."}
POST /api/config          → {"ollama_model":"..."} → uloží do config.json
GET  /api/plugins         → 15 skills + health status
GET  /api/workflows       → Workflow pravidla
POST /api/notify          → Desktop notifikace
WS   /ws/chat             → Streaming LLM odpovědi
WS   /ws/agents           → CPU/RAM každé 2s
WS   /ws/logs             → Live logy
```

---

## Konfigurace

```json
{
  "ollama_model": "qwen2.5:3b",
  "tts_voice": "cs-CZ-AntoninNeural",
  "stt_language": "cs-CZ",
  "wake_word": "jarvis",
  "plugin_handler_timeout": 5.0,
  "notification_cpu_threshold": 90
}
```

**Secrets** (`.env`, není v gitu):
```bash
BRAVE_API_KEY=...   # Brave Search MCP
```

---

## Vývoj

```bash
python -m pytest tests/ test_jarvis.py -v   # 531 testů
ruff check . --select F,E7                  # linter
```

### Frontend (web/)

```bash
cd web
npm ci
npm run lint
npm run typecheck
npm run dev
```

### Build webu pro produkci (`web_dist/`)

FastAPI pak servíruje build na `http://localhost:8002/app`.

```bash
bash scripts/build.sh
python dashboard.py
```

### Debug bundle (bugreport)

Bezpečný ZIP bez secrets (obsahuje safe config + tail logů):

```bash
curl -L "http://localhost:8002/api/debug/bundle" -o jarvis-debug-bundle.zip
```

### Lokální příkazy (justfile)

Pokud máš nainstalovaný [`just`](https://github.com/casey/just):

```bash
just web-dev
just web-build
just docker-build
```

**Přidání příkazu:** viz [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Agentní inteligence (v4.7+)

Jarvis nyní obsahuje pokročilé agentní architektury pro řešení komplexnějších úkolů:

### 1. ReAct 2.0
Nový a robustnější step-by-step agentní cyklus, který automaticky obsluhuje vícekrokové úkoly.
- **Plánování (Planning)**: Před spuštěním kroků si agent vygeneruje plán a drží se ho.
- **Introspekce (Introspection)**: V každém kroku se agent zamýšlí nad svým postupem a pokrokem.
- **Kontrola kroků & Rollback**: Automaticky detekuje selhání nástrojů nebo podezřelé/halucinované výstupní hodnoty (např. nereálné ceny GPU) a provádí návrat (rollback) k předchozímu funkčnímu checkpointu s instruktáží pro nápravu.

### 2. Hierarchický agent (Supervisor)
Supervisor/koordinátor rozděluje komplexní zadání na pod-úkoly a deleguje je specializovaným sub-agentům s omezeným a bezpečným okruhem nástrojů:
- **Researcher**: Internetové vyhledávání a stahování stránek (`web_search`, `fetch_url`).
- **MemorySpecialist**: Práce s poznámkami a dlouhodobou pamětí (`note_add`, `memory_store`, ...).
- **SystemSpecialist**: Systémový čas, výpočty a počasí (`calculate`, `get_weather`, ...).
- **GenericAgent**: Obecný logický a kódovací asistent bez nástrojů.

*Hierarchický agent se automaticky aktivuje, pokud zadání obsahuje slova jako `deleguj`, `hierarchicky` nebo `rozděl úkoly`.*

---

## Výkon a optimalizace (v4.7+)

### 1. Caching odpovědí (OllamaClient Caching)
- **OllamaClient** nyní automaticky ukládá výsledky dotazů `/api/chat` (textové i strukturované JSON odpovědi) do cache.
- Caching zamezuje opakovaným voláním Ollama pro identické dotazy (např. při opakovaném spouštění Planneru, Criticu nebo stejných ReAct kroků).
- Výrazně (2–4×) zrychluje reakce agentů a šetří hardware při opakovaných dotazech a ladění úloh.

---

## Licence

MIT © 2026 — [simivilasek-ship-it](https://github.com/simivilasek-ship-it)
