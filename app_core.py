"""JARVIS core orchestrator and lifecycle management."""

import logging
import signal
import threading
import re
import sys

from config import CONFIG, save_config
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor
from gui import JarvisGUI
from logging_setup import setup_logging
from security import is_action_allowed, requires_confirmation, confirm_action

logger = logging.getLogger(__name__)


class JarvisApp:
    """Orchestrátor — propojuje GUI s backend moduly."""

    def __init__(self):
        setup_logging()
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
        self.gui.on_language_change = self._on_language_change
        self.gui.on_energy_threshold_change = self._on_energy_threshold_change
        self.gui.on_tts_rate_change = self._on_tts_rate_change

        signal.signal(signal.SIGINT,  self._sig)
        signal.signal(signal.SIGTERM, self._sig)

        self.gui._clear_mem = lambda: (
            self.llm.clear_history(),
            self.gui._add_sys("Paměť vymazána.")
        )

        self.gui.root.after(800, self._check_ollama)
        logger.info("JARVIS připraven.")

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

    def _on_language_change(self, language: str):
        """Změní jazyk rozpoznávání řeči."""
        if self.stt.set_language(language):
            CONFIG["stt_language"] = language
            try:
                save_config(CONFIG)
            except Exception:
                pass
            lang_name = CONFIG.get("available_languages", {}).get(language, language)
            self._gui(lambda l=lang_name: self.gui.add_message(f"Jazyk STT: {l}", "jarvis"))
        else:
            self._gui(lambda: self.gui.add_message("Jazyk není dostupný.", "jarvis"))

    def _on_energy_threshold_change(self, energy: int):
        """Změní energetický práh mikrofonu."""
        CONFIG["stt_energy_threshold"] = energy
        self.stt.recognizer.energy_threshold = energy
        try:
            save_config(CONFIG)
        except Exception:
            pass
        logger.info(f"Energetický práh: {energy}")

    def _on_tts_rate_change(self, rate: int):
        """Změní rychlost TTS."""
        CONFIG["tts_rate"] = rate
        self.tts.rate = rate
        try:
            save_config(CONFIG)
        except Exception:
            pass
        self._gui(lambda r=rate: self.gui.add_message(f"TTS rychlost: {r}", "jarvis"))

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

    def _process_command(self, text: str):
        logger.info(f"Příkaz: {text}")
        self._gui(lambda: self.gui.add_message(text, "user"))
        self._gui(lambda: self.gui.set_state("thinking"))
        self._gui(lambda: self.gui.set_status("Zpracovávám..."))

        try:
            msg, action_data = self.llm._quick_match(text)
            if action_data is not None:
                self._execute_result(msg, action_data)
                return

            full_response = ""
            sentence_buf  = ""
            is_command    = False

            for chunk in self.llm.stream_ask(text):
                full_response += chunk

                if "COMMAND:" in full_response:
                    is_command = True
                    break

                sentence_buf += chunk
                while True:
                    m = re.search(r"[.!?][\s\n]", sentence_buf)
                    if not m:
                        break
                    sentence = sentence_buf[: m.end()].strip()
                    sentence_buf = sentence_buf[m.end():]
                    if sentence:
                        self._speak(sentence)

            if is_command:
                for chunk in self.llm.drain_stream():
                    full_response += chunk

            if sentence_buf.strip():
                self._speak(sentence_buf.strip())

            full_text = full_response.strip()
            if full_text:
                self._execute_result(full_text, {"action": "answer", "params": {}})

        except Exception as e:
            logger.error(f"Chyba: {e}", exc_info=True)
            self._gui(lambda: self.gui.add_message("Chyba. Zkus to znovu.", "jarvis"))
        finally:
            self._gui(lambda: self.gui.set_state("idle"))
            self._gui(lambda: self.gui.set_status(""))

    def _execute_result(self, message: str, action_data: dict):
        action = action_data.get("action", "answer")
        params = action_data.get("params", {})

        if not is_action_allowed(action):
            logger.warning(f"Akce není povolena: {action}")
            self._gui(lambda: self.gui.add_message("Tato akce není povolena.", "jarvis"))
            return

        if requires_confirmation(action, params):
            confirmed = confirm_action(action, params, parent=self.gui.root)
            if not confirmed:
                self._gui(lambda: self.gui.add_message("Akce zrušena uživatelem.", "jarvis"))
                return

        if not message and action not in ("answer", ""):
            message = self.llm._default_message(action, str(params))

        if message:
            self._gui(lambda m=message: self.gui.add_message(m, "jarvis"))
            self._speak(message)

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

    def _gui(self, fn):
        try:
            self.gui.root.after(0, fn)
        except Exception:
            pass

    def _speak(self, text: str):
        has_code = any(k in text for k in ("```", "def ", "import ", "class "))
        if not has_code and len(text) < 400:
            self._gui(lambda: self.gui.set_state("speaking"))
            self.tts.speak(text)

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
