"""JARVIS core orchestrator and lifecycle management.
Integrates plugin system, async operations, and robust error handling."""

import logging
import signal
import threading
import re
import sys
from typing import Optional, Tuple

from config import CONFIG, save_config
from stt import STTEngine
from tts import TTSEngine
from llm import LLMEngine
from commands import CommandExecutor
from gui import JarvisGUI
from logging_setup import setup_logging
from security import is_action_allowed, requires_confirmation, confirm_action

# Nové moduly
from async_utils import AsyncEngine, get_async_engine, shutdown_async_engine, TaskPriority
from error_handling import ErrorHandler, get_error_handler, ErrorSeverity, ErrorCategory
from plugin_system import PluginManager, create_plugin_manager

logger = logging.getLogger(__name__)


class JarvisApp:
    """Orchestrátor — propojuje GUI s backend moduly."""

    def __init__(self):
        setup_logging()
        logger.info("Spouštím JARVIS v3.0...")

        # Inicializace nových systémů (async, error handling, plugins)
        self._init_new_systems()

        # Backend moduly
        try:
            self.stt  = STTEngine(CONFIG)
            self.tts  = TTSEngine(CONFIG)
            self.llm  = LLMEngine(CONFIG)
            self.cmds = CommandExecutor(CONFIG)
        except Exception as e:
            logger.error(f"Chyba inicializace: {e}")
            self.error_handler.log_error(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                source="JarvisApp.__init__",
                message=f"Inicializace backendu selhala: {e}",
                exception=e,
            )
            sys.exit(1)

        # Načti pluginy
        self._load_plugins()

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

    def _init_new_systems(self):
        """Inicializuje nové systémy (async, error handling, plugins)"""
        # Error handler
        self.error_handler = get_error_handler()
        self.error_handler.on_error = self._on_error
        self.error_handler.on_recovery = self._on_recovery

        # Async engine
        self.async_engine = get_async_engine()
        self.async_engine.on_task_complete = self._on_task_complete
        self.async_engine.on_task_error = self._on_task_error

        logger.info("Nové systémy inicializovány")

    def _load_plugins(self):
        """Načte plugin systém a pluginy"""
        try:
            self.plugin_manager = create_plugin_manager(CONFIG)
            loaded = self.plugin_manager.load_all_plugins()
            logger.info(f"Načteno {len(loaded)} pluginů")
        except Exception as e:
            logger.warning(f"Plugin systém selhal: {e}")
            self.plugin_manager = None

    # ── ERROR HANDLING CALLBACKS ─────────────────────

    def _on_error(self, error_record):
        """Callback pro error handler - zobrazí chybu v GUI"""
        severity_map = {
            ErrorSeverity.DEBUG: "DEBUG",
            ErrorSeverity.INFO: "INFO",
            ErrorSeverity.WARNING: "VAROVÁNÍ",
            ErrorSeverity.ERROR: "CHYBA",
            ErrorSeverity.CRITICAL: "KRITICKÁ CHYBA"
        }

        severity_str = severity_map.get(error_record.severity, "NEZNÁMÁ")
        message = f"[{severity_str}] {error_record.category.value}: {error_record.message}"

        # Zobraz v GUI
        self._gui(lambda: self.gui.add_message(message, "jarvis"))

        # Pro kritické chyby zobraz dialog
        if error_record.severity == ErrorSeverity.CRITICAL:
            self._gui(lambda: self._show_error_dialog(error_record))

    def _on_recovery(self, error_record):
        """Callback pro úspěšnou recovery"""
        message = f"✅ Opraveno: {error_record.category.value}"
        self._gui(lambda: self.gui.add_message(message, "jarvis"))

    def _show_error_dialog(self, error_record):
        """Zobrazí dialog s detaily chyby"""
        import tkinter.messagebox as msgbox

        title = f"Chyba: {error_record.category.value}"
        message = f"{error_record.message}\n\n"
        message += f"Čas: {error_record.timestamp.strftime('%H:%M:%S')}\n"
        message += f"Zdroj: {error_record.source}\n"
        if error_record.recovery_action:
            message += f"Oprava: {error_record.recovery_action}"

        msgbox.showerror(title, message)

    # ── ASYNC CALLBACKS ──────────────────────────────

    def _on_task_complete(self, task_result):
        """Callback pro dokončenou asynchronní úlohu"""
        if task_result.success:
            logger.debug(f"Task {task_result.task_id} dokončen za {task_result.duration_ms:.1f}ms")
        else:
            logger.warning(f"Task {task_result.task_id} selhal: {task_result.error_message}")

    def _on_task_error(self, task_id, error):
        """Callback pro chybu v asynchronní úloze"""
        logger.error(f"Task {task_id} chyba: {error}")
        self.error_handler.log_error(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYSTEM,
            source=f"async_task_{task_id}",
            message=str(error),
            exception=error,
        )

    # ── GUI CALLBACKS ────────────────────────────────

    def _on_error(self, record):
        """Callback při chybě"""
        try:
            self._gui(lambda: self.gui.set_status(
                f"⚠ {record.message[:50]}..."
            ))
        except Exception:
            pass

    def _on_recovery(self, record):
        """Callback při úspěšné recovery"""
        try:
            self._gui(lambda: self.gui.set_status(
                f"✓ Obnoveno: {record.recovery_action[:50]}..."
            ))
        except Exception:
            pass

    def _on_task_complete(self, result):
        """Callback při dokončení úlohy"""
        if not result.success and result.error_message:
            logger.debug(f"Úloha {result.task_id} selhala: {result.error_message}")

    def _on_task_error(self, task_id, error):
        """Callback při chybě úlohy"""
        logger.debug(f"Chyba úlohy {task_id}: {error}")

    def _on_mic_click(self):
        if not self.stt.is_available():
            self._gui(lambda: self.gui.add_message("Mikrofon není k dispozici.", "jarvis"))
            return

        # Použij async engine místo raw thread
        self.async_engine.run_sync(
            self._listen_and_process,
            priority=TaskPriority.HIGH,
            task_name="mic_listen",
        )

    def _on_send(self, text: str):
        # Použij async engine místo raw thread
        self.async_engine.run_sync(
            self._process_command,
            text,
            priority=TaskPriority.NORMAL,
            task_name="process_command",
        )

    def _on_model_change(self, model: str):
        CONFIG["ollama_model"] = model
        self.llm.model = model
        try:
            save_config(CONFIG)
        except Exception as e:
            self.error_handler.log_error(
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.CONFIGURATION,
                source="_on_model_change",
                message=f"Uložení konfigurace selhalo: {e}",
                exception=e,
            )
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
        if hasattr(self.stt, 'recognizer') and self.stt.recognizer:
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

        # Použij error handler s fallbackem pro STT
        result = self.error_handler.execute_with_fallback(
            "stt_listen",
            self.stt.listen,
        )

        text = result.result if result.success else None

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
            # 1. Zkus plugin routes (nové)
            if self.plugin_manager:
                plugin_result = self._try_plugin_routes(text)
                if plugin_result:
                    msg, action_data = plugin_result
                    self._execute_result(msg, action_data)
                    return

            # 2. Zkus lokální router (LLM quick match)
            msg, action_data = self.llm._quick_match(text)
            if action_data is not None:
                self._execute_result(msg, action_data)
                return

            # 3. Pokud nic nesedí, použij LLM
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
            self.error_handler.log_error(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.SYSTEM,
                source="_process_command",
                message=f"Zpracování příkazu selhalo: {e}",
                exception=e,
            )
            self._gui(lambda: self.gui.add_message("Chyba. Zkus to znovu.", "jarvis"))
        finally:
            self._gui(lambda: self.gui.set_state("idle"))
            self._gui(lambda: self.gui.set_status(""))

    def _try_plugin_routes(self, text: str) -> Optional[Tuple[str, dict]]:
        """Zkusí routovat příkaz přes pluginy"""
        if not self.plugin_manager:
            return None

        for route in self.plugin_manager.get_routes():
            try:
                pattern = route.get("pattern")
                handler = route.get("handler")
                if pattern and handler and pattern.search(text):
                    result = handler(text)
                    if result and result[0] is not None:
                        return result
            except Exception as e:
                logger.debug(f"Plugin route selhala: {e}")
                continue

        return None

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
                # Zkus plugin akci (nové)
                if self.plugin_manager:
                    plugin_action = self.plugin_manager.get_action(action)
                    if plugin_action:
                        result = plugin_action(**params)
                        if result and result != "ok":
                            self._gui(lambda r=result: self.gui.set_status(f"↳ {r}"))
                            logger.info(f"Plugin výsledek: {result}")
                        return

                # Fallback na CommandExecutor
                result = self.cmds.execute(action, params)
                if result and result != "ok":
                    self._gui(lambda r=result: self.gui.set_status(f"↳ {r}"))
                    logger.info(f"Výsledek: {result}")
            except Exception as e:
                logger.error(f"Chyba akce {action}: {e}")
                self.error_handler.log_error(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.SYSTEM,
                    source=f"_execute_result.{action}",
                    message=f"Akce {action} selhala: {e}",
                    exception=e,
                )
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

            # Použij async engine pro TTS (nové)
            self.async_engine.run_sync(
                self.tts.speak,
                text,
                priority=TaskPriority.LOW,
                task_name="tts_speak",
            )

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
        logger.info("Ukončuji JARVIS...")

        # Zastav nové systémy
        try:
            shutdown_async_engine(timeout=3.0)
        except Exception as e:
            logger.warning(f"Chyba při zastavování async engine: {e}")

        # Zastav GUI
        self.gui.orb.stop()
        try:
            self.gui.root.quit()
            self.gui.root.destroy()
        except Exception:
            pass

        logger.info("JARVIS ukončen")

    def run(self):
        try:
            self.gui.run()
        except KeyboardInterrupt:
            self._shutdown()
        except Exception as e:
            logger.critical(f"Nezachytitelná chyba: {e}", exc_info=True)
            self.error_handler.log_error(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                source="JarvisApp.run",
                message=f"Nezachytitelná chyba: {e}",
                exception=e,
            )
            self._shutdown()
