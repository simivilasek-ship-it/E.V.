"""
E.V. — Průvodce prvního spuštění
Spusť: python jarvis.py --setup   nebo   python setup_wizard.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
VENV_PYTHON = Path(__file__).parent / "venv" / "bin" / "python"

# ── Barvy ─────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
NC     = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{NC} {msg}")
def warn(msg): print(f"  {YELLOW}!{NC} {msg}")
def err(msg):  print(f"  {RED}✗{NC} {msg}")
def hdr(msg):  print(f"\n{BOLD}{CYAN}{msg}{NC}")
def ask(prompt, default=""):
    val = input(f"  {prompt} [{default}]: ").strip()
    return val if val else default


# ── Kontroly ──────────────────────────────────────────────────────

def check_python() -> bool:
    v = sys.version_info
    if v >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    err(f"Python 3.11+ vyžadován, nalezena verze {v.major}.{v.minor}")
    return False


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        ok("ffmpeg")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        warn("ffmpeg nenalezen — TTS nebude fungovat")
        print("    Instalace: sudo apt install ffmpeg")
        return False


def check_ollama() -> tuple[bool, str]:
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        err("Ollama nenalezena")
        print("    Instalace: curl -fsSL https://ollama.com/install.sh | sh")
        return False, ""

    # Zjisti běžící modely
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            ok(f"Ollama běží — nainstalované modely: {models or '(žádné)'}")
            return True, models[0] if models else ""
    except Exception:
        warn("Ollama nalezena, ale neběží — spusť: ollama serve")
        return True, ""


def pull_model(model: str) -> bool:
    print(f"  Stahuji {model}... (může trvat několik minut)")
    try:
        result = subprocess.run(["ollama", "pull", model], timeout=600)
        if result.returncode == 0:
            ok(f"Model {model} stažen")
            return True
    except subprocess.TimeoutExpired:
        warn("Timeout při stahování modelu")
    except FileNotFoundError:
        err("ollama příkaz nenalezen")
    return False


def check_mic() -> bool:
    try:
        import speech_recognition as sr
        mics = sr.Microphone.list_microphone_names()
        if mics:
            ok(f"Mikrofon: {mics[0]}" if mics else "Mikrofon nenalezen")
            return bool(mics)
        warn("Žádný mikrofon nenalezen — hlasové ovládání nebude fungovat")
        return False
    except ImportError:
        warn("SpeechRecognition není nainstalován")
        return False
    except Exception as e:
        warn(f"Mikrofon: {e}")
        return False


def list_tts_voices() -> list[str]:
    try:
        result = subprocess.run(
            ["python3", "-c",
             "import asyncio, edge_tts; "
             "voices = asyncio.run(edge_tts.list_voices()); "
             "cs = [v['ShortName'] for v in voices if v['Locale'].startswith('cs')]; "
             "print('\\n'.join(cs[:6]))"],
            capture_output=True, text=True, timeout=10,
        )
        return [v.strip() for v in result.stdout.strip().splitlines() if v.strip()]
    except Exception:
        return ["cs-CZ-AntoninNeural", "cs-CZ-VlastaNeural"]


# ── Konfigurace ───────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"Konfigurace uložena → {CONFIG_PATH}")


# ── Průvodce ──────────────────────────────────────────────────────

def run():
    print(f"\n{BOLD}{'='*50}")
    print("  E.V. — Průvodce prvního spuštění")
    print(f"{'='*50}{NC}")
    print("  Zkontrolujeme závislosti a nastavíme E.V..")
    print("  Stiskni Enter pro přeskočení nebo zadej hodnotu.\n")

    issues = []

    # ── Krok 1: Systémové závislosti ──────────────
    hdr("Krok 1/4 — Systémové závislosti")
    if not check_python():
        issues.append("Python 3.11+")
    check_ffmpeg()

    # ── Krok 2: Ollama + model ────────────────────
    hdr("Krok 2/4 — Ollama (LLM engine)")
    ollama_ok, detected_model = check_ollama()

    cfg = load_config()
    current_model = cfg.get("ollama_model", "qwen2.5:3b")

    models_available = [
        ("qwen2.5:3b",            "~3 GB  — výchozí, rychlý, česky dobře"),
        ("llama3.1:8b",           "~8 GB  — lepší kvalita, pomalejší"),
        ("qwen2.5-coder:1.5b-base", "~2 GB  — specializovaný na kód"),
        ("llava:7b",              "~8 GB  — vision (popis obrazovky, webcam)"),
    ]

    if ollama_ok:
        print("\n  Dostupné modely:")
        for i, (name, desc) in enumerate(models_available, 1):
            marker = " ◀ aktuální" if name == current_model else ""
            print(f"    {i}. {name:<32} {desc}{marker}")
        choice = ask("Vyber model (1–4 nebo Enter pro ponechání)", "")
        if choice.isdigit() and 1 <= int(choice) <= len(models_available):
            chosen_model = models_available[int(choice) - 1][0]
            if chosen_model != detected_model:
                pull_model(chosen_model)
            cfg["ollama_model"] = chosen_model
        elif detected_model:
            cfg["ollama_model"] = detected_model

    # ── Krok 3: Mikrofon + TTS ────────────────────
    hdr("Krok 3/4 — Hlas (STT + TTS)")
    check_mic()

    print("\n  Dostupné jazyky STT:")
    langs = [("cs-CZ", "Čeština"), ("en-US", "Angličtina"), ("sk-SK", "Slovenština")]
    for i, (code, name) in enumerate(langs, 1):
        marker = " ◀ aktuální" if code == cfg.get("stt_language", "cs-CZ") else ""
        print(f"    {i}. {code}  — {name}{marker}")
    lang_choice = ask("Jazyk STT (1–3)", "1")
    if lang_choice.isdigit() and 1 <= int(lang_choice) <= len(langs):
        cfg["stt_language"] = langs[int(lang_choice) - 1][0]

    print("\n  Načítám dostupné TTS hlasy...")
    voices = list_tts_voices()
    if voices:
        for i, v in enumerate(voices, 1):
            marker = " ◀ aktuální" if v == cfg.get("tts_voice") else ""
            print(f"    {i}. {v}{marker}")
        v_choice = ask(f"Hlas TTS (1–{len(voices)})", "1")
        if v_choice.isdigit() and 1 <= int(v_choice) <= len(voices):
            cfg["tts_voice"] = voices[int(v_choice) - 1]

    rate = ask("Rychlost TTS (120–220, výchozí 170)", str(cfg.get("tts_rate", 170)))
    try:
        cfg["tts_rate"] = max(120, min(220, int(rate)))
    except ValueError:
        pass

    # ── Krok 4: Wake word ─────────────────────────
    hdr("Krok 4/4 — Wake word")
    current_ww = cfg.get("wake_word", "jarvis")
    print(f"  Aktuální wake word: '{current_ww}'")
    print("  E.V. se probudí když řekneš toto slovo.")
    ww = ask("Wake word", current_ww)
    cfg["wake_word"] = ww.lower().strip() or "jarvis"
    cfg["wake_word_enabled"] = ask("Zapnout wake word? (ano/ne)", "ano").lower() in ("ano", "a", "yes", "y", "1")

    # ── Uložení ───────────────────────────────────
    hdr("Ukládám konfiguraci")
    save_config(cfg)

    # ── Souhrn ────────────────────────────────────
    print(f"\n{BOLD}{'='*50}")
    print("  Nastavení dokončeno!")
    print(f"{'='*50}{NC}")
    if issues:
        print(f"\n  {YELLOW}Nevyřešené problémy:{NC}")
        for issue in issues:
            print(f"    - {issue}")
    print(f"""
  Spuštění E.V.:
    {CYAN}source venv/bin/activate && python jarvis.py{NC}

  Web dashboard:
    {CYAN}python dashboard.py{NC}   → localhost:8002

  Dokumentace:
    README.md nebo https://github.com/simivilasek-ship-it/Jarvis
""")

    start = ask("Spustit E.V. teď? (ano/ne)", "ano")
    if start.lower() in ("ano", "a", "yes", "y", "1"):
        print(f"\n  {GREEN}Spouštím E.V....{NC}\n")
        os.execv(sys.executable, [sys.executable, "jarvis.py"])


if __name__ == "__main__":
    run()
