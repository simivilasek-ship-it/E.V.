"""
JARVIS v3.0 — Desktop aplikace
Ovládá celý počítač hlasem nebo textem.
"""

import logging
import sys
import signal
import threading
import re

from config import CONFIG, save_config
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor
from gui import JarvisGUI

logger = logging.getLogger(__name__)


class JarvisApp:
    """Orchestrátor — propojuje GUI s backend moduly."""

    def __init__(self):
        self._setup_logging()
        logger.info("Spouštím JARVIS v3.0...")

        # Backend moduly
        try:
            self.stt  = STTEngine(CONFIG)
            self.tts  = TTSEngine(CONFIG)
            self.llm  = LLMEngine(CONFIG)
            self.cmds = CommandExecutor(CONFIG)
        except Exception as e:
            logger.error(f"Chyba inicializace: {e}")
            sys.exit(1)

        # GUI
        self.gui = JarvisGUI()
        self.gui.on_mic_click    = self._on_mic_click
        self.gui.on_send         = self._on_send
        self.gui.on_model_change = self._on_model_change

        signal.signal(signal.SIGINT,  self._sig)
        signal.signal(signal.SIGTERM, self._sig)

        self.gui.root.after(800, self._check_ollama)
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

    # ── GUI CALLBACKY ─────────────────────────────────

    def _on_mic_click(self):
        if not self.stt.is_available():
            self._gui(lambda: self.gui.add_message("Mikrofon není k dispozici.", "jarvis"))
            return
        threading.Thread(target=self._listen_and_process, daemon=True).start()

    def _on_send(self, text: str):
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    def _on_model_change(self, model: str):
        CONFIG["ollama_model"] = model
        self.llm.model = model
        try:
            save_config(CONFIG)
        except Exception:
            pass
        self._gui(lambda m=model: self.gui.add_message(f"Model: {m}", "jarvis"))

    # ── STT ───────────────────────────────────────────

    def _listen_and_process(self):
        self._gui(lambda: self.gui.set_state("listening"))
        self._gui(lambda: self.gui.set_status("Poslouchám..."))
        try:
            text = self.stt.listen()
        except Exception as e:
            logger.error(f"STT: {e}")
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
        1. Nejdřív zkusí lokální router (okamžitě, bez LLM)
        2. Pokud nerozpozná → pošle do Ollama
        """
        logger.info(f"Příkaz: {text}")
        self._gui(lambda: self.gui.add_message(text, "user"))
        self._gui(lambda: self.gui.set_state("thinking"))
        self._gui(lambda: self.gui.set_status("Zpracovávám..."))

        try:
            # ── 1. LOKÁLNÍ ROUTER (bez LLM) ──────────
            msg, action_data = self.llm._quick_match(text)
            if action_data is not None:
                self._execute_result(msg, action_data)
                return

            # ── 2. LLM (pro AI odpovědi / složité příkazy) ──
            full_response = ""
            sentence_buf  = ""
            is_command    = False

            for chunk in self.llm.stream_ask(text):
                full_response += chunk

                if "COMMAND:" in full_response:
                    is_command = True
                    break

                sentence_buf += chunk

                # Věty → okamžitě mluv
                while True:
                    m = re.search(r"[.!?][\s\n]", sentence_buf)
                    if not m:
                        break
                    sentence     = sentence_buf[: m.end()].strip()
                    sentence_buf = sentence_buf[m.end():]
                    if sentence:
                        self._speak(sentence)

            # Dočerpej stream
            if is_command:
                for chunk in self.llm.drain_stream():
                    full_response += chunk

            # Zbytek textu
            if sentence_buf.strip():
                self._speak(sentence_buf.strip())

            # Parsuj finální odpověď
            message, action_data = self.llm._parse_response(full_response)
            self._execute_result(message, action_data)

        except Exception as e:
            logger.error(f"Chyba: {e}", exc_info=True)
            self._gui(lambda: self.gui.add_message("Chyba. Zkus to znovu.", "jarvis"))
        finally:
            self._gui(lambda: self.gui.set_state("idle"))
            self._gui(lambda: self.gui.set_status(""))

    def _execute_result(self, message: str, action_data: dict):
        """Zobrazí odpověď a vykoná akci."""
        action = action_data.get("action", "answer")
        params = action_data.get("params", {})

        # Zpráva JARVIS
        if not message and action not in ("answer", ""):
            message = self.llm._default_message(action, str(params))

        if message:
            self._gui(lambda m=message: self.gui.add_message(m, "jarvis"))
            self._speak(message)

        # Vykonej příkaz
        if action not in ("answer", ""):
            logger.info(f"Akce: {action} {params}")
            try:
                result = self.cmds.execute(action, params)
                if result and result != "ok":
                    self._gui(lambda r=result: self.gui.set_status(f"↳ {r}"))
                    logger.info(f"Výsledek: {result}")
            except Exception as e:
                logger.error(f"Chyba akce {action}: {e}")
                self._gui(lambda: self.gui.set_status(f"Chyba: {e}"))

    # ── POMOCNÉ METODY ────────────────────────────────

    def _gui(self, fn):
        """Thread-safe spuštění v GUI vlákně."""
        try:
            self.gui.root.after(0, fn)
        except Exception:
            pass

    def _speak(self, text: str):
        """TTS — přeskočí kód a dlouhé texty."""
        has_code = any(k in text for k in ("```", "def ", "import ", "class "))
        if not has_code and len(text) < 400:
            self._gui(lambda: self.gui.set_state("speaking"))
            self.tts.speak(text)

    # ── OLLAMA CHECK ─────────────────────────────────

    def _check_ollama(self):
        def _chk():
            ok = self.llm.is_available()
            if ok:
                self._gui(lambda: self.gui.add_message(
                    f"Připojen [{CONFIG['ollama_model']}]. Jak ti mohu pomoci?", "jarvis"))
                self._gui(lambda: self.gui.set_status(f"● {CONFIG['ollama_model']}"))
            else:
                self._gui(lambda: self.gui.add_message(
                    "Ollama není dostupná. Spusť: ollama serve", "jarvis"))
        threading.Thread(target=_chk, daemon=True).start()

    # ── SHUTDOWN ─────────────────────────────────────

    def _sig(self, *_):
        self._shutdown()

    def _shutdown(self):
        self.gui.orb.stop()
        try:
            self.gui.root.quit()
            self.gui.root.destroy()
        except Exception:
            pass

    def run(self):
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
        handlers=[logging.StreamHandler(),
                  logging.FileHandler("jarvis.log", encoding="utf-8")],
    )


if __name__ == "__main__":
    _setup_logging()
    try:
        JarvisApp().run()
    except Exception as e:
        logging.error(f"Fatální chyba: {e}")
        sys.exit(1)
