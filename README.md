# JARVIS v4.0 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, dlouhodobá paměť, MCP integrace, ReAct agentní plánování a multi-modalita (OCR, kamera, popis obrazovky).

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

## Obsah
- [Rychlý start](#rychlý-start)
- [Co je nového ve v4.0](#co-je-nového-ve-v40)
- [Co umí](#co-umí)
- [ReAct agent](#react-agent)
- [Multi-modalita](#multi-modalita)
- [MCP integrace](#mcp-integrace)
- [Skills — přidání vlastního](#skills--přidání-vlastního)
- [Smart Memory](#smart-memory)
- [Architektura](#architektura)
- [Konfigurace](#konfigurace)
- [Troubleshooting](#troubleshooting)
- [Vývoj a testy](#vývoj-a-testy)

---

## Co je nového ve v4.0

| Změna | Detail |
|---|---|
| **ReAct agent** | Vícesvůlové úkoly — JARVIS plánuje kroky sám (Thought→Action→Observation→Answer) |
| **Multi-modalita** | OCR textu z obrazovky, popis obrazovky přes LLaVA, webcam vstup |
| **Computer Control MCP** | Klikání, psaní, pohyb myší, správa oken přes AI |
| **Brave Search MCP** | Opravena inicializace — BRAVE_API_KEY načítán z `.env` přes `python-dotenv` |
| **Nastavení GUI** | Plné nastavení (STT, TTS, MCP přepínače, logy) přes ⚙ tlačítko |
| **Šipky v chatu** | ↑/↓ procházení historie zpráv jako v terminálu |
| **URL router fix** | „spust web/chromium + URL" vždy otevře prohlížeč (ne YouTube) |
| **MCP výstup** | Truncace na 32 000 znaků + timeout 30 s + chybové stringy místo None |
| **Unit testy** | +50 testů: safe_run edge-cases, MCP bridge (mock), ReAct smyčka, Vision |

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

### Pro multi-modalitu (nepovinné)
```bash
ollama pull llava:7b                          # popis obrazovky + webcam
sudo apt install tesseract-ocr tesseract-ocr-ces   # OCR
pip install pytesseract opencv-python
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
| „Klikni na 500 300" | Klik na souřadnice (Computer Control MCP) |
| „Seznam oken" | Všechna otevřená okna |
| „Přepni na okno Chrome" | Aktivace okna |

### Zvuk, obraz, klávesnice
| Příkaz | Akce |
|---|---|
| „Hlasitost na 60 / Ztlum" | PulseAudio / ALSA |
| „Jas na 70" | brightnessctl |
| „Screenshot" | Uloží na plochu |
| „Napíš Hello World" | Simulace klávesnice |
| „Stiskni Ctrl+C" | pyautogui |

### Multi-modalita (Vision)
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA popis |
| „Přečti text z obrazovky / OCR" | pytesseract OCR |
| „Zapni kameru / Webcam" | cv2 záběr + LLaVA popis |

### YouTube & média
| Příkaz | Akce |
|---|---|
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay (bez prohlížeče) |
| „Stáhni video X" | yt-dlp download |
| „Info o videu X" | Metadata bez stažení |

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

### GUI klávesové zkratky
| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat příkaz |
| `↑ / ↓` | Procházet historii zpráv (jako v terminálu) |
| `Mezerník` | Aktivovat mikrofon (pokud focus není v inputu) |
| `Ctrl+L` | Vymazat chat log |
| `Ctrl+E` | Exportovat konverzaci do `.md` na plochu |
| `Esc` | Přesunout focus do input pole |

---

## ReAct agent

JARVIS v4.0 automaticky rozpozná **vícesvůlové úkoly** a plánuje kroky sám — bez nutnosti explicitních příkazů.

### Jak to funguje

```
Uživatel: "Najdi cenu RTX 4090 a ulož ji do poznámky"

Thought: Musím vyhledat cenu na webu
Action: web_search(query="RTX 4090 cena 2025")
Observation: RTX 4090 stojí ~35 000 Kč

Thought: Mám výsledek, uložím do poznámky
Action: note_add(note="RTX 4090: ~35 000 Kč")
Observation: Poznámka uložena.

Answer: Cena RTX 4090 (~35 000 Kč) uložena do poznámek.
```

### Příklady vícesvůlových úkolů
- „Najdi cenu GPU a ulož do poznámky"
- „Zjisti počasí v Praze a zapiš ho"
- „Porovnej ceny modelů RTX 4080 vs 4090"
- „Zkontroluj web a pak otevři stránku"
- „Ulož si co jsem dnes dělal"

### Dostupné nástroje agenta

| Nástroj | Popis |
|---|---|
| `web_search` | Brave Search nebo Google (dle konfigurace) |
| `fetch_url` | Stáhne obsah webové stránky (MCP fetch) |
| `note_add` / `note_list` | Poznámky |
| `memory_store` / `memory_recall` | Dlouhodobá paměť |
| `calculate` | Sandbox kalkulačka |
| `get_weather` | Počasí |
| `get_time` | Čas |
| `open_url` / `open_app` | Prohlížeč / aplikace |
| `screenshot` | Screenshot |
| `wiki_search` | Wikipedia |
| `read_file` / `list_files` | Filesystem (pokud MCP aktivní) |

Jednoduchý příkaz („otevři chrome") jde přes rychlý lokální router — beze změny výkonu.

---

## Multi-modalita

### Popis obrazovky (LLaVA)
```
„Co vidíš na obrazovce?"
„Popiš mi co je otevřené"
```
Pořídí screenshot a pošle ho do LLaVA (`ollama pull llava:7b`).

### OCR textu
```
„Přečti text z obrazovky"
„OCR"
```
Screenshot + pytesseract — vrátí rozpoznaný text. Funguje i bez Ollamy.

### Webcam
```
„Zapni kameru"
„Webcam — co vidíš?"
```
Zachytí snímek z kamery (cv2) a pošle do LLaVA.

### Instalace
```bash
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract opencv-python
```

---

## MCP integrace

JARVIS integruje [Model Context Protocol](https://modelcontextprotocol.io). Servery běží přes `npx` / `uvx` jako subprocesy.

> **Požadavky:** Node.js 18+ (`sudo apt install nodejs npm`) a `pip install mcp`

### Dostupné MCP servery

| Server | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | „přečti soubor notes.txt", „strom ~/Projekty" | ❌ |
| **Web Fetch** | „načti stránku github.com" | ❌ |
| **Git** | „git log", „git status", „git diff" | ❌ |
| **Memory Graph** | „zapamatuj si X", „co víš o X" | ❌ |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |
| **Computer Control** | klikání, psaní, okna, OCR obrazovky | ❌ |
| **Sequential Thinking** | vícesvůlové plánování | ❌ |
| **Time** | přesný čas + časová pásma | ❌ |

### Konfigurace Brave Search
```bash
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

Při příštím startu se načte automaticky.

---

## Smart Memory

### User Profile (`~/.jarvis_user_profile.json`)
Fakta se extrahují automaticky z každé konverzace:
- „jmenuji se Petr" → `jméno: Petr`
- „bydlím v Brně" → `město: Brno`
- „baví mě python" → `zájmy: [python]`

Profil se vkládá do každého LLM dotazu.

### Neural Memory / SQLite (`memory_data/memories.db`)
- SQLite backend — rychlý i pro tisíce vzpomínek
- Keyword recall s recency scoring
- Automatický decay + maintenance každých 6 hodin

### MCP Knowledge Graph (`~/.jarvis_mcp_memory/`)
Persistentní knowledge graph přes `@modelcontextprotocol/server-memory`.

---

## Architektura

```
jarvis.py               — bootstrap (10 řádků)
app_core.py             — orchestrátor, event loop, lazy init
gui/                    — GUI package (OpenCode styl)
  ├── app_window.py     — hlavní okno + callbacks + historie šipkami
  ├── orb.py            — animovaný orb + částice
  ├── chat.py           — chat panel, export do .md
  ├── settings.py       — SettingsDialog (STT, TTS, MCP, logy)
  └── constants.py      — barvy, fonty
llm.py                  — lokální router + Ollama streaming
agent_react.py          — ReAct smyčka (Thought→Action→Observation)
agent_tools.py          — ToolRegistry (12 nástrojů pro agenta)
vision.py               — VisionEngine (OCR, screen describe, webcam)
commands/               — balíček příkazů
  ├── system.py         — shutdown, hlasitost, jas, systém info
  ├── apps.py           — open/kill/install aplikace
  ├── media.py          — YouTube, screenshot, klávesnice, vision
  ├── files.py          — soubory, clipboard, web
  └── utils.py          — kalkulačka, překlad, poznámky, počasí + safe_run
tts.py                  — edge-tts / pyttsx3, queue worker
stt.py                  — Google STT + offline Sphinx fallback
memory.py               — SQLite memory + DailySummarizer
user_profile.py         — permanentní fakta o uživateli
security_v2.py          — audit log, 3 úrovně oprávnění
mcp_bridge.py           — MCP klient (8 serverů)
plugin_system.py        — skill loader (manifest.json + lazy loading)
dashboard.py            — web dashboard FastAPI (port 8002)
agents.py               — background agents (CPU/RAM monitor)
scheduler.py            — plánování úloh
event_bus.py            — pub/sub event systém

plugins/custom/
├── greeting/           — pozdravy dle denní doby
├── calculator/         — výpočty, procenta
├── timer/              — timer/alarm hlasem
├── clipboard/          — schránka
├── mcp_filesystem/     — čtení souborů, full-text hledání
├── mcp_fetch/          — DuckDuckGo + URL fetch
├── mcp_git/            — git log/status/diff
├── mcp_brave/          — Brave Search
├── mcp_memory/         — knowledge graph
└── mcp_computer_control/ — klikání, psaní, okna, OCR
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Skill routes       (greeting, calculator, timer, MCP skills…)
  ├─ 2. Lokální router     (95% příkazů bez LLM — otevři, hlasitost…)
  ├─ 3. ReAct agent        (vícesvůlové úkoly — najdi X a ulož Y)
  └─ 4. Ollama stream      (AI konverzace, kód, překlad)
           │
           ├─ UserProfile kontext
           └─ Memory kontext
  │
  ▼
Security check → CommandExecutor / MCP / VisionEngine → TTS
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
BRAVE_API_KEY=tvůj_klíč        # Brave Search MCP
MCP_BRAVE_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
```

### Doporučené modely Ollama
| Model | RAM | Rychlost | Kvalita |
|---|---|---|---|
| `qwen2.5:3b` | ~3 GB | ⚡⚡⚡ | ★★★ |
| `llama3.2:3b` | ~3 GB | ⚡⚡⚡ | ★★★ |
| `llama3.1:8b` | ~8 GB | ⚡ | ★★★★★ |
| `llava:7b` | ~8 GB | ⚡ | ★★★★ (vision) |

### Security
- **SAFE** — vždy povoleno (čas, počasí, OCR, popis obrazovky…)
- **STANDARD** — bez potvrzení (vytvořit soubor, poznámka, webcam…)
- **ELEVATED** — dialog potvrzení (smazat soubor, shutdown…)

Audit log: `~/.jarvis_audit.jsonl`

---

## Web Dashboard

**http://localhost:8002** — spouští se automaticky se JARVIS.

- CPU / RAM / Disk v reálném čase
- Status Ollama + aktuální model
- Stav background agentů
- Audit log (posledních 20 akcí)
- Live logy přes WebSocket

---

## Troubleshooting

### Ollama se nespustí
```bash
curl http://localhost:11434/api/tags
ollama serve && ollama pull qwen2.5:3b
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

### MCP nefunguje
```bash
node --version   # potřeba Node.js 18+
pip install mcp
```

### Brave Search nefunguje
```bash
cat .env | grep BRAVE
pip install python-dotenv
```

### OCR nefunguje
```bash
sudo apt install tesseract-ocr tesseract-ocr-ces
pip install pytesseract
```

### Vision / LLaVA nefunguje
```bash
ollama pull llava:7b
pip install opencv-python
```

---

## Vývoj a testy

### Spuštění testů
```bash
source venv/bin/activate
python -m pytest tests/ -v
```

**200+ testů** pokrývají: config, STT, TTS, LocalRouter, CommandExecutor, AsyncEngine, ErrorHandler, PluginManager, Security, WakeWord, UserProfile, GUI (headless), safe_run, MCP bridge (mock), ReAct agent (mock LLM), Vision (mock pytesseract/cv2).

### CI/CD
GitHub Actions — Python 3.11 + 3.12, ubuntu-latest, každý push.

### Závislosti
```bash
pip install -r requirements.txt
```

| Balíček | Účel |
|---|---|
| `customtkinter` | Sci-fi HUD GUI |
| `requests` | Ollama API, web fetch |
| `edge-tts` | Kvalitní český hlas |
| `yt-dlp` | YouTube bez prohlížeče |
| `mcp` | Model Context Protocol klient |
| `fastapi` + `uvicorn` | Web dashboard |
| `psutil` | Systémové metriky |
| `SpeechRecognition` + `PyAudio` | Mikrofon (volitelné) |
| `pytesseract` | OCR (volitelné) |
| `opencv-python` | Webcam (volitelné) |
| `python-dotenv` | Načítání `.env` |

### Přidání nové akce
1. Pattern do `LocalRouter.route()` v `llm.py`
2. Implementace `cmd_nazev()` v `commands/`
3. Export z `commands/__init__.py`
4. Oprávnění do `security_v2.py`
5. Test do `tests/`

---

## Plánované featury (v4.x)

- [ ] Lokální embeddingy pro memory (sentence-transformers)
- [ ] Plugin marketplace (stahování z GitHub jedním příkazem)
- [ ] Docker image pro headless server

---

## Požadavky

- Python 3.11+
- Node.js 18+ (pro MCP servery)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Licence

MIT — volně šiřitelný a upravitelný.
