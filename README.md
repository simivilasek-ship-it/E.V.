# JARVIS v2.0 — Hlasový asistent

Lokální hlasový asistent poháněný Ollama AI. Rozumí češtině, ovládá PC a odpovídá hlasem.

## Rychlý start

### Windows
```
install.bat
ollama serve
python jarvis.py
```

### Linux / Mac
```bash
chmod +x install.sh && ./install.sh
ollama serve
python3 jarvis.py
```

## Co umí

| Příkaz | Akce |
|---|---|
| „Otevři Chrome" | Spustí aplikaci |
| „Hledej počasí Praha" | Vyhledá na Google |
| „Dej hlasitost na 60" | Nastaví hlasitost |
| „Kolik je hodin?" | Řekne čas |
| „Timer 5 minut" | Spustí odpočet s notifikací |
| „Info o systému" | CPU, RAM, disk |
| „Přehraj / zastav" | Media klávesy |
| „Udělej screenshot" | Uloží na Plochu |
| „Zkopíruj Hello World" | Dá do schránky |
| „Ukonči notepad" | Zabije proces |
| „Napiš text ahoj" | Napíše do aktivního okna |
| „Stiskni Ctrl+C" | Simuluje klávesu |
| „Vypni počítač" | Shutdown |
| „Vymaž paměť" | Resetuje konverzaci |

## Konfigurace (`config.json`)

```json
{
  "ollama_model": "llama3.1:8b",
  "tts_enabled":  true,
  "tts_rate":     170,
  "history_size": 20,
  "window_size":  "560x760"
}
```

Vyměň `ollama_model` za jiný model (např. `"mistral:7b"`, `"llama3.2:3b"`).

## Závislosti

| Balíček | Účel |
|---|---|
| `customtkinter` | GUI |
| `requests` | Komunikace s Ollama |
| `SpeechRecognition` + `PyAudio` | Mikrofon |
| `pyttsx3` | TTS — JARVIS mluví |
| `pyautogui` | Ovládání PC |
| `psutil` | Systémové info |
| `pyperclip` | Schránka (české znaky) |
| `pycaw` *(Windows, volitelné)* | Přesná hlasitost |

## Požadavky

- Python 3.10+
- [Ollama](https://ollama.com) spuštěná (`ollama serve`)
- Model stažen (`ollama pull llama3.1:8b`)
