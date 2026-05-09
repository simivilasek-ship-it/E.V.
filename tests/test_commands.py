import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands import CommandExecutor


class TestCommandExecutor(unittest.TestCase):
    def setUp(self):
        self.config = {"log_level": "INFO"}
        self.commands = CommandExecutor(self.config)

    @patch('commands.subprocess.Popen')
    def test_open_app(self, mock_popen):
        result = self.commands.execute("open_app", {"app": "firefox"})
        self.assertEqual(result, "ok")
        mock_popen.assert_called_once()

    @patch('commands.pyautogui')
    def test_screenshot(self, mock_pg):
        mock_img = MagicMock()
        mock_pg.screenshot.return_value = mock_img
        mock_pg.screenshot.return_value.save = MagicMock()

        result = self.commands.execute("screenshot", {})
        self.assertIn("Uloženo:", result)
        mock_pg.screenshot.assert_called_once()
        mock_img.save.assert_called_once()

    def test_create_and_move_file(self):
        tmp_dir = tempfile.mkdtemp()
        src = os.path.join(tmp_dir, "source.txt")
        dst = os.path.join(tmp_dir, "dest.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("hello")

        result_create = self.commands.execute("create_file", {"path": src})
        self.assertIn("Soubor vytvořen", result_create)

        result_move = self.commands.execute("move_file", {"src": src, "dst": dst})
        self.assertIn("Přesunuto:", result_move)
        self.assertTrue(os.path.exists(dst))

    def test_volume_mute(self):
        with patch('commands.pyautogui') as mock_pg:
            result = self.commands.execute("volume", {"action": "mute"})
            self.assertEqual(result, "ok")
            mock_pg.press.assert_called_with("volumemute")
