# JARVIS v2.0 — Hlasový asistent

Lokální AI asistent poháněný Ollama. Ovládá PC hlasem nebo textem, mluví kvalitním českým hlasem.

## Rychlý start

### Linux
```bash
chmod +x install.sh && ./install.sh
source jarvis-env/bin/activate
ollama serve &
python jarvis.py
```

### Windows
```
install.bat
ollama serve
python jarvis.py
```

### Jako aplikace (Linux — ikona na ploše)
```bash
# Zkopíruj start-jarvis.sh do ~/.local/bin/
cp start_jarvis.sh ~/.local/bin/start-jarvis.sh
chmod +x ~/.local/bin/start-jarvis.sh

# Vytvoř .desktop soubor
cp jarvis.desktop ~/.local/share/applications/
cp jarvis.desktop ~/Plocha/   # nebo ~/Desktop/
```

## Co umí

### Systém
| Příkaz | Akce |
|---|---|
| „Vypni počítač" | Shutdown |
| „Restartuj" | Restart |
| „Uspi počítač" | Suspend |
| „Info o systému" | CPU, RAM, disk |
| „Ukonči chrome" | Kill process |
| „Aktualizuj systém" | apt upgrade |

### Soubory
| Příkaz | Akce |
|---|---|
| „Vytvoř složku kytara v Dokumentech" | mkdir |
| „Vytvoř složku kytara a otevři ve vscode" | mkdir + VSCode |
| „Smaž soubor test.txt" | přesun do koše |
| „Přesuň soubor X do Y" | mv |
| „Najdi soubor readme" | find |
| „Otevři složku X ve vscode" | code /cesta |

### Aplikace & web
| Příkaz | Akce |
|---|---|
| „Otevři Chrome" | Spustí aplikaci |
| „Nainstaluj vlc" | apt install |
| „Odinstaluj vlc" | apt remove |
| „Hledej počasí Praha" | Google |
| „Počasí Praha" | wttr.in přímo |
| „Otevři github.com" | Browser |

### Zvuk & displej
| Příkaz | Akce |
|---|---|
| „Hlasitost na 60" | Nastaví hlasitost |
| „Ztlum" / „Odtlum" | Mute toggle |
| „Jas na 70" | Nastaví jas (brightnessctl) |
| „Zastav přehrávání" | Media klávesa |
| „Screenshot" | Uloží na plochu |

### Automatizace
| Příkaz | Akce |
|---|---|
| „Timer 5 minut" | Odpočet + notifikace |
| „Napiš hello world" | Napíše do aktivního okna |
| „Stiskni Ctrl+C" | Simuluje klávesu |
| „Zkopíruj Hello World" | Do schránky |
| „Nový soubor ve vscode" | Ctrl+N |

### Informace
| Příkaz | Akce |
|---|---|
| „Kolik je hodin?" | Čas |
| „Jaké je datum?" | Datum |
| „Jaký je jas CPU?" | System info |
| Obecné otázky | Ollama AI odpověď |

## Konfigurace (`config.json`)

```json
{
  "ollama_url":   "http://localhost:11434/api/chat",
  "ollama_model": "llama3.1:8b",
  "tts_enabled":  true,
  "tts_voice":    "cs-CZ-AntoninNeural",
  "history_size": 20,
  "window_size":  "600x820"
}
```

**Dostupné české hlasy (edge-tts):**
- `cs-CZ-AntoninNeural` — muž (výchozí)
- `cs-CZ-VlastaNeural` — žena

**Modely Ollama:** `llama3.1:8b` (výchozí), `mistral:7b`, `llama3.2:3b` (rychlejší)

## Závislosti

```
pip install -r requirements.txt
```

| Balíček | Účel |
|---|---|
| `customtkinter` | GUI |
| `requests` | Ollama API + počasí |
| `edge-tts` | Kvalitní český TTS hlas |
| `pyautogui` | Ovládání klávesnice/myši |
| `psutil` | Systémové info a procesy |
| `pyperclip` | Schránka (české znaky) |
| `SpeechRecognition` + `PyAudio` | Mikrofon (volitelné) |
| `pycaw` + `comtypes` | Přesná hlasitost Windows (volitelné) |

## Požadavky

- Python 3.10+
- [Ollama](https://ollama.com) — `ollama serve`
- Model — `ollama pull llama3.1:8b`
- ffplay (Linux TTS) — `sudo apt install ffmpeg`
- brightnessctl (jas) — `sudo apt install brightnessctl`

## Struktura projektu

```
jarvis.py          — hlavní aplikace
config.json        — konfigurace
requirements.txt   — Python závislosti
start_jarvis.sh    — launcher (Linux)
install.sh         — instalace Linux
install.bat        — instalace Windows
```
