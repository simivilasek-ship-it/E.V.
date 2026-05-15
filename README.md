# JARVIS v3.3 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, dlouhodobá paměť, MCP integrace a rozšiřitelný skill systém.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

## Obsah
- [Rychlý start](#rychlý-start)
- [Co umí](#co-umí)
- [MCP integrace](#mcp-integrace)
- [Skills — přidání vlastního](#skills--přidání-vlastního)
- [Smart Memory](#smart-memory)
- [Architektura](#architektura)
- [Konfigurace](#konfigurace)
- [Troubleshooting](#troubleshooting)
- [Vývoj a testy](#vývoj-a-testy)

---

## Co je nového v v3.3

| Změna | Detail |
|---|---|
| **GUI package** | `gui.py` → `gui/` balíček (orb, chat, settings, constants, app_window) |
| **OpenCode styl** | Nový design — top bar, fullwidth chat, bottom input |
| **safe_run helper** | Všechny subprocess volání bez `shell=True` — ochrana před shell injection |
| **Router fix** | „spust/pust chrome" správně otevírá aplikaci místo YouTube |
| **Security cleanup** | `security.py` smazán, vše v `security_v2.py` + zpětně kompatibilní aliasy |
| **commands package** | `commands.py` (1323 ř.) → `commands/` balíček (system, apps, media, files, utils) |
| **SQLite memory** | `memory.py` přešel z JSON na SQLite — rychlejší recall, automatická migrace |
| **Lazy init** | `app_core.py` načítá těžké moduly až na vyžádání → rychlejší start |
| **CI: Xvfb** | GUI testy v CI/CD přes virtual framebuffer, coverage upload |

---

## Rychlý start

### Linux
```bash
chmod +x install.sh && ./install.sh
bash start_jarvis.sh
```

Spouštěč automaticky:
- Spustí Ollama pokud neběží
- Spustí web dashboard na http://localhost:8002
- Aktivuje virtualenv a spustí JARVIS

### Manuálně
```bash
source ~/Stažené/jarvis-env/bin/activate
ollama serve &
python jarvis.py
```

### Jako ikona na ploše (Linux)
```bash
cp start_jarvis.sh ~/.local/bin/start-jarvis.sh
chmod +x ~/.local/bin/start-jarvis.sh
cp jarvis.desktop ~/.local/share/applications/
cp jarvis.desktop ~/Plocha/
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
| „Najdi soubor readme" | `find` |
| „Otevři složku X ve vscode" | VS Code |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Zvuk, obraz, klávesnice
| Příkaz | Akce |
|---|---|
| „Hlasitost na 60 / Ztlum" | PulseAudio / ALSA |
| „Jas na 70" | brightnessctl |
| „Screenshot" | Uloží na plochu |
| „Napíš Hello World" | Simulace klávesnice |
| „Stiskni Ctrl+C" | pyautogui |

### YouTube & média
| Příkaz | Akce |
|---|---|
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay (bez prohlížeče) |
| „Stáhni video X" | yt-dlp download |
| „Info o videu X" | Metadata bez stažení |
| „Titulky k videu X" | yt-dlp subtitles |

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Kolik je hodin / Jaké je datum" | Přímá odpověď |
| „Info o systému" | CPU, RAM, disk |
| „Počasí Praha" | wttr.in |
| „Co je Python?" | Wikipedia |
| „Přelož hello world" | Ollama překlad |
| „Vypočítej 15% z 200" | Sandbox kalkulačka |
| „Zapamatuj si X" | Neural memory |
| „Co si pamatuješ o X?" | Recall z memory |
| Obecná otázka / kód / matematika | Ollama LLM |

### Produktivita
| Příkaz | Akce |
|---|---|
| „Timer 5 minut" | Odpočet + hlasová notifikace |
| „Zkopíruj tento text" | Schránka (xclip/pyperclip) |
| „Přidej poznámku nakoupit chleba" | `~/jarvis_notes.txt` |

### Wake Word
Řekni **„Jarvis"** — asistent se probudí a začne poslouchat bez kliknutí. Mikrofon je uvolněn pro STT (žádná kolize).

### GUI klávesové zkratky
| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat příkaz |
| `Mezerník` | Aktivovat mikrofon (pokud focus není v inputu) |
| `Ctrl+L` | Vymazat chat log |
| `Ctrl+E` | Exportovat konverzaci do `.md` na plochu |
| `Esc` | Přesunout focus do input pole |

---

## MCP integrace

JARVIS integruje [Model Context Protocol](https://modelcontextprotocol.io) pro pokročilé schopnosti. Servery běží přes `npx` jako subprocesy.

### Dostupné MCP skills

| Skill | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | „přečti soubor notes.txt", „strom ~/Projekty", „hledej v souborech TODO" | ❌ není potřeba |
| **Web Fetch** | „hledej online Python asyncio", „načti stránku github.com" | ❌ není potřeba |
| **Git** | „git log", „git status", „git diff", „větve" | ❌ není potřeba |
| **Memory Graph** | „zapamatuj si X", „co víš o X", „zapomeň X" | ❌ není potřeba |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |

### Konfigurace Brave Search
```bash
# Nastav do .env (nikdy do gitu!)
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
# Klíč zdarma: https://api.search.brave.com/
```

### Přidání vlastního MCP serveru
```python
# mcp_bridge.py → create_mcp_bridge()
bridge.register(MCPServerConfig(
    name="muj-server",
    command="npx",
    args=["-y", "@muj/mcp-server"],
))
```

---

## Skills — přidání vlastního

Vytvoř složku v `plugins/custom/muj_skill/`:

**`manifest.json`**
```json
{
  "name": "muj_skill",
  "version": "1.0.0",
  "description": "Co skill dělá",
  "author": "Tvoje jméno",
  "permissions": ["answer"],
  "triggers": ["klíčové slovo"]
}
```

**`skill.py`**
```python
import re

_PATTERN = re.compile(r"\b(moje|klicove\s+slovo)\b", re.IGNORECASE)

def _handle(text: str):
    return "Tady je odpověď!", {"action": "answer", "params": {}}

def get_routes():
    return [{"pattern": _PATTERN, "handler": _handle}]

def get_actions():
    return {}
```

Při příštím startu se načte automaticky. Žádný restart kódu není potřeba.

---

## Smart Memory

JARVIS si pamatuje informace o tobě **permanentně** (přes restarty).

### User Profile (`~/.jarvis_user_profile.json`)
Fakta se extrahují automaticky z každé konverzace:
- „jmenuji se Petr" → `jméno: Petr`
- „bydlím v Brně" → `město: Brno`
- „baví mě python" → `zájmy: [python]`

Profil se vkládá do každého LLM dotazu — JARVIS ví kdo jsi.

### Neural Memory / SQLite Memory (`memory_data/memories.db`)
- Ukládá konverzace s důležitostí a tagy
- Keyword recall s recency scoring
- Automatický decay + maintenance každých 6 hodin
- **SQLite backend** — rychlý i pro tisíce vzpomínek, bez RAM overhead
- Automatická migrace z původního JSON při prvním spuštění

### Daily Summarizer
Každou půlnoc Ollama zpracuje dnešní konverzace a extrahuje fakta do UserProfile.

### MCP Knowledge Graph (`~/.jarvis_mcp_memory/`)
Persistentní knowledge graph přes `@modelcontextprotocol/server-memory` — entity a vztahy.

---

## Architektura

```
jarvis.py               — bootstrap (10 řádků)
app_core.py             — orchestrátor, event loop, lazy init (rychlý start)
gui/                    — GUI package (OpenCode styl — top bar, fullwidth chat)
  ├── app_window.py     — JarvisGUI hlavní okno + všechny callbacks
  ├── orb.py            — animovaný orb + částice
  ├── chat.py           — chat panel, render zpráv, export do .md
  ├── settings.py       — SettingsDialog
  └── constants.py      — barvy, ORB_COLORS, blend/lerp
llm.py                  — lokální router + Ollama streaming + user profil inject
commands/               — balíček příkazů (system, apps, media, files, utils)
  ├── system.py         — shutdown, restart, hlasitost, jas, systém info
  ├── apps.py           — open/kill/install aplikace (safe_run)
  ├── media.py          — YouTube, screenshot, klávesnice, timer (safe_run)
  ├── files.py          — soubory, složky, clipboard, web (safe_run)
  └── utils.py          — kalkulačka, překlad, poznámky, počasí, wiki, měna + safe_run helper
tts.py                  — edge-tts / pyttsx3, queue worker (sériové přehrávání)
stt.py                  — Google STT + offline Sphinx fallback
memory.py               — SQLite memory + DailySummarizer (migrace z JSON)
user_profile.py         — permanentní fakta o uživateli
security_v2.py          — audit log, 3 úrovně oprávnění, dangerous patterns
event_bus.py            — pub/sub event systém
agents.py               — background agents (CPU/RAM monitor, idle detector)
scheduler.py            — plánování úloh (at/after/every/every_day_at)
plugin_system.py        — skill loader (manifest.json + lazy loading)
mcp_bridge.py           — MCP klient (filesystem, brave-search, git, memory)
dashboard.py            — web dashboard FastAPI (port 8002)
wake_word_detector.py   — wake word detekce (pause/resume při STT)

plugins/custom/
├── greeting/           — pozdravy dle denní doby
├── calculator/         — výpočty, procenta, sqrt
├── timer/              — timer/alarm hlasem + callback
├── clipboard/          — schránka (xclip/pyperclip)
├── mcp_filesystem/     — čtení souborů, strom, full-text hledání
├── mcp_fetch/          — DuckDuckGo search + URL fetch
├── mcp_git/            — git log/status/diff/blame
├── mcp_brave/          — Brave Search (vyžaduje API klíč)
└── mcp_memory/         — knowledge graph přes MCP
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes     (greeting, calculator, timer, MCP skills…)
  ├─ 2. Lokální router   (95% příkazů bez LLM — otevři, hlasitost…)
  └─ 3. Ollama stream    (AI konverzace, kód, překlad, vysvětlení)
           │
           ├─ UserProfile kontext (jméno, město, zájmy…)
           └─ Memory kontext (relevantní vzpomínky)
  │
  ▼
Security check → CommandExecutor / MCP → TTS worker queue
```

---

## Konfigurace

### config.json
```json
{
  "ollama_url":        "http://localhost:11434/api/chat",
  "ollama_model":      "qwen2.5:3b",
  "tts_enabled":       true,
  "tts_voice":         "cs-CZ-AntoninNeural",
  "tts_rate":          170,
  "stt_language":      "cs-CZ",
  "wake_word":         "jarvis",
  "wake_word_enabled": true
}
```

### .env (secrets — není v gitu)
```bash
cp .env.example .env
# Vyplň:
BRAVE_API_KEY=tvůj_klíč   # pro Brave Search MCP
```

### Doporučené modely Ollama
| Model | RAM | Rychlost | Kvalita |
|---|---|---|---|
| `qwen2.5:3b` | ~3 GB | ⚡⚡⚡ | ★★★ |
| `llama3.2:3b` | ~3 GB | ⚡⚡⚡ | ★★★ |
| `llama3.1:8b` | ~8 GB | ⚡ | ★★★★★ |

### Security
- **SAFE** — vždy povoleno (čas, počasí, otevřít URL…)
- **STANDARD** — bez potvrzení (vytvořit soubor, poznámka…)
- **ELEVATED** — dialog potvrzení (smazat soubor, shutdown…)

Audit log: `~/.jarvis_audit.jsonl`

---

## Web Dashboard

**http://localhost:8002** — spouští se automaticky se JARVIS.

- CPU / RAM / Disk v reálném čase
- Status Ollama + aktuální model
- Stav background agentů
- Naplánované úlohy
- Audit log (posledních 20 akcí)
- Live logy přes WebSocket

---

## Troubleshooting

### Ollama se nespustí
```bash
curl http://localhost:11434/api/tags
ollama serve
ollama pull qwen2.5:3b
```

### TTS nefunguje
```bash
sudo apt install ffmpeg mpg123
pip install edge-tts
```

### Mikrofon nefunguje
```bash
sudo usermod -a -G audio $USER
python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```

### MCP filesystem nefunguje
```bash
node --version        # potřeba Node.js 18+
npx --version
npx -y @modelcontextprotocol/server-filesystem ~
```

### Brave Search nefunguje
```bash
# Zkontroluj .env
cat .env | grep BRAVE
# Klíč zdarma: https://api.search.brave.com/
```

---

## Vývoj a testy

### Spuštění testů
```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest test_jarvis.py -v
```

**177+ testů** pokrývají: config, STT, TTS (worker queue), LocalRouter, CommandExecutor (sandbox kalkulačka), AsyncEngine, ErrorHandler, PluginManager, Security (audit, dangerous patterns), WakeWord (pause/resume), UserProfile (normalizace diakritiky), GUI (headless), safe_run helper.

### CI/CD
GitHub Actions běží automaticky na každý push — Python 3.11 + 3.12, ubuntu-latest.

### Závislosti
```bash
pip install -r requirements.txt
```

| Balíček | Účel |
|---|---|
| `customtkinter` | Sci-fi HUD GUI |
| `requests` | Ollama API, počasí, web fetch |
| `edge-tts` | Kvalitní český hlas |
| `yt-dlp` | YouTube bez prohlížeče |
| `ffplay` (ffmpeg) | Audio/video přehrávač |
| `mcp` | Model Context Protocol klient |
| `fastapi` + `uvicorn` | Web dashboard |
| `psutil` | Systémové metriky |
| `SpeechRecognition` + `PyAudio` | Mikrofon (volitelné) |

### Přidání nové akce
1. Pattern do `LocalRouter.route()` v `llm.py`
2. Implementace `cmd_nazev()` v příslušném modulu `commands/` (system/apps/media/files/utils)
3. Export z `commands/__init__.py` do `CommandExecutor.execute()`
4. Oprávnění do `ACTION_PERMISSIONS` v `security_v2.py`
5. Test do `test_jarvis.py` nebo `tests/`

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP servery)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Licence

MIT — volně šiřitelný a upravitelný.
