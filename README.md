# JARVIS v4.2 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, dlouhodobá paměť, grafový agent (Planner→Router→Executor→Critic), lokální embeddingy, plugin marketplace, MCP integrace a multi-modalita (OCR, kamera, popis obrazovky).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

## Obsah
- [Rychlý start](#rychlý-start)
- [Co je nového](#co-je-nového)
- [Co umí](#co-umí)
- [Grafový agent](#grafový-agent)
- [Multi-modalita](#multi-modalita)
- [Smart Memory & Embeddingy](#smart-memory--embeddingy)
- [Plugin Marketplace](#plugin-marketplace)
- [MCP integrace](#mcp-integrace)
- [Skills — přidání vlastního](#skills--přidání-vlastního)
- [Architektura](#architektura)
- [Konfigurace](#konfigurace)
- [Troubleshooting](#troubleshooting)
- [Vývoj a testy](#vývoj-a-testy)

---

## Co je nového

### v4.2
| Změna | Detail |
|---|---|
| **TTS streaming** | Hlasová odezva ~1s místo ~5s — JARVIS mluví větu po větě z generátoru |
| **Graf timeout** | Circuit breaker 120s — grafový agent nikdy nezamrzne |
| **Fuzzy matching** | rapidfuzz zachytí překlepy: „otrevi crhome" → otevři chrome |

### v4.1
| Změna | Detail |
|---|---|
| **Grafový agent** | 4 specializované uzly: Planner→Router→Executor→Critic s retry/replan |
| **Lokální embeddingy** | `sentence-transformers` — sémantické vyhledávání v paměti místo keyword overlap |
| **Plugin marketplace** | Stahování pluginů z GitHub jedním příkazem |

### v4.0
| Změna | Detail |
|---|---|
| **ReAct agent** | Vícesvůlové úkoly (Thought→Action→Observation→Answer) |
| **Multi-modalita** | OCR, popis obrazovky přes LLaVA, webcam |
| **Computer Control MCP** | Klikání, psaní, pohyb myší, správa oken |
| **Brave Search MCP** | Opravena inicializace — `python-dotenv` |
| **Nastavení GUI** | STT, TTS, MCP přepínače, logy přes ⚙ |
| **Šipky v chatu** | ↑/↓ procházení historie jako v terminálu |
| **URL router fix** | „spust web + URL" vždy otevře prohlížeč |
| **+50 unit testů** | MCP bridge (mock), ReAct, Vision, safe_run |

---

## Rychlý start

### Linux
```bash
chmod +x install.sh && ./install.sh
bash start_jarvis.sh
```

### Manuálně
```bash
source venv/bin/activate
ollama serve &
python jarvis.py
```

### Pro embeddingy a vision (nepovinné)
```bash
pip install sentence-transformers          # sémantická paměť
ollama pull llava:7b                       # popis obrazovky + webcam
sudo apt install tesseract-ocr tesseract-ocr-ces && pip install pytesseract opencv-python
```

---

## Co umí

### Ovládání PC
| Příkaz | Akce |
|---|---|
| „Otevři Chrome / Discord / Spotify" | Spustí aplikaci |
| „Zavři Chrome" | Ukončí proces |
| „Nainstaluj vlc" | `apt install` |
| „Smaž / Vytvoř / Najdi soubor X" | Správa souborů |
| „Vypni / Restartuj počítač" | Shutdown / Restart |
| „Klikni na 500 300" | Klik na souřadnice (Computer Control MCP) |
| „Seznam oken / Přepni na okno Chrome" | Správa oken |

### Vision & obraz
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA |
| „Přečti text z obrazovky / OCR" | pytesseract |
| „Zapni kameru / Webcam" | cv2 + LLaVA |
| „Screenshot" | Uloží na plochu |

### YouTube & média
| Příkaz | Akce |
|---|---|
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay |
| „Stáhni / Info o videu X" | yt-dlp |

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Kolik je hodin / datum / počasí Praha" | Přímá odpověď |
| „Co je Python? / Přelož / Vypočítej" | Wikipedia / Ollama / sandbox |
| „Zapamatuj si X / Co si pamatuješ o X?" | Sémantická paměť |
| Obecná otázka / kód / matematika | Ollama LLM |

### Plugin marketplace
| Příkaz | Akce |
|---|---|
| „Marketplace seznam" | Dostupné pluginy |
| „Nainstaluj plugin X" | Stáhne a nainstaluje |
| „Nainstaluj z github user/repo" | Přímá instalace z GitHub |
| „Odinstaluj / Aktualizuj plugin X" | Správa pluginů |

### GUI klávesové zkratky
| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat příkaz |
| `↑ / ↓` | Procházet historii zpráv |
| `Mezerník` | Mikrofon |
| `Ctrl+L` | Vymazat chat |
| `Ctrl+E` | Exportovat konverzaci do `.md` |
| `Esc` | Focus do input pole |

---

## Grafový agent

JARVIS v4.1 používá **stavový graf** pro složité vícesvůlové úkoly. Oproti lineárnímu ReAct má každý uzel vlastní specializovaný LLM prompt a Critic aktivně kontroluje výsledky.

### Tok grafu

```
START
  │
  ▼
Planner ──── LLM rozdělí úkol na 2–5 konkrétních kroků
  │
  ▼
Router ───── LLM vybere nástroj pro aktuální krok
  │                    │
  ▼                    ▼
Executor            DONE ──── LLM shrne výsledky
  │
  ▼
Critic ──── OK → Router (další krok)
            RETRY → Executor (max 2×)
            REPLAN → Planner (max 1×)
```

### Příklad

```
Uživatel: "Sestav report o cenách GPU a ulož ho"

Planner:  ["vyhledej ceny GPU", "porovnej modely", "ulož report do poznámky"]
Router:   → web_search(query="GPU ceny 2025")
Executor: → "RTX 4090: 35k, RTX 4080: 25k..."
Critic:   → OK
Router:   → web_search(query="porovnání GPU modely")
Executor: → "RTX 4090 nejrychlejší, 4080 nejlepší poměr cena/výkon"
Critic:   → OK
Router:   → note_add(note="GPU report: RTX 4090 35k...")
Executor: → "Poznámka uložena."
Critic:   → OK
Answer:   "Report o cenách GPU uložen do poznámek."
```

### Kdy se který agent použije

| Typ úkolu | Agent |
|---|---|
| Jednoduchý příkaz („otevři chrome") | Lokální router — okamžitě |
| Vícesvůlový úkol („najdi X a ulož Y") | ReAct agent |
| Složitý úkol („sestav / porovnej / analyzuj") | Grafový agent |
| Obecná otázka | Ollama LLM |

---

## Multi-modalita

### Popis obrazovky
```
„Co vidíš na obrazovce?" / „Popiš mi co je otevřené"
```
Screenshot → LLaVA (`ollama pull llava:7b`).

### OCR textu
```
„Přečti text z obrazovky" / „OCR"
```
Screenshot → pytesseract. Funguje bez Ollamy.

### Webcam
```
„Zapni kameru" / „Webcam — co vidíš?"
```
cv2 záběr → LLaVA.

```bash
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

---

## Smart Memory & Embeddingy

### Sémantická paměť (v4.1)
```bash
pip install sentence-transformers
```
Po instalaci JARVIS automaticky přepne recall na **kosinovou podobnost** přes model `paraphrase-multilingual-MiniLM-L12-v2` — lokálně, bez API.

- Bez `sentence-transformers` → keyword overlap (stávající chování)
- S `sentence-transformers` → sémantické hledání (najde i synonyma a parafráze)

### User Profile (`~/.jarvis_user_profile.json`)
Fakta z konverzací: jméno, město, zájmy — vkládají se do každého LLM dotazu.

### SQLite Memory (`memory_data/memories.db`)
- Keyword + embedding recall s recency scoring
- Automatický decay + maintenance každých 6 hodin

### MCP Knowledge Graph (`~/.jarvis_mcp_memory/`)
Persistentní knowledge graph přes `@modelcontextprotocol/server-memory`.

---

## Plugin Marketplace

Stahování pluginů jedním příkazem — žádná ruční instalace.

### Použití
```
„Marketplace seznam"          → zobrazí dostupné pluginy
„Nainstaluj plugin calculator" → stáhne a nainstaluje
„Nainstaluj z github user/muj-jarvis-plugin" → přímá instalace z GitHub
„Aktualizuj plugin X"         → aktualizuje na nejnovější verzi
„Odinstaluj plugin X"         → odebere plugin
```

### Jak funguje
1. Stáhne ZIP z GitHub release nebo main větve
2. Rozbalí do `plugins/custom/<nazev>/`
3. JARVIS načte plugin při příštím příkazu (hot reload)

---

## MCP integrace

> **Požadavky:** Node.js 18+ a `pip install mcp`

### Dostupné MCP servery

| Server | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | čtení souborů, strom, full-text | ❌ |
| **Web Fetch** | načtení obsahu stránek | ❌ |
| **Git** | git log/status/diff | ❌ |
| **Memory Graph** | knowledge graph | ❌ |
| **Brave Search** | vyhledávání | ✅ BRAVE_API_KEY |
| **Computer Control** | klikání, psaní, okna, OCR | ❌ |
| **Sequential Thinking** | vícesvůlové plánování | ❌ |
| **Time** | čas + časová pásma | ❌ |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
# Klíč zdarma: https://api.search.brave.com/
```

---

## Skills — přidání vlastního

```
plugins/custom/muj_skill/
  manifest.json
  skill.py
```

**`manifest.json`**
```json
{
  "name": "muj_skill", "version": "1.0.0",
  "permissions": ["answer"], "triggers": ["klíčové slovo"]
}
```

**`skill.py`**
```python
import re
_PATTERN = re.compile(r"\b(klicove\s+slovo)\b", re.IGNORECASE)

def _handle(text):
    return "Odpověď!", {"action": "answer", "params": {}}

def get_routes():
    return [{"pattern": _PATTERN, "handler": _handle}]

def get_actions():
    return {}
```

---

## Architektura

```
jarvis.py               — bootstrap
app_core.py             — orchestrátor, lazy init
gui/                    — GUI package (OpenCode styl)
  ├── app_window.py     — hlavní okno + šipky v historii
  ├── settings.py       — SettingsDialog (STT, TTS, MCP, logy)
  ├── chat.py / orb.py / constants.py
llm.py                  — lokální router + Ollama streaming
agent_graph.py          — Grafový agent (Planner→Router→Executor→Critic)
agent_react.py          — ReAct agent (fallback pro vícesvůlové)
agent_tools.py          — ToolRegistry (12 nástrojů)
vision.py               — VisionEngine (OCR, screen, webcam)
memory.py               — SQLite + embedding recall + DailySummarizer
plugin_marketplace.py   — stahování pluginů z GitHub
commands/               — system / apps / media / files / utils + safe_run
tts.py / stt.py         — edge-tts / Google STT
user_profile.py         — permanentní fakta o uživateli
security_v2.py          — audit log, 3 úrovně oprávnění
mcp_bridge.py           — MCP klient (8 serverů)
plugin_system.py        — skill loader (lazy loading)
dashboard.py            — web dashboard FastAPI (port 8002)
agents.py / scheduler.py / event_bus.py

plugins/custom/
├── greeting / calculator / timer / clipboard
├── mcp_filesystem / mcp_fetch / mcp_git / mcp_brave / mcp_memory
└── mcp_computer_control / marketplace
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes     (greeting, calculator, MCP skills, marketplace…)
  ├─ 2. Lokální router   (otevři, hlasitost, čas… — bez LLM)
  ├─ 3. Grafový agent    (sestav / porovnej / analyzuj)
  ├─ 4. ReAct agent      (najdi X a ulož Y)
  └─ 5. Ollama stream    (konverzace, kód, překlad)
           ├─ UserProfile kontext
           └─ Memory kontext (embedding recall)
  │
  ▼
Security → CommandExecutor / MCP / VisionEngine → TTS
```

---

## Konfigurace

### config.json
```json
{
  "ollama_url":    "http://localhost:11434/api/chat",
  "ollama_model":  "qwen2.5:3b",
  "tts_voice":     "cs-CZ-AntoninNeural",
  "tts_rate":      170,
  "stt_language":  "cs-CZ"
}
```

### .env
```bash
BRAVE_API_KEY=tvůj_klíč
MCP_BRAVE_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
```

### Modely Ollama
| Model | RAM | Kvalita |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | ★★★ (výchozí) |
| `llama3.1:8b` | ~8 GB | ★★★★★ |
| `llava:7b` | ~8 GB | ★★★★ (vision) |

---

## Troubleshooting

| Problém | Řešení |
|---|---|
| Ollama nespustí | `ollama serve && ollama pull qwen2.5:3b` |
| TTS nefunguje | `sudo apt install ffmpeg && pip install edge-tts` |
| Mikrofon nefunguje | `sudo usermod -a -G audio $USER` |
| MCP nefunguje | `node --version` (18+), `pip install mcp` |
| Brave Search | `cat .env \| grep BRAVE`, `pip install python-dotenv` |
| OCR nefunguje | `sudo apt install tesseract-ocr tesseract-ocr-ces && pip install pytesseract` |
| Vision / LLaVA | `ollama pull llava:7b && pip install opencv-python` |
| Embeddingy | `pip install sentence-transformers` |
| Fuzzy matching nefunguje | `pip install rapidfuzz` |

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

**250+ testů:** config, STT, TTS + streaming (16), LocalRouter + fuzzy, CommandExecutor, AsyncEngine, PluginManager, Security, WakeWord, UserProfile, GUI (headless), safe_run, MCP bridge (mock), ReAct (mock LLM), Grafový agent (27), Vision (mock), Embeddingy (8), Marketplace (8).

### Přidání nové akce
1. Pattern → `LocalRouter.route()` v `llm.py`
2. `cmd_nazev()` v `commands/`
3. Export z `commands/__init__.py`
4. Oprávnění do `security_v2.py`
5. Test do `tests/`

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Licence

MIT — volně šiřitelný a upravitelný.
