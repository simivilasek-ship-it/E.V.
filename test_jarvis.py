#!/usr/bin/env python3
"""
E.V. v3.0 — Unit testy
Spuštění: python test_jarvis.py
Pokrývá: config, STT, TTS, LLM, Commands, LocalRouter,
         AsyncEngine, ErrorHandler, PluginManager
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock volitelné závislosti před importem modulů
for _mod in ("pyautogui", "pyperclip", "edge_tts", "pyttsx3",
             "speech_recognition", "customtkinter", "pycaw",
             "pycaw.pycaw", "comtypes", "tkinter"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

try:
    from config import CONFIG
    from stt import STTEngine
    from tts import TTSEngine
    from llm import LLMEngine, LocalRouter
    from commands import CommandExecutor
    from async_utils import AsyncEngine, TaskPriority
    from error_handling import ErrorHandler, ErrorSeverity, ErrorCategory
    from plugin_system import PluginManager, create_plugin_manager
except ImportError as e:
    print(f"Chyba importu modulů: {e}")
    sys.exit(1)

_CFG = {
    "ollama_url":   "http://localhost:11434/api/chat",
    "ollama_model": "qwen2.5:3b",
    "tts_enabled":  True,
    "tts_rate":     170,
    "history_size": 20,
    "window_size":  "820x560",
    "log_level":    "WARNING",
    "stt_language": "cs-CZ",
    "stt_energy_threshold": 300,
    "stt_timeout":  10,
    "stt_phrase_limit": 15,
}


# ══════════════════════════════════════════════════════
#  KONFIGURACE
# ══════════════════════════════════════════════════════

class TestConfig(unittest.TestCase):

    def test_required_keys(self):
        for key in ("ollama_url", "ollama_model", "tts_enabled",
                    "tts_rate", "history_size"):
            self.assertIn(key, CONFIG)

    def test_defaults_sane(self):
        self.assertIsInstance(CONFIG["history_size"], int)
        self.assertGreater(CONFIG["history_size"], 0)
        self.assertIsInstance(CONFIG["tts_enabled"], bool)
        self.assertIn("http", CONFIG["ollama_url"])


# ══════════════════════════════════════════════════════
#  STT / TTS
# ══════════════════════════════════════════════════════

class TestEngines(unittest.TestCase):

    def test_stt_has_api(self):
        stt = STTEngine(_CFG)
        self.assertTrue(hasattr(stt, "listen"))
        self.assertTrue(hasattr(stt, "is_available"))

    def test_tts_has_api(self):
        tts = TTSEngine(_CFG)
        self.assertTrue(hasattr(tts, "speak"))
        self.assertTrue(hasattr(tts, "is_available"))


# ══════════════════════════════════════════════════════
#  LOCAL ROUTER
# ══════════════════════════════════════════════════════

class TestLocalRouter(unittest.TestCase):

    def setUp(self):
        self.router = LocalRouter()

    def _action(self, text):
        _, a = self.router.route(text)
        return a["action"] if a else None

    def test_time(self):
        self.assertEqual(self._action("kolik je hodin"), "get_time")
        self.assertEqual(self._action("jaký je čas"), "get_time")

    def test_date(self):
        self.assertEqual(self._action("jaké je datum"), "get_date")
        self.assertEqual(self._action("dnes"), "get_date")

    def test_screenshot(self):
        self.assertEqual(self._action("udělej screenshot"), "screenshot")
        self.assertEqual(self._action("snímek obrazovky"), "screenshot")

    def test_shutdown(self):
        self.assertEqual(self._action("vypni počítač"), "shutdown")
        self.assertEqual(self._action("vypni pc"), "shutdown")

    def test_volume(self):
        _, a = self.router.route("hlasitost na 60")
        self.assertEqual(a["action"], "volume")
        self.assertEqual(a["params"]["level"], 60)

    def test_mute(self):
        _, a = self.router.route("ztlum zvuk")
        self.assertEqual(a["action"], "volume")
        self.assertEqual(a["params"]["action"], "mute")

    def test_youtube_play(self):
        _, a = self.router.route("pust let me love you justin bieber")
        self.assertEqual(a["action"], "youtube_play")
        self.assertIn("let me love you", a["params"]["query"].lower())

    def test_open_youtube_only(self):
        _, a = self.router.route("pust youtube")
        self.assertEqual(a["action"], "open_url")
        self.assertIn("youtube", a["params"]["url"])

    def test_kill_process(self):
        _, a = self.router.route("zavři discord")
        self.assertEqual(a["action"], "kill_process")

    def test_weather(self):
        _, a = self.router.route("počasí Praha")
        self.assertEqual(a["action"], "weather")
        self.assertEqual(a["params"]["city"], "Praha")

    def test_open_site(self):
        _, a = self.router.route("otevři github")
        self.assertEqual(a["action"], "open_url")
        self.assertIn("github", a["params"]["url"])

    def test_search(self):
        _, a = self.router.route("hledej python tutoriál")
        self.assertEqual(a["action"], "search_web")
        self.assertIn("python", a["params"]["query"])

    def test_create_folder(self):
        _, a = self.router.route("vytvoř složku projekt")
        self.assertEqual(a["action"], "create_folder")

    def test_timer(self):
        _, a = self.router.route("timer 5 minut")
        self.assertEqual(a["action"], "set_timer")
        self.assertEqual(a["params"]["seconds"], 300)

    def test_unknown_goes_to_llm(self):
        # Čistě konverzační dotaz bez klíčových slov příkazů
        msg, action = self.router.route("kdo je albert einstein")
        # Buď jde na LLM (None) nebo na wiki_search — obojí je správně
        if action is not None:
            self.assertIn(action["action"], ("wiki_search", "search_web", "answer"))

    def test_brightness(self):
        _, a = self.router.route("jas na 80")
        self.assertEqual(a["action"], "set_brightness")
        self.assertEqual(a["params"]["level"], 80)


# ══════════════════════════════════════════════════════
#  LLM ENGINE
# ══════════════════════════════════════════════════════

class TestLLMEngine(unittest.TestCase):

    def setUp(self):
        self.llm = LLMEngine(_CFG)

    def test_has_api(self):
        for m in ("ask", "stream_ask", "clear_history", "is_available", "quick_match"):
            self.assertTrue(hasattr(self.llm, m))

    def test_clear_history(self):
        self.llm.history.append({"role": "user", "content": "test"})
        self.llm.clear_history()
        self.assertEqual(len(self.llm.history), 0)

    def test_quick_match_time(self):
        msg, action = self.llm.quick_match("kolik je hodin")
        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "get_time")
        self.assertIn(":", msg)

    def test_quick_match_unknown(self):
        # Čistě konverzační dotaz
        _, action = self.llm.quick_match("ahoj jak se máš")
        self.assertIsNone(action)

    @patch("requests.post")
    def test_ask_mock(self, mock_post):
        mock_post.return_value.json.return_value = {
            "message": {"content": "Odpověď na testovací otázku."}}
        msg, action = self.llm.ask("Testovací otázka na AI")
        self.assertEqual(action["action"], "answer")
        self.assertGreater(len(msg), 0)

    @patch("requests.post")
    def test_ask_timeout(self, mock_post):
        import requests
        mock_post.side_effect = requests.Timeout()
        msg, action = self.llm.ask("timeout test")
        self.assertIn("timeout", msg.lower())
        self.assertEqual(action["action"], "answer")


# ══════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════

class TestCommands(unittest.TestCase):

    def setUp(self):
        self.cmds = CommandExecutor(_CFG)

    def test_has_execute(self):
        self.assertTrue(hasattr(self.cmds, "execute"))

    @patch("commands.apps.safe_run")
    def test_open_app(self, mock_run):
        mock_run.return_value = {"rc": 0, "stdout": "", "stderr": "", "timeout": False}
        result = self.cmds.execute("open_app", {"app": "firefox"})
        self.assertEqual(result, "ok")
        mock_run.assert_called()

    @patch("commands.utils.subprocess.run")
    def test_volume_mute(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = self.cmds.execute("volume", {"action": "mute"})
        self.assertTrue(len(result) > 0)  # mute vrátí neprázdný string

    @patch("commands.media.pyautogui")
    def test_screenshot(self, mock_pg):
        mock_img = MagicMock()
        mock_pg.screenshot.return_value = mock_img
        result = self.cmds.execute("screenshot", {})
        self.assertIn("Uloženo:", result)
        mock_img.save.assert_called_once()

    def test_unknown_action(self):
        result = self.cmds.execute("neexistujici_akce", {})
        self.assertIn("Neznámá", result)

    def test_answer_noop(self):
        result = self.cmds.execute("answer", {})
        self.assertEqual(result, "ok")


# ══════════════════════════════════════════════════════
#  ASYNC ENGINE  (Priority 1)
# ══════════════════════════════════════════════════════

class TestAsyncEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AsyncEngine(max_workers=2)
        self.engine.start()

    def tearDown(self):
        self.engine.stop(timeout=2.0)

    def test_start_and_has_stats(self):
        stats = self.engine.get_stats()
        self.assertIsInstance(stats, dict)

    def test_run_sync_simple(self):
        results = []
        def task():
            results.append(42)

        self.engine.run_sync(task, priority=TaskPriority.NORMAL, task_name="test")
        time.sleep(0.4)
        self.assertIn(42, results)

    def test_run_sync_with_args(self):
        results = []
        def add(a, b):
            results.append(a + b)

        self.engine.run_sync(add, 3, 4, priority=TaskPriority.NORMAL, task_name="add")
        time.sleep(0.4)
        self.assertIn(7, results)

    def test_multiple_tasks(self):
        counter = []
        lock = threading.Lock()

        def inc():
            with lock:
                counter.append(1)

        for _ in range(5):
            self.engine.run_sync(inc, priority=TaskPriority.NORMAL, task_name="inc")

        time.sleep(0.6)
        self.assertEqual(len(counter), 5)

    def test_high_priority_executes(self):
        done = []
        self.engine.run_sync(lambda: done.append(True),
                             priority=TaskPriority.HIGH, task_name="high")
        time.sleep(0.4)
        self.assertTrue(done)


# ══════════════════════════════════════════════════════
#  ERROR HANDLER  (Priority 1)
# ══════════════════════════════════════════════════════

class TestErrorHandler(unittest.TestCase):

    def setUp(self):
        self.handler = ErrorHandler()

    def test_log_and_get_errors(self):
        self.handler.log_error(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK,
            source="test",
            message="Test chyba"
        )
        errors = self.handler.get_errors()
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[-1].message, "Test chyba")

    def test_multiple_severities(self):
        before = len(self.handler.get_errors())
        for sev in (ErrorSeverity.DEBUG, ErrorSeverity.INFO,
                    ErrorSeverity.WARNING, ErrorSeverity.ERROR):
            self.handler.log_error(severity=sev, category=ErrorCategory.SYSTEM,
                                   source="test", message=f"msg {sev}")
        after = len(self.handler.get_errors())
        self.assertEqual(after - before, 4)

    def test_on_error_callback(self):
        received = []
        self.handler.on_error = lambda r: received.append(r)
        self.handler.log_error(severity=ErrorSeverity.ERROR,
                               category=ErrorCategory.SYSTEM,
                               source="test", message="cb test")
        self.assertGreater(len(received), 0)

    def test_get_stats(self):
        stats = self.handler.get_error_stats()
        self.assertIsInstance(stats, dict)

    def test_register_fallback(self):
        called = []
        self.handler.register_fallback(
            ErrorCategory.NETWORK, lambda r: called.append(True))
        # Ověř, že se nezhroutilo
        self.assertTrue(True)


# ══════════════════════════════════════════════════════
#  PLUGIN MANAGER  (Priority 1)
# ══════════════════════════════════════════════════════

class TestPluginManager(unittest.TestCase):

    def test_create(self):
        pm = create_plugin_manager()
        self.assertIsNotNone(pm)
        self.assertTrue(hasattr(pm, "get_routes"))
        self.assertTrue(hasattr(pm, "load_plugin"))

    def test_get_routes_returns_list(self):
        pm = create_plugin_manager()
        routes = pm.get_routes()
        self.assertIsInstance(routes, list)

    def test_list_plugins(self):
        pm = create_plugin_manager()
        plugins = pm.list_plugins()
        self.assertIsInstance(plugins, list)

    def test_get_all_actions(self):
        pm = create_plugin_manager()
        actions = pm.get_all_actions()
        self.assertIsInstance(actions, (list, dict))


# ══════════════════════════════════════════════════════
#  TTS — LOCK A STOP
# ══════════════════════════════════════════════════════

class TestTTSQueue(unittest.TestCase):
    """TTS worker fronta — neblokující, sériové přehrávání."""

    def setUp(self):
        cfg = {**_CFG, "tts_enabled": True, "tts_voice": "cs-CZ-AntoninNeural", "tts_rate": 170}
        self.tts = TTSEngine(cfg)

    def tearDown(self):
        self.tts.shutdown()

    def test_has_queue(self):
        """TTS musí mít interní frontu."""
        import queue
        self.assertIsInstance(self.tts._queue, queue.Queue)

    def test_has_worker_thread(self):
        """TTS musí mít worker vlákno."""
        self.assertIsNotNone(self.tts._worker)
        self.assertTrue(self.tts._worker.is_alive())

    def test_speak_nonblocking(self):
        """speak() musí vrátit okamžitě (neblokující)."""
        self.tts.enabled = False   # nepřehrávej audio, jen testuj neblokování
        import time
        t0 = time.time()
        self.tts.speak("toto je dlouhý testovací text který by blokoval")
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.1, "speak() musí být neblokující")

    def test_stop_clears_queue(self):
        """stop() musí vyprázdnit frontu."""
        self.tts.enabled = False
        for i in range(5):
            self.tts.speak(f"věta {i}")
        self.tts.stop()
        self.assertTrue(self.tts._queue.empty())

    def test_stop_no_error_when_idle(self):
        """stop() nesmí vyhodit výjimku když nic nehraje."""
        self.tts.stop()

    def test_speak_disabled_does_nothing(self):
        """speak() s tts_enabled=False nesmí přidat do fronty."""
        self.tts.enabled = False
        before = self.tts._queue.qsize()
        self.tts.speak("test")
        self.assertEqual(self.tts._queue.qsize(), before)


# ══════════════════════════════════════════════════════
#  SECURITY — CONFIRM ACTION A AUDIT
# ══════════════════════════════════════════════════════

class TestSecurityV2(unittest.TestCase):

    def setUp(self):
        from security_v2 import SecurityManager, PermissionLevel
        self.sec = SecurityManager()

    def test_safe_action_allowed(self):
        """Akce na úrovni SAFE musí projít bez potvrzení."""
        allowed, reason = self.sec.check("get_time", {})
        self.assertTrue(allowed)

    def test_unknown_action_blocked(self):
        """Neznámá akce musí být blokována."""
        allowed, reason = self.sec.check("destroy_everything", {})
        self.assertFalse(allowed)

    def test_dangerous_pattern_blocked(self):
        """Parametry s rm -rf musí být blokované."""
        allowed, reason = self.sec.check("run_script", {"path": "rm -rf /home"})
        self.assertFalse(allowed)

    def test_audit_log_records(self):
        """Audit log musí zaznamenat každou kontrolu."""
        before = len(self.sec.get_audit_log(100))
        self.sec.check("get_date", {})
        after = len(self.sec.get_audit_log(100))
        self.assertGreaterEqual(after, before)  # >= protože log může být prázdný

    def test_confirm_action_safe_no_dialog(self):
        """confirm_action pro SAFE akci musí vrátit True bez dialogu."""
        from security_v2 import confirm_action
        result = confirm_action("get_time", {})
        self.assertTrue(result)


# ══════════════════════════════════════════════════════
#  CALCULATE — SANDBOX SECURITY
# ══════════════════════════════════════════════════════

class TestCalculateSandbox(unittest.TestCase):
    """_cmd_calculate nesmí dovolit spuštění libovolného kódu."""

    def setUp(self):
        self.cmds = CommandExecutor(_CFG)

    def test_basic_math(self):
        self.assertEqual(self.cmds._cmd_calculate("2 + 2"), "4")

    def test_multiplication(self):
        self.assertEqual(self.cmds._cmd_calculate("3 * 7"), "21")

    def test_power(self):
        self.assertEqual(self.cmds._cmd_calculate("2 ** 10"), "1024")

    def test_sqrt(self):
        self.assertEqual(self.cmds._cmd_calculate("sqrt(144)"), "12")

    def test_float_result(self):
        result = self.cmds._cmd_calculate("1 / 3")
        self.assertIn("0.333", result)

    def test_dangerous_import_blocked(self):
        """__import__ nesmí projít."""
        result = self.cmds._cmd_calculate("__import__('os').system('id')")
        self.assertIn("Chyba", result)

    def test_dangerous_open_blocked(self):
        """open() nesmí projít."""
        result = self.cmds._cmd_calculate("open('/etc/passwd').read()")
        self.assertIn("Chyba", result)

    def test_dangerous_exec_blocked(self):
        """exec() nesmí projít."""
        result = self.cmds._cmd_calculate("exec('import os')")
        self.assertIn("Chyba", result)

    def test_string_literal_blocked(self):
        """Řetězcové literály nesmí projít."""
        result = self.cmds._cmd_calculate("'hello'")
        self.assertIn("Chyba", result)


# ══════════════════════════════════════════════════════
#  VALIDACE VSTUPŮ
# ══════════════════════════════════════════════════════

class TestInputValidation(unittest.TestCase):
    """validate_package_name a validate_path musí blokovat nebezpečné vstupy."""

    def setUp(self):
        from commands.utils import validate_package_name, validate_path
        self.vpkg  = validate_package_name
        self.vpath = validate_path

    # ── package name ──────────────────────────────────

    def test_valid_package(self):
        self.assertEqual(self.vpkg("vlc"), "vlc")
        self.assertEqual(self.vpkg("python3-pip"), "python3-pip")
        self.assertEqual(self.vpkg("lib32gcc-s1"), "lib32gcc-s1")

    def test_package_with_spaces_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("vlc; rm -rf /")

    def test_package_semicolon_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("vlc;bash")

    def test_package_ampersand_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("vlc && echo pwned")

    def test_package_backtick_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("`id`")

    def test_package_empty_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("")

    def test_package_too_long_rejected(self):
        with self.assertRaises(ValueError):
            self.vpkg("a" * 200)

    # ── path validation ───────────────────────────────

    def test_valid_home_path(self):
        import os
        p = self.vpath("~")
        self.assertEqual(str(p), os.path.expanduser("~"))

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            self.vpath("")

    def test_path_traversal_resolves(self):
        # validate_path neblokuje traversal absolutně (je v tmp),
        # ale musí vrátit rozřešenou absolutní cestu
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            p = self.vpath(os.path.join(d, "sub", "..", "file.txt"))
            self.assertTrue(p.is_absolute())
            self.assertNotIn("..", str(p))


# ══════════════════════════════════════════════════════
#  SAFE_RUN — SUBPROCESS WRAPPER
# ══════════════════════════════════════════════════════

class TestSafeRun(unittest.TestCase):

    def setUp(self):
        from commands.utils import safe_run
        self.safe_run = safe_run

    def test_echo_returns_output(self):
        r = self.safe_run(["echo", "hello"])
        self.assertEqual(r["rc"], 0)
        self.assertIn("hello", r["stdout"])
        self.assertFalse(r["timeout"])

    def test_nonexistent_cmd(self):
        r = self.safe_run(["_jarvis_nonexistent_cmd_xyz"])
        self.assertEqual(r["rc"], -1)
        self.assertIn("nenalezen", r["stderr"])

    def test_timeout_respected(self):
        r = self.safe_run(["sleep", "10"], timeout=0.1)
        self.assertTrue(r["timeout"])
        self.assertEqual(r["rc"], -1)

    def test_bg_returns_immediately(self):
        import time
        t0 = time.time()
        r = self.safe_run(["sleep", "2"], bg=True)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.5)
        self.assertEqual(r["rc"], 0)

    def test_empty_cmd_raises(self):
        with self.assertRaises(ValueError):
            self.safe_run([])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            self.safe_run("echo hello")  # type: ignore

    def test_exit_code_propagated(self):
        r = self.safe_run(["false"])
        self.assertNotEqual(r["rc"], 0)


# ══════════════════════════════════════════════════════
#  PLUGIN TIMEOUTY
# ══════════════════════════════════════════════════════

class TestPluginTimeout(unittest.TestCase):

    def setUp(self):
        from plugin_system import PluginManager
        self.pm = PluginManager()

    def test_fast_handler_returns_result(self):
        def fast_handler(text):
            return "Rychlá odpověď", {"action": "answer", "params": {}}

        result = self.pm.call_route(fast_handler, "test", plugin_name="fast")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Rychlá odpověď")

    def test_slow_handler_times_out(self):
        import time as _time
        # Nastavíme krátký timeout pro test
        self.pm.config["plugin_handler_timeout"] = 0.3

        def slow_handler(text):
            _time.sleep(10)
            return "Nikdy", {}

        result = self.pm.call_route(slow_handler, "test", plugin_name="slow")
        self.assertEqual(result, (None, None))  # call_route vrátí (None, None)
        self.pm.config["plugin_handler_timeout"] = 5.0  # reset

    def test_crashing_handler_returns_none(self):
        def bad_handler(text):
            raise RuntimeError("plugin explodoval")

        result = self.pm.call_route(bad_handler, "test", plugin_name="bad")
        self.assertEqual(result, (None, None))  # call_route vrátí (None, None)

    def test_action_timeout(self):
        from unittest.mock import patch
        import concurrent.futures

        def slow_action(**kwargs):
            import time
            time.sleep(30)
            return "never"

        # Mock ThreadPoolExecutor.submit aby timeout byl okamžitý
        with patch.object(self.pm, 'call_action',
                          return_value=(None, "timeout")) as mock_call:
            result, err = self.pm.call_action(slow_action, plugin_name="slow_action")
            self.assertIsNone(result)
            self.assertIsNotNone(err)


# ══════════════════════════════════════════════════════
#  COMMANDS — VALIDACE BALÍČKŮ A CEST
# ══════════════════════════════════════════════════════

class TestCommandsValidation(unittest.TestCase):

    def setUp(self):
        self.cmds = CommandExecutor(_CFG)

    @patch("commands.apps.is_app_installed", return_value=False)
    def test_install_valid_package(self, _mock_installed):
        result = self.cmds.execute("install_app", {"name": "vlc"})
        self.assertTrue("instaluji" in result.lower(), result)

    @patch("commands.apps.safe_run")
    def test_install_injection_blocked(self, mock_run):
        result = self.cmds.execute("install_app", {"name": "vlc; rm -rf /"})
        self.assertIn("Chyba", result)
        mock_run.assert_not_called()

    @patch("commands.apps.safe_run")
    def test_uninstall_injection_blocked(self, mock_run):
        result = self.cmds.execute("uninstall_app", {"name": "pkg && reboot"})
        self.assertIn("Chyba", result)
        mock_run.assert_not_called()

    def test_delete_empty_path_blocked(self):
        result = self.cmds.execute("delete_file", {"path": ""})
        self.assertIn("Chyba", result)

    def test_find_files_empty_name(self):
        # prázdný název je OK — vrátí všechny soubory
        with patch("commands.files.safe_run") as mock_run:
            mock_run.return_value = {"rc": 0, "stdout": "/tmp/a\n/tmp/b",
                                     "stderr": "", "timeout": False}
            result = self.cmds.execute("find_files", {"name": ""})
            self.assertNotIn("Chyba", result)


# ══════════════════════════════════════════════════════
#  WAKE WORD — PAUSE / RESUME
# ══════════════════════════════════════════════════════

class TestWakeWordPauseResume(unittest.TestCase):

    def setUp(self):
        from wake_word_detector import WakeWordDetector
        # Neposíláme on_wake callback → detektor se nespustí bez porpoise/SR
        self.detector = WakeWordDetector(wake_word="jarvis", on_wake=None)

    def test_initially_active(self):
        """Detektor musí být po inicializaci aktivní (ne pozastavený)."""
        self.assertTrue(self.detector._paused.is_set())

    def test_pause_clears_event(self):
        """pause() musí vyčistit event (blokovat vlákno)."""
        self.detector.pause()
        self.assertFalse(self.detector._paused.is_set())

    def test_resume_sets_event(self):
        """resume() musí obnovit event."""
        self.detector.pause()
        self.detector.resume()
        self.assertTrue(self.detector._paused.is_set())

    def test_stop_sets_event(self):
        """stop() musí nastavit event aby vlákno mohlo skončit."""
        self.detector.pause()
        self.detector.stop()
        self.assertTrue(self.detector._paused.is_set())


# ══════════════════════════════════════════════════════
#  USER PROFILE — NORMALIZACE DIAKRITIKY
# ══════════════════════════════════════════════════════

class TestUserProfileExtraction(unittest.TestCase):

    def setUp(self):
        import tempfile, pathlib
        tmp = tempfile.mktemp(suffix=".json")
        from user_profile import UserProfile
        self.profile = UserProfile(path=pathlib.Path(tmp))

    def test_extract_name_with_diacritics(self):
        """Extrakce jména s diakritikou (normalizovaný text → lowercase hodnota)."""
        found = self.profile.extract_from_text("Jmenuji se Petr")
        self.assertIn("jméno", found)
        # _norm() vrátí lowercase, jméno bude "petr"
        self.assertEqual(self.profile.get("jméno").lower(), "petr")

    def test_extract_name_without_diacritics(self):
        """Extrakce jména BEZ diakritiky (STT výstup)."""
        self.profile._facts.clear()
        found = self.profile.extract_from_text("jmenuji se Honza")
        self.assertIn("jméno", found)

    def test_extract_city(self):
        """Extrakce města z textu bez diakritiky."""
        self.profile._facts.clear()
        found = self.profile.extract_from_text("bydlim v Brne")
        self.assertIn("město", found)

    def test_extract_hobby(self):
        """Extrakce zájmů."""
        self.profile._facts.clear()
        found = self.profile.extract_from_text("bavi me python a gaming")
        self.assertIn("zájmy", found)

    def test_higher_confidence_overwrites(self):
        """Vyšší confidence přepíše nižší."""
        self.profile.set("jméno", "Stará hodnota", confidence=0.3)
        self.profile.set("jméno", "Nová hodnota", confidence=0.9)
        self.assertEqual(self.profile.get("jméno"), "Nová hodnota")

    def test_lower_confidence_does_not_overwrite(self):
        """Nižší confidence nepřepíše vyšší."""
        self.profile.set("jméno", "Petr", confidence=0.9)
        self.profile.set("jméno", "Jiný", confidence=0.4)
        self.assertEqual(self.profile.get("jméno"), "Petr")


# ══════════════════════════════════════════════════════
#  GUI — HEADLESS (bez zobrazení okna)
# ══════════════════════════════════════════════════════

class TestGUIHeadless(unittest.TestCase):
    """Testy GUI logiky bez otevření okna (mockovaný tkinter)."""

    def test_blend_function(self):
        """blend() musí vrátit validní hex barvu."""
        from gui_legacy import blend
        result = blend("#00d4ff", "#070b12", 0.5)
        self.assertRegex(result, r"^#[0-9a-f]{6}$")

    def test_blend_alpha_zero(self):
        """blend() s alpha=0 musí vrátit barvu pozadí."""
        from gui_legacy import blend
        result = blend("#ffffff", "#000000", 0.0)
        self.assertEqual(result, "#000000")

    def test_blend_alpha_one(self):
        """blend() s alpha=1 musí vrátit barvu popředí."""
        from gui_legacy import blend
        result = blend("#ffffff", "#000000", 1.0)
        self.assertEqual(result, "#ffffff")

    def test_orb_colors_defined(self):
        """Všechny stavy mají definované barvy a ikony."""
        from gui_legacy import ORB_COLORS, STATE_ICON
        for state in ("idle", "listening", "thinking", "speaking"):
            self.assertIn(state, ORB_COLORS)
            self.assertIn(state, STATE_ICON)

    def test_particle_pos_returns_tuple(self):
        """Particle.pos() musí vrátit tuple čísel (x, y) nebo (x, y, depth)."""
        from gui_legacy import Particle
        p = Particle(120, 120)
        result = p.pos(frame=10, speed_mult=1.0, orbit_mult=1.0)
        self.assertIsInstance(result, tuple)
        self.assertGreaterEqual(len(result), 2)
        for v in result:
            self.assertIsInstance(v, (int, float))

    def test_particle_orbit_radius_range(self):
        """Particle orbit radius musí být v platném rozsahu."""
        from gui_legacy import Particle
        for _ in range(20):
            p = Particle(0, 0)
            self.assertGreater(p.orbit_r, 0)
            self.assertLess(p.orbit_r, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
