# JARVIS v4.3 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, multi-modalita (OCR, kamera, screen describe), ReAct agentní plánování, 9 MCP serverů, 14 skills, plugin marketplace a sandbox.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

---

## Co je nového v v4.3

| Změna | Detail |
|---|---|
| **356 testů, 0 failed** | Stabilizace celé test suite — opraveny mock cesty, API nesoulady, timeouty |
| **Plugin sandbox** | `ManifestValidator` + `ThreadPoolExecutor` timeout — pluginy nemohou zablokovat JARVIS |
| **Manifest validace** | Povinná pole, typy, whitelist permissions (`answer/system/media/files/mcp/internal`) |
| **MCP mock testy** | 16 testů MCPBridge bez reálného npx serveru — CI nezávisí na síti |
| **Ruff linter** | `.ruff.toml` + `.pre-commit-config.yaml` — 0 kritických F821/F811 chyb |
| **Vosk offline STT** | `VoskSTT` fallback při výpadku internetu — Czech model 50 MB |
| **Streaming TTS** | `edge-tts → ffplay stdin` — první slovo slyšíš o ~1s dříve |
| **`_parse_currency`** | Parsování měnových konverzí (100 USD na CZK) |

---

## Rychlý start

```bash
chmod +x install.sh && ./install.sh
bash start_jarvis.sh
```

Nebo manuálně:
```bash
source ~/Stažené/jarvis-env/bin/activate
ollama serve &
python jarvis.py
```

### Volitelné závislosti

```bash
# Offline STT
pip install vosk
# Model stáhne JARVIS automaticky (~50 MB)

# Vision / OCR
ollama pull llava:7b
sudo apt install tesseract-ocr tesseract-ocr-ces
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
| „Klikni na 500 300" | Computer Control MCP |
| „Seznam oken" | Všechna otevřená okna |
| „Vypni / Restartuj počítač" | Shutdown / Restart |

### Vision — Multi-modalita
| Příkaz | Akce |
|---|---|
| „Co vidíš / Popiš obrazovku" | Screenshot + LLaVA |
| „Přečti text / OCR" | pytesseract OCR |
| „Zapni kameru / Webcam" | cv2 + LLaVA |

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

### Informace a AI
| Příkaz | Akce |
|---|---|
| „Kolik je hodin v Tokiu" | MCP Time server |
| „Počasí Praha" | wttr.in |
| „Co je Python?" | Wikipedia |
| „Přelož hello world" | Ollama překlad |
| „Vypočítej 15% z 200" | AST sandbox |
| „100 USD na CZK" | Měnový konvertor |
| „Zapamatuj si X" | SQLite memory |
| Obecná otázka / kód | Ollama LLM |

### Plugin Marketplace
| Příkaz | Akce |
|---|---|
| „marketplace seznam" | Dostupné pluginy |
| „nainstaluj plugin X" | ZIP z GitHubu |
| „nainstaluj z github user/repo" | Přímá instalace |
| „odinstaluj / aktualizuj plugin X" | Správa pluginů |

### ReAct agent (vícesvůlové úkoly)
```
„Najdi cenu RTX 4090 a ulož ji do poznámky"
„Zjisti počasí v Praze a zapiš ho"
„Porovnej ceny RTX 4080 vs 4090"
```

### GUI klávesové zkratky
| Zkratka | Akce |
|---|---|
| `Enter` | Odeslat |
| `Mezerník` | Mikrofon |
| `Ctrl+L` | Vymazat chat |
| `Ctrl+E` | Export `.md` |
| `Esc` | Focus input |

---

## MCP integrace (9 serverů)

| Server | Příkaz | API klíč |
|---|---|---|
| **Filesystem** | „přečti soubor X", „strom ~/Projekty" | ❌ |
| **Fetch** | „načti stránku github.com" | ❌ |
| **Git** | „git log", „git status", „git diff" | ❌ |
| **Memory Graph** | „zapamatuj si X", „co víš o X" | ❌ |
| **Time** | „kolik je hodin v Tokiu" | ❌ |
| **Sequential Thinking** | „přemýšlej jak X", „rozlož na kroky X" | ❌ |
| **Puppeteer** | „screenshot webu X", „klikni na #id" | ❌ |
| **Computer Control** | klikání, psaní, okna, screenshot | ❌ |
| **Brave Search** | „vyhledej X", „novinky o X" | ✅ BRAVE_API_KEY |

```bash
echo "BRAVE_API_KEY=tvůj_klíč" >> .env
```

---

## Plugin systém — 14 skills

```
plugins/custom/
├── calculator/              — AST sandbox kalkulačka
├── clipboard/               — xclip / pyperclip
├── greeting/                — pozdravy dle denní doby
├── marketplace/             — stahování pluginů z GitHubu
├── timer/                   — odpočet + hlasová notifikace
├── mcp_brave/               — Brave Search
├── mcp_computer_control/    — klikání, psaní, okna, OCR
├── mcp_fetch/               — DuckDuckGo + URL fetch
├── mcp_filesystem/          — čtení souborů, strom, hledání
├── mcp_git/                 — git log/status/diff/blame
├── mcp_memory/              — knowledge graph
├── mcp_puppeteer/           — browser automation
├── mcp_sequential_thinking/ — krok-za-krokem plánování
└── mcp_time/                — časová pásma (40+ měst)
```

### Přidání vlastního pluginu

```json
// manifest.json
{
  "name": "muj_skill",
  "version": "1.0.0",
  "description": "Co skill dělá",
  "permissions": ["answer"],
  "triggers": ["klíčové slovo"]
}
```

**permissions:** `answer` · `system` · `media` · `files` · `mcp` · `internal`

```python
# skill.py
import re
_RE = re.compile(r"\b(klicove\s+slovo)\b", re.IGNORECASE)

