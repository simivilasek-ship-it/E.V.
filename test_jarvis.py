#!/usr/bin/env python3
"""
JARVIS v3.0 — Unit testy
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
        for m in ("ask", "stream_ask", "clear_history", "is_available", "_quick_match"):
            self.assertTrue(hasattr(self.llm, m))

    def test_clear_history(self):
        self.llm.history.append({"role": "user", "content": "test"})
        self.llm.clear_history()
        self.assertEqual(len(self.llm.history), 0)

    def test_quick_match_time(self):
        msg, action = self.llm._quick_match("kolik je hodin")
        self.assertIsNotNone(action)
        self.assertEqual(action["action"], "get_time")
        self.assertIn(":", msg)

    def test_quick_match_unknown(self):
        # Čistě konverzační dotaz
        _, action = self.llm._quick_match("ahoj jak se máš")
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

    @patch("subprocess.Popen")
    def test_open_app(self, mock_popen):
        result = self.cmds.execute("open_app", {"app": "firefox"})
        self.assertEqual(result, "ok")
        mock_popen.assert_called()

    @patch("commands.pyautogui")
    def test_volume_mute(self, mock_pg):
        result = self.cmds.execute("volume", {"action": "mute"})
        self.assertEqual(result, "ok")
        mock_pg.press.assert_called_with("volumemute")

    @patch("commands.pyautogui")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
