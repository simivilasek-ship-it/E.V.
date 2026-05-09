"""
JARVIS v3.0 — Desktop aplikace
Orchestrátor: propojuje JarvisGUI (gui.py) se STT, TTS, LLM a Commands.
"""

import logging
import sys
import signal
import threading
import re

from config import CONFIG
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor
from gui import JarvisGUI

logger = logging.getLogger(__name__)
APP_VERSION = "3.0"


# ══════════════════════════════════════════════════════
#  APLIKACE
# ══════════════════════════════════════════════════════

class JarvisApp:
    """
    Hlavní třída desktop aplikace.
    Inicializuje GUI (JarvisGUI) a napojuje backend moduly.
    """

    def __init__(self):
        self._setup_logging()
        logger.info(f"Spouštím JARVIS v{APP_VERSION}...")

        # ── Backend moduly ────────────────────────────
        try:
            self.stt  = STTEngine(CONFIG)
            self.tts  = TTSEngine(CONFIG)
            self.llm  = LLMEngine(CONFIG)
            self.cmds = CommandExecutor(CONFIG)
        except Exception as e:
            logger.error(f"Chyba inicializace: {e}")
            sys.exit(1)

        # ── GUI ───────────────────────────────────────
        self.gui = JarvisGUI()
        self.gui.on_mic_click = self._on_mic_click
        self.gui.on_send      = self._on_send

        # ── Signály ───────────────────────────────────
        signal.signal(signal.SIGINT,  self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Zkontroluj Ollama po spuštění
        self.gui.root.after(600, self._check_ollama)
        logger.info("JARVIS připraven.")

    # ── LOGGING ──────────────────────────────────────

    def _setup_logging(self):
        level = getattr(logging, CONFIG.get("log_level", "INFO").upper())
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("jarvis.log", encoding="utf-8"),
            ],
        )

    # ── GUI → BACKEND CALLBACKY ───────────────────────

    def _on_mic_click(self):
        """Klik na mic tlačítko → spustí STT v jiném vlákně."""
        if not self.stt.is_available():
            self._gui(lambda: self.gui.add_message(
                "Mikrofon není k dispozici.", "jarvis"))
            return
        threading.Thread(target=self._listen_and_process, daemon=True).start()

    def _on_send(self, text: str):
        """Odeslání textového příkazu."""
        threading.Thread(
            target=self._process_command, args=(text,), daemon=True
        ).start()

    # ── STT ───────────────────────────────────────────

    def _listen_and_process(self):
        """Poslouchá mikrofon a zpracuje rozpoznaný text."""
        self._gui(lambda: self.gui.set_state("listening"))
        self._gui(lambda: self.gui.set_status("Poslouchám..."))

        try:
            text = self.stt.listen()
        except Exception as e:
            logger.error(f"STT chyba: {e}")
            text = None
        finally:
            self._gui(lambda: self.gui.set_state("idle"))
            self._gui(lambda: self.gui.set_status(""))

        if text:
            self._process_command(text)
        else:
            self._gui(lambda: self.gui.set_status("Nerozuměl jsem."))

    # ── ZPRACOVÁNÍ PŘÍKAZU ────────────────────────────

    def _process_command(self, text: str):
        """
        Zpracuje příkaz:
        1. Zobrazí zprávu uživatele v GUI
        2. Streamuje LLM → věty průběžně mluví přes TTS
        3. Detekuje COMMAND → vykoná akci
        4. Zobrazí finální odpověď JARVIS
        """
        logger.info(f"Příkaz: {text}")
        self._gui(lambda: self.gui.add_message(text, "user"))
        self._gui(lambda: self.gui.set_state("thinking"))
        self._gui(lambda: self.gui.set_status("Přemýšlím..."))

        full_response = ""
        sentence_buf  = ""
        is_command    = False

        try:
            # ── Streamování LLM ──────────────────────
            for chunk in self.llm.stream_ask(text):
                full_response += chunk

                if "COMMAND:" in full_response:
                    is_command = True
                    break

                sentence_buf += chunk

                # Hledej konce vět → okamžitě mluv
                while True:
                    m = re.search(r"[.!?][\s\n]", sentence_buf)
                    if not m:
                        break
                    sentence     = sentence_buf[: m.end()].strip()
                    sentence_buf = sentence_buf[m.end():]
                    if sentence:
                        self._speak(sentence)

            # Dočerpej stream pokud byl přerušen
            if is_command:
                for chunk in self.llm.drain_stream():
                    full_response += chunk

            # Zbytek sentence_buf
            if sentence_buf.strip():
                self._speak(sentence_buf.strip())

            # ── Parsuj finální odpověď ────────────────
            message, action_data = self.llm._parse_response(full_response)
            action = action_data.get("action", "answer")
            params = action_data.get("params", {})

            # Zobraz odpověď v GUI
            if is_command:
                display_msg = (action_data.get("message")
                               or self.llm._default_message(action, ""))
                if display_msg:
                    self._gui(lambda m=display_msg: self.gui.add_message(m, "jarvis"))
                    self._speak(display_msg)
            elif message:
                self._gui(lambda m=message: self.gui.add_message(m, "jarvis"))

            # ── Vykonej příkaz ────────────────────────
            if action not in ("answer", ""):

                result = self.cmds.execute(action, params)
                if result and result != "ok":
                    self._gui(lambda r=result: self.gui.set_status(f"↳ {r}"))

        except Exception as e:
            logger.error(f"Chyba zpracování: {e}", exc_info=True)
            self._gui(lambda: self.gui.add_message("Chyba. Zkus to znovu.", "jarvis"))
        finally:
            self._gui(lambda: self.gui.set_state("idle"))
            self._gui(lambda: self.gui.set_status(""))

    # ── POMOCNÉ METODY ────────────────────────────────

    def _gui(self, fn):
        """Thread-safe spuštění funkce v GUI vlákně."""
        try:
            self.gui.root.after(0, fn)
        except Exception:
            pass

    def _speak(self, text: str):
        """Promluví text přes TTS (přeskočí kódové bloky)."""
        has_code = any(k in text for k in ("```", "def ", "import ", "class "))
        if not has_code and len(text) < 400:
            self._gui(lambda: self.gui.set_state("speaking"))
            self.tts.speak(text)

    # ── OLLAMA CHECK ─────────────────────────────────

    def _check_ollama(self):
        def _check():
            if self.llm.is_available():
                self._gui(lambda: self.gui.set_status(
                    f"● Ollama [{CONFIG['ollama_model']}] OK"))
                self._gui(lambda: self.gui.add_message(
                    f"Ollama [{CONFIG['ollama_model']}] připojena.", "jarvis"))
            else:
                self._gui(lambda: self.gui.set_status("● Ollama offline"))
                self._gui(lambda: self.gui.add_message(
                    "Ollama není dostupná. Spusť: ollama serve", "jarvis"))
        threading.Thread(target=_check, daemon=True).start()

    # ── SHUTDOWN ─────────────────────────────────────

    def _signal_handler(self, signum, _frame):
        logger.info(f"Signál {signum}")
        self._shutdown()

    def _shutdown(self):
        logger.info("Ukončuji JARVIS...")
        self.gui.orb.stop()
        try:
            self.gui.root.quit()
            self.gui.root.destroy()
        except Exception:
            pass

    def run(self):
        """Spustí aplikaci."""
        try:
            self.gui.run()
        except KeyboardInterrupt:
            self._shutdown()


# ══════════════════════════════════════════════════════
#  SPUŠTĚNÍ
# ══════════════════════════════════════════════════════

def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("jarvis.log", encoding="utf-8"),
        ],
    )


if __name__ == "__main__":
    _setup_logging()
    try:
        app = JarvisApp()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatální chyba: {e}")
        sys.exit(1)
