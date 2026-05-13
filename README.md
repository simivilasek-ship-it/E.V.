# JARVIS v3.1 — Lokální AI asistent

Plnohodnotný AI asistent běžící **100% lokálně** — Ollama LLM, český hlas, ovládání celého PC, dlouhodobá paměť a rozšiřitelný skill systém.

## Obsah
- [Rychlý start](#rychlý-start)
- [Co umí](#co-umí)
- [Architektura](#architektura)
- [Skills — přidání vlastního](#skills--přidání-vlastního)
- [Smart Memory](#smart-memory)
- [Konfigurace](#konfigurace)
- [Troubleshooting](#troubleshooting)
- [Vývoj a testy](#vývoj-a-testy)

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

### Hlasové a textové ovládání PC
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
| „Zahraj Bohemian Rhapsody" | yt-dlp + ffplay |
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
| „Vypočítej 15% z 200" | Lokální kalkulačka |
| „Zapamatuj si X" | Neural memory |
| „Co si pamatuješ o X?" | Recall z memory |
| Obecná otázka / kód / matematika | Ollama LLM |

### Produktivita
| Příkaz | Akce |
|---|---|
| „Timer 5 minut" | Odpočet + notifikace |
| „Zkopíruj tento text" | Schránka |
| „Přidej poznámku nakoupit chleba" | `~/jarvis_notes.txt` |
| „Zobraz poznámky" | Výpis poznámek |

### Wake Word
Řekni **„Jarvis"** — asistent se probudí a začne poslouchat bez kliknutí.

---

## Architektura

```
jarvis.py           — bootstrap (11 řádků)
app_core.py         — orchestrátor, event loop, security, wake word
gui.py              — sci-fi HUD GUI (customtkinter + animovaný orb)
llm.py              — lokální router + Ollama streaming + user profil inject
commands.py         — implementace všech akcí (~60 příkazů)
tts.py              — edge-tts / pyttsx3, threading.Lock (bez dvojího hlasu)
stt.py              — Google STT + offline Sphinx fallback
memory.py           — neural memory + DailySummarizer
user_profile.py     — permanentní fakta o uživateli (nikdy nedecay)
security_v2.py      — audit log, permission levels, dangerous pattern detection
event_bus.py        — pub/sub event systém
agents.py           — background agents (CPU/RAM monitor, idle detector)
scheduler.py        — plánování úloh (at/after/every/every_day_at)
plugin_system.py    — skill loader (manifest.json + lazy loading)
llm_router.py       — LLM router 2.0 (task detection, model fallback)
dashboard.py        — web dashboard FastAPI (port 8002)
wake_word_detector.py — wake word detekce (porpoise / SR fallback)
```

### Datový tok

```
Uživatel (hlas/text)
  │
  ▼
JarvisApp._process_command()
  ├─ 1. Plugin/Skill routes   (greeting, calculator, timer, clipboard…)
  ├─ 2. Lokální router        (95% příkazů bez LLM — otevři, hlasitost…)
  └─ 3. Ollama LLM stream     (AI konverzace, kód, překlad, vysvětlení)
           │
           ├─ UserProfile kontext (jméno, město, zájmy…)
           └─ Neural memory kontext (relevantní vzpomínky)
  │
  ▼
Security check → CommandExecutor → TTS (fronta, bez double-speak)
```

### Skills pipeline

```
plugins/custom/
├── greeting/         ← manifest.json + skill.py
├── calculator/       ← výpočty, procenta
├── timer/            ← timer/alarm hlasem
└── clipboard/        ← schránka (xclip/pyperclip)
```

Každý skill je **izolovaná složka** — stačí přidat novou a JARVIS ji načte automaticky při startu.

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
  "triggers": ["klíčové", "slovo"]
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

Žádný restart není potřeba pokud zavoláš `plugin_manager.reload_plugin("muj_skill")`. Při příštím startu se načte automaticky.

---

## Smart Memory

JARVIS si pamatuje informace o tobě **permanentně** (přes restarty):

### User Profile (`~/.jarvis_user_profile.json`)
Při každé konverzaci JARVIS automaticky extrahuje fakta:
- „jmenuji se Petr" → `jméno: Petr`
- „bydlím v Brně" → `město: Brno`
- „baví mě python" → `zájmy: [python]`

Profil se vkládá do každého LLM dotazu — JARVIS ví kdo jsi.

### Daily Summarizer
Každou půlnoc Ollama zpracuje dnešní konverzace, extrahuje fakta a uloží je do profilu. Výsledné shrnutí je dostupné v neural memory s tagy `daily_summary`.

### Neural Memory (`memory_data/`)
- Ukládá konverzace s důležitostí a tagy
- Sémantické vyhledávání pro LLM kontext
- Automatický decay neaktivních vzpomínek (konverzace decayují, user fakta nikdy)
- Auto-maintenance každých 6 hodin

### Příkazy pro paměť
```
„Zapamatuj si [informace]"    → uloží do neural memory
„Co si pamatuješ o [téma]?"   → recall z memory
„Statistiky paměti"           → počet vzpomínek, avg importance
„Údržba paměti"               → spustí decay + merge
```

---

## Konfigurace

### config.json (hlavní)
```json
{
  "ollama_url":   "http://localhost:11434/api/chat",
  "ollama_model": "qwen2.5:3b",
  "tts_enabled":  true,
  "tts_voice":    "cs-CZ-AntoninNeural",
  "tts_rate":     170,
  "history_size": 20,
  "stt_language": "cs-CZ",
  "wake_word":    "jarvis",
  "wake_word_enabled": true
}
```

Model lze měnit přímo v GUI — uloží se automaticky.

### Dostupné hlasy (edge-tts)
- `cs-CZ-AntoninNeural` — muž (výchozí)
- `cs-CZ-VlastaNeural` — žena

### Doporučené modely Ollama
| Model | Rychlost | Kvalita | RAM |
|---|---|---|---|
| `qwen2.5:3b` | ⚡⚡⚡ | ★★★ | ~3 GB |
| `llama3.2:3b` | ⚡⚡ | ★★★ | ~3 GB |
| `llama3.1:8b` | ⚡ | ★★★★★ | ~8 GB |

### Security (`security_v2.py`)
Tříúrovňový systém oprávnění:
- **SAFE** — vždy povoleno (čas, počasí, otevřít URL…)
- **STANDARD** — bez potvrzení (vytvořit soubor, poznámka…)
- **ELEVATED** — vyžaduje potvrzení dialogem (smazat soubor, kill process, shutdown…)

Audit log se ukládá do `~/.jarvis_audit.jsonl`.

---

## Web Dashboard

Dostupný na **http://localhost:8002** — spouští se automaticky se JARVIS.

Zobrazuje:
- CPU / RAM / Disk v reálném čase
- Status Ollama + aktuální model
- Stav background agentů
- Naplánované úlohy (scheduler)
- Audit log (posledních 20 akcí)
- Live logy přes WebSocket

---

## Troubleshooting

### Ollama se nespustí
```bash
curl http://localhost:11434/api/tags   # test připojení
ollama serve                           # manuální start
ollama pull qwen2.5:3b                 # stáhni model
```

### TTS nefunguje / není slyšet
```bash
sudo apt install ffmpeg mpg123         # audio přehrávač
pip install edge-tts                   # TTS engine
python -c "import edge_tts; print('OK')"
```

### Mikrofon nefunguje
```bash
sudo usermod -a -G audio $USER
python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```

### Wake word nefunguje
```bash
pip install porpoise                   # nejlehčí detektor
# nebo — funguje i bez porpoise (SR fallback)
```

### Dashboard nedostupný (port 8002)
```bash
python dashboard.py                    # manuální start
curl http://localhost:8002/            # test
```

---

## Vývoj a testy

### Spuštění testů
```bash
source ~/Stažené/jarvis-env/bin/activate
cd "/home/simi/Stažené/nepojmenovaná složka"
python -m pytest test_jarvis.py -v
```

54 testů pokrývá: config, STT, TTS (lock/stop), LLM router, CommandExecutor,
AsyncEngine, ErrorHandler, PluginManager, Security (audit log, dangerous patterns, confirm_action).

### Závislosti
```bash
pip install -r requirements.txt
```

| Balíček | Účel |
|---|---|
| `customtkinter` | Sci-fi HUD GUI |
| `requests` | Ollama API, počasí |
| `edge-tts` | Kvalitní český hlas |
| `yt-dlp` | YouTube přehrávání a stahování |
| `ffplay` (ffmpeg) | Audio přehrávač |
| `pyautogui` | Klávesnice/myš simulace |
| `psutil` | Systémové info a procesy |
| `fastapi` + `uvicorn` | Web dashboard |
| `SpeechRecognition` + `PyAudio` | Mikrofon (volitelné) |

### Přidání nové akce (bez skill systému)
1. Přidej pattern do `LocalRouter.route()` v `llm.py`
2. Implementuj `_cmd_nazev_akce()` v `commands.py`
3. Přidej akci do `ACTION_PERMISSIONS` v `security_v2.py`
4. Přidej unit test do `test_jarvis.py`

---

## Požadavky

- Python 3.11+
- [Ollama](https://ollama.com) — `ollama serve` + `ollama pull qwen2.5:3b`
- ffmpeg — `sudo apt install ffmpeg` (TTS + YouTube)
- brightnessctl — `sudo apt install brightnessctl` (jas, volitelné)

---

## Licence

MIT — volně šiřitelný a upravitelný.
