#!/usr/bin/env python3
"""
JARVIS v2.0 — Unit testy
Spuštění: python test_jarvis.py
"""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Přidat aktuální adresář do cesty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock volitelné závislosti před importem modulů
for _mod in ("pyautogui", "pyperclip", "edge_tts", "pyttsx3",
             "speech_recognition", "customtkinter", "pycaw",
             "pycaw.pycaw", "comtypes"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Importovat JARVIS moduly
try:
    from config import CONFIG
    from stt import STTEngine
    from tts import TTSEngine
    from llm import LLMEngine
    from commands import CommandExecutor
except ImportError as e:
    print(f"Chyba importu modulů: {e}")
    sys.exit(1)

class TestJarvis(unittest.TestCase):

    def setUp(self):
        """Nastavení testů"""
        # Mock config pro testy
        self.test_config = {
            "ollama_url": "http://localhost:11434/api/chat",
            "ollama_model": "llama3.1:8b",
            "tts_enabled": True,
            "tts_rate": 170,
            "history_size": 20,
            "window_size": "560x760",
            "log_level": "INFO",
        }

    def test_config_loading(self):
        """Test načítání konfigurace"""
        # Testujeme, že config má výchozí hodnoty
        config_keys = ["ollama_url", "ollama_model", "tts_enabled", "tts_rate", "history_size", "window_size"]
        for key in config_keys:
            self.assertIn(key, CONFIG)

    def test_stt_engine_init(self):
        """Test inicializace STT enginu"""
        stt = STTEngine(self.test_config)
        self.assertIsNotNone(stt)
        # Test, že má metodu listen
        self.assertTrue(hasattr(stt, 'listen'))
        self.assertTrue(hasattr(stt, 'is_available'))

    def test_tts_engine_init(self):
        """Test inicializace TTS enginu"""
        tts = TTSEngine(self.test_config)
        self.assertIsNotNone(tts)
        # Test, že má metody speak a is_available
        self.assertTrue(hasattr(tts, 'speak'))
        self.assertTrue(hasattr(tts, 'is_available'))

    def test_llm_engine_init(self):
        """Test inicializace LLM enginu"""
        llm = LLMEngine(self.test_config)
        self.assertIsNotNone(llm)
        # Test, že má metody ask, is_available, clear_history
        self.assertTrue(hasattr(llm, 'ask'))
        self.assertTrue(hasattr(llm, 'is_available'))
        self.assertTrue(hasattr(llm, 'clear_history'))

    def test_commands_executor_init(self):
        """Test inicializace CommandExecutor"""
        commands = CommandExecutor(self.test_config)
        self.assertIsNotNone(commands)
        # Test, že má metodu execute
        self.assertTrue(hasattr(commands, 'execute'))

    @patch('subprocess.Popen')
    def test_commands_open_app_linux(self, mock_popen):
        """Test otevření aplikace na Linuxu"""
        commands = CommandExecutor(self.test_config)
        result = commands.execute("open_app", {"app": "firefox"})
        self.assertEqual(result, "ok")
        # Ověřit, že subprocess.Popen byl zavolán
        mock_popen.assert_called()

    @patch('commands.pyautogui')
    def test_commands_screenshot(self, mock_pg):
        """Test screenshotu"""
        mock_img = MagicMock()
        mock_pg.screenshot.return_value = mock_img

        commands = CommandExecutor(self.test_config)
        result = commands.execute("screenshot", {})
        self.assertIn("Uloženo:", result)
        mock_pg.screenshot.assert_called_once()
        mock_img.save.assert_called_once()

    @patch('commands.pyautogui')
    def test_commands_volume_mute(self, mock_pg):
        """Test ztlumení hlasitosti"""
        commands = CommandExecutor(self.test_config)
        result = commands.execute("volume", {"action": "mute"})
        self.assertEqual(result, "ok")
        mock_pg.press.assert_called_with("volumemute")

    def test_llm_clear_history(self):
        """Test vymazání historie LLM"""
        llm = LLMEngine(self.test_config)
        # Přidat nějakou historii (mock)
        llm.history = [{"role": "user", "content": "test"}]
        llm.clear_history()
        self.assertEqual(len(llm.history), 0)

    @patch('requests.post')
    def test_llm_ask_mock(self, mock_post):
        """Test LLM odpovědi (mock)"""
        # Mock odpověď od Ollama - správný formát
        mock_response = MagicMock()
        # Nový formát: plain text = AI odpověď, COMMAND: X = příkaz
        mock_response.json.return_value = {
            "message": {"content": "Test odpověď"}
        }
        mock_post.return_value = mock_response

        llm = LLMEngine(self.test_config)
        message, action_data = llm.ask("Test otázka")

        self.assertEqual(message, "Test odpověď")
        self.assertEqual(action_data["action"], "answer")
        mock_post.assert_called_once()

if __name__ == "__main__":
    unittest.main()
