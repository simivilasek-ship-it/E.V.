# JARVIS v4.2 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, grafový agent (Planner→Router→Executor→Critic), ReAct agent, sémantická paměť s denním shrnutím, plugin marketplace, MCP integrace, security audit, background monitoring a multi-modalita (OCR, kamera, popis obrazovky).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

## Obsah

- [Co je nového](#co-je-nového)
- [Rychlý start](#rychlý-start)
- [Jak JARVIS zpracovává příkazy](#jak-jarvis-zpracovává-příkazy)
- [Co umí](#co-umí)
- [Agenti](#agenti)
- [Paměť a personalizace](#paměť-a-personalizace)
- [Multi-modalita](#multi-modalita)
- [Plugin systém a sandbox](#plugin-systém-a-sandbox)
- [Plugin marketplace](#plugin-marketplace)
- [MCP integrace](#mcp-integrace)
- [Bezpečnost a audit](#bezpečnost-a-audit)
- [Monitoring a health check](#monitoring-a-health-check)
- [Architektura](#architektura)
- [Konfigurace](#konfigurace)
- [GUI a klávesové zkratky](#gui-a-klávesové-zkratky)
- [Troubleshooting](#troubleshooting)
- [Vývoj a testy](#vývoj-a-testy)

---

## Co je nového

### v4.2 — aktuální
| Změna | Detail |
|---|---|
| **TTS streaming** | Hlasová odezva ~1 s místo ~5 s — JARVIS mluví větu po větě z generátoru |
| **Graf timeout** | Circuit breaker 120 s — grafový agent nikdy nezamrzne |
| **Fuzzy matching** | rapidfuzz zachytí překlepy: „otrevi crhome" → otevři chrome |
| **Plugin sandbox** | AST kontrola importů před načtením pluginu, 7 named permissions v manifestu |
| **LLM Router** | Automatický výběr modelu a teploty podle typu úkolu (kód, math, překlad, chat) |
| **STT validace** | `set_language()` validuje oproti seznamu 23 podporovaných jazyků |
| **Bugfixy** | Opraven executor agentů (`self.cmds`), `AgentState.last_args`, health check URL, offline queue cesty |

### v4.1
| Změna | Detail |
|---|---|
| **Grafový agent** | 4 specializované uzly: Planner→Router→Executor→Critic s retry/replan |
| **Lokální embeddingy** | `sentence-transformers` — sémantické vyhledávání v paměti místo keyword overlap |
| **Plugin marketplace** | Stahování pluginů z GitHub jedním příkazem |
| **DailySummarizer** | Automatická denní sumarizace konverzací + extrakce faktů do UserProfile |

### v4.0
| Změna | Detail |
|---|---|
| **ReAct agent** | Vícesvůlové úkoly (Thought→Action→Observation→Answer) |
| **Multi-modalita** | OCR, popis obrazovky přes LLaVA, webcam |
| **Computer Control MCP** | Klikání, psaní, pohyb myší, správa oken |
| **Security 2.0** | Audit log, 5 úrovní oprávnění, confirmation dialogy pro destruktivní akce |
| **Background monitoring** | CPU/RAM/disk agenti, Event Bus, Async engine s prioritní frontou |
| **Health check** | Monitoring dostupnosti Ollama, paměti, disku a CPU |
| **Offline mode** | Fronta příkazů + fallback knowledge base bez internetu |

---

## Rychlý start

### Linux (automaticky)
```bash
chmod +x install.sh && ./install.sh
bash start_jarvis.sh
```

### Manuálně
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
ollama serve &
ollama pull qwen2.5:3b
python jarvis.py
```

### Volitelné rozšíření
```bash
pip install sentence-transformers   # sémantická paměť (doporučeno)
pip install rapidfuzz               # fuzzy matching překlepů (doporučeno)
pip install vosk                    # offline STT bez internetu
ollama pull llava:7b                # popis obrazovky + webcam
ollama pull qwen2.5-coder:1.5b-base # specializovaný model pro kód
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

### Docker
```bash
docker-compose up
```

---

## Jak JARVIS zpracovává příkazy

```
Hlas / Text
    │
    ▼
STT Engine ── Google STT primárně, Vosk offline fallback
    │
    ▼
LocalRouter ── regex + fuzzy matching (95 % příkazů bez LLM, offline, <10 ms)
    │                │
  [match]        [no match]
    │                │
    │       ┌────────▼────────────────┐
    │       │  Plugin routes          │
    │       │  (marketplace skills)   │
    │       └────────┬────────────────┘
    │                │
    │       ┌────────▼────────────────┐
    │       │  Grafový agent          │  ← "sestav report o X"
    │       │  Planner→Router→        │
    │       │  Executor→Critic        │
    │       └────────┬────────────────┘
    │                │
    │       ┌────────▼────────────────┐
    │       │  ReAct agent            │  ← "najdi X a ulož Y"
    │       │  Thought→Action→        │
    │       │  Observation→Answer     │
    │       └────────┬────────────────┘
    │                │
    │       ┌────────▼────────────────┐
    │       │  LLMEngine + LLMRouter  │  ← konverzace, kód, překlad
    │       │  (model dle task type)  │
    │       └────────┬────────────────┘
    │                │
    └────────────────┘
    │
    ▼
Security check ── permission level, audit log, confirmation dialog
    │
    ▼
CommandExecutor ── 40+ akcí (system, apps, files, media, utils)
    │
    ▼
TTS streaming ── edge-tts větu po větě (~1 s první odezva)
```

**LocalRouter** zpracuje 95 % příkazů bez jediného LLM volání — čas, hlasitost, aplikace, soubory, paměť, počasí. Přidá fuzzy matching pro překlepy (rapidfuzz).

**LLMRouter** dynamicky vybere model a teplotu podle detekovaného typu úkolu:
- `CODE` → qwen2.5-coder:1.5b, temp 0.1, max 2000 tokenů
- `MATH` → temp 0.0, max 500 tokenů
- `TRANSLATE` → temp 0.1, max 800 tokenů
- `CHAT` → default model, temp 0.2, max 1000 tokenů

---

## Co umí

### Systém
| Příkaz | Akce |
|---|---|
| „Kolik je hodin / datum" | Přímá odpověď |
| „Počasí Praha" | OpenWeather API |
| „Hlasitost na 60 / ztlum" | Nastaví systémovou hlasitost |
| „Jas na 80" | Nastaví jas obrazovky |
| „Vypni / Restartuj počítač" | Shutdown / Restart |
| „Info o systému" | CPU, RAM, disk |
| „Uspat počítač" | Suspend |

### Aplikace
| Příkaz | Akce |
|---|---|
| „Otevři Chrome / Discord / Spotify" | Spustí aplikaci |
| „Zavři Chrome" | Ukončí proces |
| „Nainstaluj vlc" | `apt install` |
| „Otevři VSCode v /home/…" | Spustí editor v adresáři |
| „Spusť skript X" | Spustí shell skript |

### Soubory a web
| Příkaz | Akce |
|---|---|
| „Smaž / Vytvoř / Najdi soubor X" | Správa souborů |
| „Přesuň X do Y" | Přesun souboru |
| „Hledej na webu X" | Google search |
| „Otevři URL" | Prohlížeč |
| „Zkopíruj do schránky X" | Clipboard |
| „Klikni na 500 300" | Klik na souřadnice (Computer Control MCP) |

### Média a produktivita
| Příkaz | Akce |
|---|---|
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay |
| „Stáhni video / audio X" | yt-dlp |
| „Screenshoot" | Uloží na plochu |
| „Nastav timer na 5 minut" | Hlasové upozornění po vypršení |
| „Play / pauza / další" | Mediální klávesy |

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Co je Python / Wikipedia X" | Wikipedia API |
| „Přelož hello do češtiny" | Ollama překlad |
| „Vypočítej 15 % ze 3 400" | Math sandbox |
| „Převeď 100 USD na CZK" | ExchangeRate API |
| „Zapamatuj si X / Co víš o X?" | Sémantická paměť |
| Kód, esej, analýza, kuchyně… | Ollama LLM |

### Poznámky a připomínky
| Příkaz | Akce |
|---|---|
| „Přidej poznámku X" | Uloží do `~/jarvis_notes.txt` |
| „Ukaž poznámky" | Vypíše všechny |
| „Připomeň mi X v 15:30" | Scheduler |

---

## Agenti

### Grafový agent — složité úkoly

Použije se automaticky pro analýzy, porovnání, reporty a vícesvůlové plánování.

```
START
  │
  ▼
Planner ── LLM rozdělí úkol na 2–5 pojmenovaných kroků (JSON)
  │
  ▼
Router ─── LLM vybere nástroj pro aktuální krok
  │                │
  ▼                ▼
Executor        DONE ── LLM shrne výsledky
  │
  ▼
Critic ── OK → Router (další krok)
          RETRY → Executor (max 2×)
          REPLAN → Planner (max 1×)
```

**Limity:** timeout 120 s, max 8 kroků, max 2 retry, max 1 replan.

**Příklad:**
```
„Sestav report o cenách GPU a ulož ho"

Planner:  ["vyhledej ceny GPU", "porovnej modely", "ulož report"]
Router:   web_search("GPU ceny 2025")
Executor: "RTX 4090: 35k, RTX 4080: 25k..."
Critic:   OK
Router:   note_add("GPU report: RTX 4090 35k...")
Critic:   OK
Answer:   "Report o cenách GPU uložen do poznámek."
```

### ReAct agent — vícesvůlové úkoly

Použije se pro příkazy jako „najdi X a ulož Y", „zkontroluj ceny a pak mi pošli souhrn".

```
Thought: Co musím udělat?
Action:  tool_name(param="value")
Observation: [výsledek nástroje]
... max 6 kroků ...
Answer:  Finální odpověď
```

### Výběr agenta

| Typ příkazu | Agent |
|---|---|
| Jednoduchý příkaz („otevři chrome") | LocalRouter — okamžitě, bez LLM |
| Vícesvůlový úkol („najdi X a ulož Y") | ReAct agent |
| Složitý úkol („sestav / porovnej / analyzuj") | Grafový agent |
| Obecná otázka / konverzace | LLMEngine + LLMRouter |

### Dostupné nástroje agentů (16+)

`web_search`, `fetch_url`, `note_add`, `note_list`, `memory_store`, `memory_recall`, `get_time`, `get_weather`, `calculate`, `open_url`, `open_app`, `screenshot`, `wiki_search`, `read_file`, `list_files`, `screen_describe`

---

## Paměť a personalizace

### Sémantická paměť (`memory_data/memories.db`)

```bash
pip install sentence-transformers   # aktivuje sémantické vyhledávání
```

- **S `sentence-transformers`:** cosine similarity přes `paraphrase-multilingual-MiniLM-L12-v2` — najde synonyma a parafráze
- **Bez balíčku:** keyword overlap fallback
- Exponenciální decay pro starší záznamy (nikdy zcela nevymizí)
- Recall context se automaticky injektuje do každého LLM dotazu

### DailySummarizer

Každou noc shrne dnešní konverzace, extrahuje klíčová fakta a přidá je do UserProfile.

### UserProfile (`~/.jarvis_user_profile.json`)

Permanentní fakta o uživateli — **nikdy nedecay**.

JARVIS automaticky extrahuje z textu:
- „Jmenuju se Petr" → jméno = Petr
- „Bydlím v Brně" → město = Brno
- „Mám rád Python" → zájmy = Python

Summary se injektuje do systémového promptu každého LLM dotazu.

### MCP Knowledge Graph (`~/.jarvis_mcp_memory/`)

Persistentní knowledge graph přes `@modelcontextprotocol/server-memory`.

---

## Multi-modalita

### Popis obrazovky
```
„Co vidíš na obrazovce?" / „Popiš co je otevřené"
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

## Plugin systém a sandbox

### Formáty pluginů

**1. Složka s manifestem (doporučeno):**
```
plugins/custom/muj_skill/
  manifest.json
  skill.py
```

**2. Standalone soubor:**
```
plugins/custom/muj_skill.py
```

### Sandbox — kontrola importů

Každý plugin je před načtením **staticky analyzován (AST)** — kód se nikdy nespustí dřív, než projde kontrolou importů. Zakázané moduly (`subprocess`, `socket`, `os`…) způsobí odmítnutí pluginu s chybou v logu.

Manifest rozšiřuje povolené moduly přes pole `permissions`:

| Permission | Odemkne moduly |
|---|---|
| `os` | `os`, `os.path` |
| `subprocess` | `subprocess` |
| `socket` | `socket`, `ssl`, `asyncio` |
| `filesystem` | `shutil`, `glob`, `tempfile`, `fnmatch` |
| `system` | `psutil`, `platform`, `resource` |
| `database` | `sqlite3`, `sqlalchemy` |
| `crypto` | `cryptography`, `hmac`, `secrets` |

### Příklad pluginu

**`manifest.json`**
```json
{
  "name": "muj_skill",
  "version": "1.0.0",
  "description": "Příklad skill pluginu",
  "author": "ja",
  "permissions": ["filesystem"],
  "triggers": ["muj příkaz"]
}
```

**`skill.py`**
```python
import re
_PATTERN = re.compile(r"\b(muj\s+prikaz)\b", re.IGNORECASE)

def _handle(text):
    return "Hotovo!", {"action": "answer", "params": {}}

def get_routes():
    return [{"pattern": _PATTERN, "handler": _handle}]

def get_actions():
    return {}
```

### Timeout

- Route handler: max **3 s**
- Action handler: max **10 s**

---

## Plugin marketplace

```
„Marketplace seznam"                  → dostupné pluginy
„Nainstaluj plugin calculator"        → stáhne a nainstaluje
„Nainstaluj z github user/muj-plugin" → přímá instalace z GitHub
„Aktualizuj plugin X"                 → aktualizuje na nejnovější
„Odinstaluj plugin X"                 → odebere plugin
```

Marketplace stáhne ZIP z GitHub release nebo `main` větve, rozbalí do `plugins/custom/<nazev>/` a JARVIS načte plugin při příštím příkazu.

---

## MCP integrace

> **Požadavky:** Node.js 18+ a `pip install mcp`

### Dostupné servery

| Server | Co umí | API klíč |
|---|---|---|
| **Filesystem** | Čtení souborů, strom adresářů, full-text | ❌ |
| **Web Fetch** | Načtení obsahu stránek | ❌ |
| **Git** | git log / status / diff | ❌ |
| **Memory Graph** | Persistentní knowledge graph | ❌ |
| **Brave Search** | Vyhledávání | ✅ `BRAVE_API_KEY` |
| **Computer Control** | Klikání, psaní, okna, OCR | ❌ |
| **Sequential Thinking** | Vícesvůlové plánování | ❌ |
| **Time** | Čas + časová pásma | ❌ |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
# Klíč zdarma: https://api.search.brave.com/
```

---

## Bezpečnost a audit

### 5 úrovní oprávnění

| Úroveň | Akce | Výchozí |
|---|---|---|
| `SAFE` | answer, search, screenshot | vždy povoleno |
| `STANDARD` | create_folder, memory_store | povoleno |
| `ELEVATED` | delete_file, kill_process, shutdown | **vyžaduje potvrzení** |
| `RESTRICTED` | update_system | blokováno výchozím |
| `FORBIDDEN` | nebezpečné patterny (`rm -rf /`, fork bomb) | vždy zakázáno |

### Audit log (`~/.jarvis_audit.jsonl`)

Každá akce se zaznamenává: `timestamp`, `action`, `params`, `allowed`, `reason`, `user_text`, `result`.

---

## Monitoring a health check

### Background agenti (vždy běží)

| Agent | Spustí se při |
|---|---|
| CPU agent | CPU > 80 % |
| RAM agent | RAM > 85 % |
| Disk agent | Disk < 10 % volného místa |

Agenti publikují eventy přes Event Bus — JARVIS tě upozorní hlasem nebo v chatu.

### Health check

Kontroluje: Ollama dostupnost, využití paměti, místo na disku, zatížení CPU, síťové připojení.

### Web dashboard (`localhost:8002`)

```bash
python dashboard.py
```

Zobrazí přehled systému, logy, audit trail, scheduler a stav agentů.

---

## Architektura

```
jarvis.py               — bootstrap
app_core.py             — orchestrátor, lazy init, routing pipeline
│
├── gui/                — GUI package (Tkinter)
│   ├── app_window.py   — hlavní okno, chat, history šipky
│   ├── settings.py     — SettingsDialog (STT, TTS, MCP, logy)
│   └── orb.py / chat.py / constants.py
│
├── llm.py              — LLMEngine + LocalRouter (regex + fuzzy)
├── llm_router.py       — LLMRouter — výběr modelu dle TaskType
│
├── agent_graph.py      — Grafový agent (Planner→Router→Executor→Critic)
├── agent_react.py      — ReAct agent (Thought→Action→Observation)
├── agent_tools.py      — ToolRegistry (16+ nástrojů)
│
├── memory.py           — SQLite + embedding recall + DailySummarizer
├── user_profile.py     — permanentní fakta o uživateli
│
├── plugin_system.py    — SkillLoader + sandbox (AST kontrola importů)
├── plugin_marketplace.py — stahování pluginů z GitHub
│
├── tts.py              — edge-tts / pyttsx3, streaming worker
├── stt.py              — Google STT + Vosk offline fallback
├── vision.py           — VisionEngine (OCR, screen, webcam + LLaVA)
├── wake_word_detector.py — detekce „JARVISe", pause/resume s STT
│
├── security_v2.py      — AuditLog, 5 úrovní oprávnění, confirmation
├── mcp_bridge.py       — MCP klient (8 serverů)
│
├── health_check.py     — monitoring komponent (Ollama, RAM, disk, CPU)
├── cache_manager.py    — LRU + disk cache pro LLM a API odpovědi
├── offline_mode.py     — offline fronta příkazů + fallback knowledge base
├── async_utils.py      — AsyncEngine s prioritní frontou (4 workers)
│
├── event_bus.py        — PUB/SUB (GUI, LLM, CMD, Agent, Memory eventy)
├── agents.py           — background monitoring agenti (CPU/RAM/disk)
├── scheduler.py        — plánování úloh (at/after/every/every_day_at)
├── error_handling.py   — centrální error handler + recovery
│
├── commands/           — CommandExecutor — 40+ akcí
│   ├── system.py       — čas, datum, hlasitost, jas, shutdown
│   ├── apps.py         — open/kill/install aplikace
│   ├── files.py        — soubory, web, clipboard
│   ├── media.py        — screenshot, youtube, timer, klávesnice
│   └── utils.py        — kalkulačka, překlad, poznámky, wiki, počasí
│
├── dashboard.py        — web UI FastAPI (port 8002)
├── config.py           — centrální konfigurace (.env → config.json → defaults)
│
└── plugins/custom/     — sandbox chráněné pluginy
    ├── greeting / calculator / timer / clipboard
    ├── mcp_filesystem / mcp_fetch / mcp_git / mcp_brave / mcp_memory
    └── mcp_computer_control / marketplace
```

### Event Bus typy

```
GUI:    GUI_COMMAND, GUI_STATE_CHANGE, GUI_MESSAGE
LLM:    LLM_START, LLM_CHUNK, LLM_DONE, LLM_ERROR
CMD:    CMD_EXECUTE, CMD_DONE, CMD_ERROR
Agent:  AGENT_ALERT, CPU_HIGH, RAM_HIGH, DISK_LOW
Memory: MEMORY_STORED, MEMORY_RECALLED
Sched:  TASK_SCHEDULED, TASK_FIRED
```

---

## Konfigurace

### `config.json`
```json
{
  "ollama_url":              "http://localhost:11434/api/chat",
  "ollama_model":            "qwen2.5:3b",
  "tts_enabled":             true,
  "tts_voice":               "cs-CZ-AntoninNeural",
  "tts_rate":                170,
  "stt_language":            "cs-CZ",
  "stt_energy_threshold":    300,
  "history_size":            20,
  "plugins_enabled":         true,
  "wake_word_enabled":       true,
  "wake_word":               "jarvis",
  "audit_enabled":           true,
  "async_max_workers":       4,
  "mcp_filesystem_enabled":  true,
  "mcp_brave_enabled":       false
}
```

### `.env`
```bash
BRAVE_API_KEY=tvůj_klíč
MCP_BRAVE_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
```

### Ollama modely

| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | výchozí — chat, překlad |
| `qwen2.5-coder:1.5b-base` | ~2 GB | kód (LLMRouter auto-vybere) |
| `llama3.1:8b` | ~8 GB | komplexní analýzy |
| `llava:7b` | ~8 GB | vision (OCR, screen, webcam) |
| `deepseek-coder:latest` | ~4 GB | kód fallback |

### Podporované jazyky STT

`cs-CZ`, `en-US`, `en-GB`, `de-DE`, `fr-FR`, `es-ES`, `it-IT`, `pl-PL`, `sk-SK`, `ru-RU`, `zh-CN`, `ja-JP`, `ko-KR`, `pt-BR`, `nl-NL`, `sv-SE`, `da-DK`, `fi-FI`, `nb-NO`, `hu-HU`, `ro-RO`, `tr-TR`, `uk-UA`

---

## GUI a klávesové zkratky

| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat příkaz |
| `↑ / ↓` | Procházet historii zpráv |
| `Mezerník` | Zapnout / vypnout mikrofon |
| `Ctrl+L` | Vymazat chat |
| `Ctrl+E` | Exportovat konverzaci do `.md` |
| `Esc` | Focus do vstupního pole |

GUI nabídne dropdown pro výběr Ollama modelu a jazyka STT přímo za běhu — změna se projeví okamžitě.

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
| Fuzzy matching | `pip install rapidfuzz` |
| Vosk offline STT | `pip install vosk` + stáhnout model z [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) do `~/.vosk/` |
| Plugin odmítnut sandboxem | Přidej potřebnou permission do `manifest.json` |
| Health check hlásí Ollama offline | Ověř že Ollama běží: `curl http://localhost:11434/api/tags` |
| Agenti nefungují (ReAct / Graf) | Zkontroluj log — může selhat `ollama pull` nebo chybět model |

---

## Vývoj a testy

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

**330+ testů:** STT + Vosk (10), TTS + streaming (6), LocalRouter + fuzzy, CommandExecutor (24), Security (22), safe_run (13), MCP bridge (11), ReAct (17), Grafový agent (27), Vision (15), Embeddingy (8), Marketplace (8), nové moduly (23), vylepšení (16), integrace (108).

### Přidání nové akce

1. Pattern → `LocalRouter.route()` v `llm.py`
2. `cmd_nazev()` v příslušném `commands/` modulu
3. Export z `commands/__init__.py`
4. Oprávnění do `security_v2.py`
5. Test do `tests/`

### Přidání nového agentního nástroje

1. Funkce do `agent_tools.py` → `build_registry()`
2. `Tool(name, description, params, fn, examples)` — description musí být popisná, Router ji čte jako instrukci

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Licence

MIT — volně šiřitelný a upravitelný.
