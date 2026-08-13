"""
E.V. Demo Script
==================
Spusť tenhle script před natáčením dema.
Připraví prostředí, ověří že vše běží a vytvoří demo soubory.

Použití:
    python3 demo.py

Pak spusť E.V. a zadej příkaz:
    "Open Chrome, research the best Python async libraries,
     summarize findings, and save a note."
"""
import os
import subprocess
import sys
import time
from pathlib import Path

SEP = "─" * 60


def check(label: str, fn) -> bool:
    try:
        result = fn()
        print(f"  ✓  {label}" + (f" — {result}" if result else ""))
        return True
    except Exception as e:
        print(f"  ✗  {label}: {e}")
        return False


def main():
    print(f"\n{SEP}")
    print("  E.V. Demo — kontrola prostředí")
    print(f"{SEP}\n")

    ok = True

    # 1. Ollama běží?
    ok &= check("Ollama", lambda: (
        __import__("requests").get("http://localhost:11434/api/tags", timeout=3)
        .raise_for_status() or "online"
    ))

    # 2. E.V. backend běží?
    ok &= check("E.V. backend :8002", lambda: (
        __import__("requests").get("http://localhost:8002/health", timeout=3)
        .raise_for_status() or "online"
    ))

    # 3. Groq API klíč?
    groq_key = os.environ.get("GROQ_API_KEY") or ""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        groq_key = os.environ.get("GROQ_API_KEY") or ""
    except ImportError:
        pass
    check("Groq API key", lambda: "nastaven ✓" if groq_key else (_ for _ in ()).throw(Exception("chybí — přidej do .env")))

    # 4. pyautogui pro Computer Use?
    check("pyautogui (Computer Use)", lambda: __import__("pyautogui") and "ok")

    # 5. Vytvoř demo složku
    notes = Path.home() / "notes"
    notes.mkdir(exist_ok=True)
    check("~/notes/ adresář", lambda: str(notes))

    print()
    if not ok:
        print("  ⚠  Některé kontroly selhaly. Oprav je před natáčením.\n")
    else:
        print("  ✅  Vše připraveno!\n")

    print(f"{SEP}")
    print("  DEMO SCRIPT — zadej tento příkaz do JARVISe:")
    print(f"{SEP}")
    print("""
  "Open Chrome, research the best Python async libraries,
   summarize the top 3, and save a note to my notes folder."
""")
    print("  Co E.V. udělá (~30 sekund):")
    print("""
  0.3s  → Otevře Chrome
  2.0s  → Vyhledá "best Python async libraries 2025"
  4.0s  → Přečte top výsledky (Trio, AnyIO, asyncio)
  5.0s  → Shrne přes Groq LLaMA 3.3 (~200ms)
  5.5s  → Uloží ~/notes/async-libs.md
  6.0s  → "Done. Saved to ~/notes/async-libs.md"
""")
    print(f"{SEP}")
    print("  TIPY PRO NATÁČENÍ:")
    print("""
  • Rozlišení: 1920×1080, tmavý režim
  • Okno: E.V. dashboard na levé straně, Chrome na pravé
  • OBS: zapni "Highlight mouse clicks"
  • Délka: 30–60 sekund, žádný střih — jeden záběr
  • Thumbnail: "E.V. controls Chrome" + GIF z Computer Use
""")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
