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

# Core moduly — nutné ihned
from async_utils import get_async_engine, shutdown_async_engine, TaskPriority
from error_handling import get_error_handler, ErrorSeverity, ErrorCategory
from event_bus import EventType, Event, get_event_bus

# Těžké moduly — importují se lazy (zrychlení startu o ~2-4s)
# from plugin_system import create_plugin_manager   → lazy v _load_plugins
# from agents import AgentManager                   → lazy v _init_new_systems
# from scheduler import get_scheduler               → lazy v _init_new_systems
# from security_v2 import get_security_manager, confirm_action → lazy v _init_new_systems
# from wake_word_detector import WakeWordDetector   → lazy v _init_new_systems
# from user_profile import get_user_profile         → lazy v _schedule_memory_maintenance
# from mcp_bridge import get_mcp_bridge, HAS_MCP   → lazy v _init_mcp

logger = logging.getLogger(__name__)


class JarvisApp:
    """Orchestrátor — propojuje GUI s backend moduly."""

    def __init__(self):
        setup_logging()
        logger.info("Spouštím JARVIS v4.2...")

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

        # Načti pluginy a navař callbacks
        self._load_plugins()
        self._wire_skill_callbacks()
        self._init_mcp()

        # Routing pipeline (vyčleněno do routing.py)
        from routing import CommandRouter
        self._router = CommandRouter(self)

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

        self.gui._clear_mem = self._clear_memory

        self.gui.root.after(800, self._check_ollama)
        self._schedule_memory_maintenance()
        logger.info("JARVIS připraven.")

    def _init_new_systems(self):
        """Inicializuje všechny systémy."""
        from agents import AgentManager
        from scheduler import get_scheduler
        from security_v2 import get_security_manager
        from wake_word_detector import WakeWordDetector

        # Error handler
        self.error_handler = get_error_handler()
        self.error_handler.on_error    = self._on_error
        self.error_handler.on_recovery = self._on_recovery

        # Async engine
        self.async_engine = get_async_engine()
        self.async_engine.on_task_complete = self._on_task_complete
        self.async_engine.on_task_error    = self._on_task_error

        # ── Event Bus ────────────────────────────────
        self.bus = get_event_bus()
        self.bus.subscribe(EventType.AGENT_ALERT,  self._on_agent_alert)
        self.bus.subscribe(EventType.CPU_HIGH,      self._on_agent_alert)
        self.bus.subscribe(EventType.RAM_HIGH,      self._on_agent_alert)
        self.bus.subscribe(EventType.DISK_LOW,      self._on_agent_alert)
        self.bus.subscribe(EventType.TASK_FIRED,    self._on_task_fired)

        # ── Background Agents ────────────────────────
        self.agent_manager = AgentManager.create_default(self.bus)
        self.agent_manager.start_all()

        # ── Scheduler ────────────────────────────────
        self.scheduler = get_scheduler()

        # ── Security Manager ─────────────────────────
        self.security = get_security_manager()

        # ── Wake Word ─────────────────────────────────
        self.wake_word = WakeWordDetector(
            wake_word=CONFIG.get("wake_word", "jarvis"),
            on_wake=self._on_wake_word,
        )
        if CONFIG.get("wake_word_enabled", True):
            self.wake_word.start()

        logger.info("Systémy v2.0 inicializovány (EventBus, Agents, Scheduler, Security, WakeWord)")

    def _load_plugins(self):
        """Načte plugin systém a pluginy"""
        try:
            from plugin_system import create_plugin_manager
            self.plugin_manager = create_plugin_manager(CONFIG)
            loaded = self.plugin_manager.load_all_plugins()
            logger.info(f"Načteno {len(loaded)} pluginů")
        except Exception as e:
            logger.warning(f"Plugin systém selhal: {e}")
            self.plugin_manager = None

    def _init_mcp(self):
        """Inicializuje MCP bridge a předá ho skill modulům."""
        from mcp_bridge import get_mcp_bridge, HAS_MCP
        if not HAS_MCP:
            logger.info("MCP bridge: mcp balíček není nainstalován, přeskočeno")
            return
        try:
            self.mcp = get_mcp_bridge(CONFIG)
            # Předej bridge skill modulům přes sys.modules (jsou již načteny)
            import sys as _sys
            for mod_name in ("jarvis_skill_mcp_filesystem", "jarvis_skill_mcp_brave"):
                mod = _sys.modules.get(mod_name)
                if mod and hasattr(mod, "_bridge"):
                    mod._bridge = self.mcp
            logger.info(f"MCP bridge inicializován: {self.mcp.get_server_names()}")
        except Exception as e:
            logger.warning(f"MCP bridge init selhal: {e}")
        self._init_agents()

    def _init_agents(self):
        """Inicializuje ReAct agenta a grafového agenta."""
        url   = CONFIG.get("ollama_url",   "http://localhost:11434/api/chat")
        model = CONFIG.get("ollama_model", "qwen2.5:3b")
        mcp   = getattr(self, "mcp", None)

        try:
            from agent_react import get_react_agent
            self.react_agent = get_react_agent(
                executor=self.cmds, mcp_bridge=mcp,
                ollama_url=url, model=model)
            logger.info("ReactAgent připraven")
        except Exception as e:
            self.react_agent = None
            logger.warning(f"ReactAgent init selhal: {e}")

        try:
            from agent_graph import get_graph_agent
            self.graph_agent = get_graph_agent(
                executor=self.cmds, mcp_bridge=mcp,
                ollama_url=url, model=model)
            logger.info("GraphAgent připraven")
        except Exception as e:
            self.graph_agent = None
            logger.warning(f"GraphAgent init selhal: {e}")

    def _wire_skill_callbacks(self):
        """Naváže callbacks do skill modulů po jejich načtení."""
        import sys as _sys
        # Timer skill — callback pro hlasové upozornění při vypršení
        timer_mod = _sys.modules.get("jarvis_skill_timer")
        if timer_mod and hasattr(timer_mod, "_on_timer_done"):
            def _timer_done(msg: str):
                self._gui(lambda m=msg: self.gui.add_message(m, "jarvis"))
                self._speak(msg)
            timer_mod._on_timer_done = _timer_done
            logger.info("Timer skill callback navázan")

    def _clear_memory(self):
        """Vymaže LLM historii s error handlingem."""
        try:
            self.llm.clear_history()
            self._gui(lambda: self.gui._add_sys("Paměť vymazána."))
        except Exception as e:
            msg = str(e)
            logger.error(f"Chyba při mazání paměti: {msg}")
            self._gui(lambda: self.gui._add_sys(f"Chyba při mazání paměti: {msg}"))

    # ── ERROR HANDLING CALLBACKS ─────────────────────

    def _on_error(self, error_record):
        """Callback pro error handler — aktualizuje status bar, pro CRITICAL zobrazí dialog."""
        try:
            self._gui(lambda: self.gui.set_status(
                f"⚠ {error_record.message[:60]}"))
            if error_record.severity == ErrorSeverity.CRITICAL:
                self._gui(lambda: self._show_error_dialog(error_record))
        except Exception:
            pass

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

    # ── v2.0: Agent & Scheduler callbacks ────────────

    def _on_agent_alert(self, event: Event):
        """Zobrazí alert od background agenta v GUI."""
        data = event.data or {}
        msg  = data.get("message", str(data))
        logger.warning(f"[Agent] {msg}")
        self._gui(lambda m=msg: self.gui.add_message(f"⚠ {m}", "jarvis"))
        self._gui(lambda m=msg: self.gui.set_status(f"⚠ {m[:50]}"))

    def _on_task_fired(self, event: Event):
        """Notifikace při spuštění naplánované úlohy."""
        data = event.data or {}
        name = data.get("name", "?")
        self._gui(lambda n=name: self.gui.set_status(f"⏰ {n}"))

    def _on_wake_word(self):
        """Wake word detekován — spustí naslouchání jako klik na mikrofon."""
        logger.info("Wake word detekován, spouštím naslouchání")
        self._gui(lambda: self.gui.set_status("Wake word detekován..."))
        self._on_mic_click()

    def _on_mic_click(self):
        if not self.stt.is_available():
            self._gui(lambda: self.gui.add_message("Mikrofon není k dispozici.", "jarvis"))
            return
        self.tts.stop()  # Přeruš mluvení, nový příkaz přichází
        self.async_engine.run_sync(
            self._listen_and_process,
            priority=TaskPriority.HIGH,
            task_name="mic_listen",
        )

    def _on_send(self, text: str):
        self.tts.stop()  # Přeruš mluvení, nový příkaz přichází
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

        # Pozastav wake word — uvolni mikrofon pro STT
        try:
            self.wake_word.pause()
        except Exception:
            pass

        result = self.error_handler.execute_with_fallback(
            "stt_listen",
            self.stt.listen,
        )
        text = result.result if result.success else None

        # Obnov wake word detektor
        try:
            self.wake_word.resume()
        except Exception:
            pass

        self._gui(lambda: self.gui.set_state("idle"))
        self._gui(lambda: self.gui.set_status(""))

        if text:
            self._process_command(text)
        else:
            self._gui(lambda: self.gui.set_status("Nerozuměl jsem."))

    def _process_command(self, text: str):
        """Deleguje na CommandRouter (routing.py)."""
        logger.info(f"Příkaz: {text}")
        self._router.process(text)

    # Zpětná kompatibilita — delegace na router
    def _try_fast_path(self, text: str) -> bool:
        return self._router._fast_path(text)

    def _run_llm_path(self, text: str):
        self._router._llm_path(text)

    def _try_plugin_routes(self, text: str) -> Optional[Tuple[str, dict]]:
        return self._router._plugin_routes(text)

    def _execute_result(self, message: str, action_data: dict, speak: bool = True):
        """Zobrazí odpověď a vykoná akci. speak=False přeskočí TTS (pokud bylo mluveno při streamování)."""
        action = action_data.get("action", "answer")
        params = action_data.get("params", {})

        # Security 2.0 — audit log + permission check
        allowed, reason = self.security.check(action, params)
        if not allowed:
            logger.warning(f"Security: {action} zamítnuto — {reason}")
            self._gui(lambda r=reason: self.gui.add_message(
                f"Akce zamítnuta: {r}", "jarvis"))
            return

        # Potvrzení pro nebezpečné akce
        if self.security.needs_confirmation(action):
            from security_v2 import confirm_action
            confirmed = confirm_action(action, params, parent=self.gui.root)
            if not confirmed:
                self._gui(lambda: self.gui.add_message("Akce zrušena.", "jarvis"))
                return

        # Publikuj event o vykonání akce
        self.bus.emit(EventType.CMD_EXECUTE, {"action": action, "params": params},
                      source="execute_result")

        if not message and action not in ("answer", ""):
            message = self.llm._default_message(action, str(params))

        if message:
            self._gui(lambda m=message: self.gui.add_message(m, "jarvis"))
            if speak:
                self._speak(message)

        if action not in ("answer", ""):
            logger.info(f"Akce: {action} {params}")
            try:
                # Zkus plugin akci (nové)
                if self.plugin_manager:
                    plugin_action = self.plugin_manager.get_action(action)
                    if plugin_action:
                        result, err = self.plugin_manager.call_action(
                            plugin_action, plugin_name=action, **params)
                        if err:
                            logger.warning(f"Plugin akce '{action}' selhala: {err}")
                        elif result and result != "ok":
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
                err_msg = str(e)
                self._gui(lambda: self.gui.set_status(f"Chyba: {err_msg}"))

    def _gui(self, fn):
        try:
            self.gui.root.after(0, fn)
        except Exception:
            pass

    def _speak(self, text: str):
        has_code = any(k in text for k in ("```", "def ", "import ", "class "))
        if not has_code and len(text) < 400:
            self._gui(lambda: self.gui.set_state("speaking"))
            self.tts.speak(text)  # neblokující — přidá do fronty workeru

    def _ollama_reachable(self) -> bool:
        """Rychlá kontrola dostupnosti Ollama (cachováno na 15s)."""
        import time as _time
        now = _time.time()
        if now - getattr(self, "_ollama_check_ts", 0) < 15:
            return getattr(self, "_ollama_ok", True)
        try:
            import requests as _req
            r = _req.get(
                self.llm.url.replace("/api/chat", "/api/tags"),
                timeout=2,
            )
            self._ollama_ok = r.status_code == 200
        except Exception:
            self._ollama_ok = False
        self._ollama_check_ts = now
        return self._ollama_ok

    def _schedule_memory_maintenance(self):
        """Naplánuje auto-maintenance paměti a denní shrnutí."""
        try:
            from memory import JarvisMemory, DailySummarizer
            mem = JarvisMemory(CONFIG)
            self.scheduler.every(6 * 3600, mem.run_maintenance,
                                 name="memory_maintenance")

            # UserProfile — načti a vlož souhrn do LLM systémového promptu
            from user_profile import get_user_profile
            self.user_profile = get_user_profile()
            profile_summary = self.user_profile.summary()
            if profile_summary:
                self.llm.inject_profile(profile_summary)

            # DailySummarizer — spusť dnes pokud ještě neproběhl, naplánuj půlnoc
            summarizer = DailySummarizer(CONFIG, mem)
            if summarizer.should_run():
                import threading as _t
                _t.Thread(target=summarizer.run, daemon=True).start()
            summarizer.schedule_midnight(self.scheduler)

            logger.info("Memory maintenance + DailySummarizer naplánováno")
        except Exception as e:
            logger.debug(f"Memory setup skip: {e}")

    def _check_ollama(self):
        def _chk():
            import requests as _req
            try:
                r = _req.get(self.llm.url.replace("/api/chat", "/api/tags"), timeout=4)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    current = CONFIG["ollama_model"]
                    # Aktualizuj dropdown v GUI
                    if models:
                        self._gui(lambda ml=models, c=current:
                                  self.gui.update_model_list(ml, c))
                    self._gui(lambda: self.gui.add_message(
                        f"Připojen [{CONFIG['ollama_model']}]. Jak ti mohu pomoci?", "jarvis"))
                    self._gui(lambda: self.gui.set_status(f"● {CONFIG['ollama_model']}"))
                else:
                    raise ConnectionError()
            except Exception:
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

        # Zastav TTS worker
        try:
            self.tts.shutdown()
        except Exception:
            pass

        # Zastav wake word
        try:
            self.wake_word.stop()
        except Exception:
            pass

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
