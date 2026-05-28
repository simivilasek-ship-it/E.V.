# JARVIS v4.3 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, multi-modalita (OCR, kamera, screen describe), grafový agent (Planner→Router→Executor→Critic), ReAct agent, 9 MCP serverů, plugin marketplace se sandboxem a 390+ testy.

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)

---

## Co je nového

### v4.3 — aktuální
| Změna | Detail |
|---|---|
| **LocalRouter vyčleněn** | `local_router.py` — samostatný modul, snazší testování a rozšiřování |
| **Graf agent konfigurovatelný** | `agent_max_steps`, `agent_timeout`, `agent_llm_tokens` v `config.json` |
| **390+ testů, 0 failed** | Nové sady: `test_async_utils.py` (16), `test_event_bus.py` (13), `test_integration.py` (30) |
| **Thread-safe singletons** | `_agent_lock` / `_graph_lock` — race condition v agentní inicializaci odstraněna |
| **Token budget** | LLM history se dynamicky ořezává aby nepřekročila 3072 tokenů |
| **Event bus timeout** | Callbacky v daemon threadech, 5s limit — pomalý callback nezablokuje app |
| **AsyncEngine cleanup fix** | `_cleanup_task` vždy smaže dokončenou úlohu, pak teprve čistí nejstarší |
| **Memory NaN guard** | Clamp `sem_score` / `importance` / `recency` na `[0.0, 1.0]`, odmítnutí NaN/inf |
| **Plugin marketplace** | 7 pluginů v REGISTRY (calculator, timer, clipboard, greeting, MCP), 404 hlášení |
| **`_clear_mem` error handling** | Metoda místo lambda, chyby se zobrazí v GUI |
| **Kalkulátor hardening** | Limit 500 znaků, hloubka AST max 50, exponent max 300 |

### v4.2
| Změna | Detail |
|---|---|
| **TTS streaming** | Hlasová odezva ~1 s — věta po větě z generátoru |
| **Graf timeout** | Circuit breaker 120 s — grafový agent nikdy nezamrzne |
| **Fuzzy matching** | rapidfuzz zachytí překlepy: „otrevi crhome" → otevři chrome |
| **Plugin sandbox** | AST kontrola importů, 7 named permissions v manifestu |
| **LLM Router** | Automatický výběr modelu a teploty podle TaskType (kód, math, překlad…) |
| **STT validace** | `set_language()` validuje oproti 23 podporovaným jazykům |

### v4.1
| Změna | Detail |
|---|---|
| **Grafový agent** | Planner→Router→Executor→Critic s retry/replan |
| **Lokální embeddingy** | `sentence-transformers` — sémantické vyhledávání v paměti |
| **Plugin marketplace** | Stahování pluginů z GitHub jedním příkazem |
| **DailySummarizer** | Denní extrakce faktů z konverzací do UserProfile |

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
jarvis.py             — bootstrap
app_core.py           — orchestrátor, lazy init, routing pipeline
│
├── local_router.py   — LocalRouter: regex + fuzzy, 95% příkazů bez LLM
├── llm.py            — LLMEngine + token budget + streaming
├── llm_router.py     — LLMRouter: TaskType → model/temperature
│
├── agent_graph.py    — Graf agent (Planner→Router→Executor→Critic)
├── agent_react.py    — ReAct agent (Thought→Action→Observation)
├── agent_tools.py    — ToolRegistry (16+ nástrojů)
│
├── memory.py         — SQLite + EmbeddingEngine + DailySummarizer
├── user_profile.py   — permanentní fakta o uživateli
│
├── plugin_system.py  — sandbox (AST kontrola), lazy loading
├── plugin_marketplace.py — 7 pluginů v REGISTRY, builtin + GitHub ZIP
│
├── tts.py            — streaming TTS (edge-tts → ffplay stdin) + pyttsx3
├── stt.py            — Google STT + VoskSTT offline fallback
├── vision.py         — OCR, screen describe, webcam + LLaVA
├── wake_word_detector.py — detekce „JARVISe", pause/resume s STT
│
├── security_v2.py    — AuditLog, 5 úrovní oprávnění, confirmation
├── mcp_bridge.py     — MCP klient (9 serverů)
│
├── health_check.py   — monitoring Ollama, RAM, disk, CPU
├── cache_manager.py  — LRU + disk cache
├── offline_mode.py   — fronta příkazů + fallback knowledge base
├── async_utils.py    — AsyncEngine, prioritní fronta (4 workers)
├── event_bus.py      — PUB/SUB, async callbacky s 5s timeoutem
├── agents.py         — background monitoring (CPU/RAM/disk)
├── scheduler.py      — at/after/every/every_day_at
├── error_handling.py — centrální error handler + recovery
│
├── commands/         — 40+ akcí
│   ├── system.py     — čas, datum, hlasitost, jas, shutdown
│   ├── apps.py       — open/kill/install aplikace
│   ├── files.py      — soubory, web, clipboard
│   ├── media.py      — screenshot, youtube, timer, klávesnice
│   └── utils.py      — kalkulačka, překlad, poznámky, wiki, počasí
│
├── dashboard.py      — web UI FastAPI (localhost:8002)
├── gui/              — Tkinter GUI (chat, orb, settings)
└── config.py         — centrální konfigurace (v4.2.0)
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
  "plugin_handler_timeout": 5.0,
  "agent_max_steps":        8,
  "agent_max_retries":      2,
  "agent_max_replans":      1,
  "agent_timeout":          120,
  "agent_llm_tokens":       500
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
source venv/bin/activate
python -m pytest tests/ test_jarvis.py -v
# 390+ testů, 0 failed
```

**Testovací sady:**

| Soubor | Počet | Pokrývá |
|---|---|---|
| `test_jarvis.py` | 108 | Integrace — config, STT, TTS, LocalRouter, LLM, commands, plugins |
| `tests/test_agent_graph.py` | 27 | Grafový agent — uzly, plánování, retry, timeout |
| `tests/test_commands.py` | 24 | CommandExecutor — 40+ akcí |
| `tests/test_security.py` | 22 | Security — úrovně oprávnění, audit log |
| `tests/test_new_modules.py` | 23 | Health check, cache, offline mode, async engine |
| `tests/test_async_utils.py` | 16 | AsyncEngine — priority queue, task lifecycle, cleanup |
| `tests/test_event_bus.py` | 13 | EventBus — subscribe, publish, wildcard, timeout |
| `tests/test_integration.py` | 30 | Integrace — security pipeline, path validation, sandbox |
| `tests/test_react_agent.py` | 17 | ReAct agent — parsing, tool calls, mock LLM |
| `tests/test_vision.py` | 15 | Vision — OCR, screen describe, webcam |
| `tests/test_llm.py` | 18 | LLMEngine, LLMRouter, TaskType detection |
| `tests/test_memory.py` | 11 | JarvisMemory — store, recall, NaN guard |
| ostatní | ~66 | STT+Vosk, TTS streaming, marketplace, embeddingy… |

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
- [ ] OfflineManager integrace do routing pipeline
- [ ] Spotify API (aktuálně fallback na `xdg-open`)
- [ ] Kontext token počítání přes tiktoken místo heuristiky

---

## Licence

MIT — volně šiřitelný a upravitelný.
