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

# Importovat JARVIS moduly (bez GUI)
try:
    import jarvis
except ImportError as e:
    print(f"Chyba importu jarvis: {e}")
    sys.exit(1)

class TestJarvis(unittest.TestCase):

    def setUp(self):
        # Mock config
        jarvis._cfg = {
            "ollama_url": "http://localhost:11434/api/chat",
            "ollama_model": "llama3.1:8b",
            "tts_enabled": True,
            "tts_rate": 170,
            "history_size": 20,
            "window_size": "560x760",
        }
        jarvis.OLLAMA_URL = jarvis._cfg["ollama_url"]
        jarvis.OLLAMA_MODEL = jarvis._cfg["ollama_model"]

    def test_find_app(self):
        """Test nalezení aplikace"""
        self.assertEqual(jarvis._find_app("chrome"), "chrome")
        self.assertEqual(jarvis._find_app("firefox"), "firefox")
        self.assertEqual(jarvis._find_app("neexistuje"), "neexistuje")

    @patch('subprocess.run')
    def test_set_volume_linux(self, mock_run):
        """Test nastavení hlasitosti na Linuxu"""
        jarvis.IS_LINUX = True
        jarvis.IS_WINDOWS = False
        jarvis._set_volume(50)
        mock_run.assert_called_with(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "50%"], capture_output=True)

    @patch('subprocess.run')
    def test_get_volume_linux(self, mock_run):
        """Test získání hlasitosti na Linuxu"""
        jarvis.IS_LINUX = True
        jarvis.IS_WINDOWS = False
        mock_run.return_value.stdout.decode.return_value = "Volume: 0:  50% / 100% / 100%"
        result = jarvis._get_volume()
        self.assertEqual(result, 50)

    def test_ask_ollama_mock(self):
        """Test Ollama odpovědi (mock)"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"message": {"content": '{"action": "answer", "params": {}, "message": "Test"}'}}
            mock_post.return_value = mock_response

            result = jarvis.ask_ollama("Test")
            self.assertEqual(result["action"], "answer")
            self.assertEqual(result["message"], "Test")

    def test_execute_action_open_app_linux(self):
        """Test otevření aplikace na Linuxu"""
        jarvis.IS_LINUX = True
        jarvis.IS_WINDOWS = False

        with patch('subprocess.Popen') as mock_popen:
            result = jarvis.execute_action("open_app", {"app": "firefox"})
            mock_popen.assert_called_with("firefox", shell=True)
            self.assertEqual(result, "ok")

    def test_execute_action_volume(self):
        """Test nastavení hlasitosti"""
        with patch('jarvis._set_volume') as mock_set:
            result = jarvis.execute_action("volume", {"level": 75})
            mock_set.assert_called_with(75)
            self.assertEqual(result, "ok")

    def test_execute_action_screenshot(self):
        """Test screenshotu"""
        with patch('pyautogui.screenshot') as mock_screenshot:
            mock_img = MagicMock()
            mock_screenshot.return_value = mock_img
            mock_img.save = MagicMock()

            result = jarvis.execute_action("screenshot", {})
            self.assertIn("Uloženo:", result)
            mock_screenshot.assert_called_once()
            mock_img.save.assert_called_once()

if __name__ == '__main__':
    unittest.main()