def _handle(text): return "Odpověď!", {"action": "answer", "params": {}}
def get_routes():  return [{"pattern": _RE, "handler": _handle}]
def get_actions(): return {}
```

Plugin se automaticky načte při startu. Handler běží v sandboxu s timeoutem.

---

## Smart Memory

- **User Profile** (`~/.jarvis_user_profile.json`) — fakta z konverzace, vkládá se do každého LLM dotazu
- **SQLite Memory** (`memory_data/memories.db`) — keyword recall + recency scoring + embedding similarity
- **MCP Knowledge Graph** (`~/.jarvis_mcp_memory/`) — entity a vztahy

```bash
# Opt-in lokální embeddingy (lepší recall)
pip install sentence-transformers
```

---

## Architektura

```
jarvis.py           — bootstrap
app_core.py         — orchestrátor, lazy init
gui/                — OpenCode styl (top bar + fullwidth chat)
llm.py              — LLMEngine + LocalRouter (95% bez LLM)
agent_react.py      — ReAct smyčka
agent_graph.py      — Graf agent (Planner→Router→Executor→Critic)
vision.py           — VisionEngine (OCR, screen describe, webcam)
commands/           — safe_run, system, apps, media, files, utils
tts.py              — streaming TTS (ffplay stdin) + pyttsx3
stt.py              — Google STT + VoskSTT offline fallback
memory.py           — SQLite + EmbeddingEngine
plugin_system.py    — ManifestValidator + sandbox + lazy loading
plugin_marketplace.py — GitHub ZIP download
mcp_bridge.py       — MCPBridge (9 serverů)
security_v2.py      — SAFE/STANDARD/ELEVATED + audit log
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
  "plugin_handler_timeout": 5.0
}
```

### Modely Ollama
| Model | RAM | Použití |
|---|---|---|
| `qwen2.5:3b` | ~3 GB | Výchozí |
| `llama3.1:8b` | ~8 GB | Lepší kvalita |
| `llava:7b`    | ~8 GB | Vision |

---

## Vývoj a testy

```bash
source ~/Stažené/jarvis-env/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 356 testů, 0 failed
```

### Linter
```bash
pip install ruff
ruff check . --select F821,F811,E711,E712
# All checks passed!
```

### CI/CD
GitHub Actions — Python 3.11 + 3.12, ruff lint + pytest, ubuntu-latest.

---

## Požadavky

- Python 3.11+
- Node.js 18+ (MCP servery)
- [Ollama](https://ollama.com) — `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg`

---

## Plánované featury

- [ ] Docker image (headless server mód)
- [ ] Plugin autoupdate (VERSION v manifestu)
- [ ] Rate limiting LLM
- [ ] Kontext aktivního okna v system promptu

---

## Licence

MIT — volně šiřitelný a upravitelný.
