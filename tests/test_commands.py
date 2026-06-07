"""
Unit tests for commands.py — comprehensive test suite with pytest
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands import CommandExecutor, find_app

pytestmark = [pytest.mark.unit]


@pytest.fixture
def command_executor(mock_config):
    """Create CommandExecutor instance for testing"""
    return CommandExecutor(mock_config)


class TestCommandExecutor:
    """Test suite for CommandExecutor class"""
    
    def test_init(self, command_executor, mock_config):
        """Test CommandExecutor initialization"""
        assert command_executor.config == mock_config
        assert hasattr(command_executor, 'config')
    
    def test_execute_unknown_action(self, command_executor):
        """Test handling unknown action"""
        result = command_executor.execute("unknown_action_xyz", {})
        assert "Neznámá akce" in result or "error" in result.lower()
    
    @patch("commands.apps.safe_run", return_value={"rc": 0})
    @patch("commands.apps.shutil.which", return_value="/usr/bin/google-chrome")
    def test_open_app_chrome(self, _mock_which, mock_safe_run, command_executor):
        """Test opening Chrome application"""
        with patch("commands.apps.find_app", return_value="chrome"):
            result = command_executor._cmd_open_app(app="chrome")
            assert result == "ok"
            assert mock_safe_run.called
    
    def test_open_app_not_found(self, command_executor):
        """Test that open_app always returns a string."""
        result = command_executor._cmd_open_app(app="nonexistent_app_xyz")
        assert isinstance(result, str)
    
    @patch('commands.media.pyautogui.screenshot')
    def test_screenshot(self, mock_screenshot, command_executor):
        """Test screenshot command"""
        with patch("commands.media.HAS_PYAUTOGUI", True):
            # Create mock image with save method
            mock_img = MagicMock()
            mock_screenshot.return_value = mock_img
            
            result = command_executor._cmd_screenshot()
            assert result == "ok" or "Uloženo" in result
    
    def test_create_file(self, command_executor):
        """Test file creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            result = command_executor._cmd_create_file(path=filepath)
            assert os.path.exists(filepath) or "ok" in result
    
    def test_move_file(self, command_executor):
        """Test file moving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "source.txt")
            dst = os.path.join(tmpdir, "dest.txt")
            
            # Create source file
            with open(src, "w") as f:
                f.write("test")
            
            result = command_executor._cmd_move_file(src=src, dst=dst)
            # File should be moved
            assert os.path.exists(dst) or "ok" in result
    
    def test_find_app_chrome(self, command_executor):
        """Test finding Chrome app"""
        result = find_app("chrome")
        assert result is not None
        assert isinstance(result, str)
    
    def test_find_app_alias(self, command_executor):
        """Test finding app by alias"""
        result = find_app("google chrome")
        assert result is not None
    
    def test_find_app_not_found(self, command_executor):
        """Test finding non-existent app"""
        result = find_app("app_that_does_not_exist_xyz")
        # find_app returns name as-is if not in APP_MAP
        assert isinstance(result, str)
    
    def test_cmd_get_time(self, command_executor):
        """Test get_time command"""
        result = command_executor._cmd_get_time()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain time format (HH:MM or similar)
        assert any(c.isdigit() for c in result)
    
    def test_cmd_get_date(self, command_executor):
        """Test get_date command"""
        result = command_executor._cmd_get_date()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain date info (numbers or month names)
        assert any(c.isdigit() for c in result)
    
    def test_cmd_calculate_simple(self, command_executor):
        """Test calculate command with simple math"""
        assert command_executor._cmd_calculate(expression="2+2") == "4"
        assert command_executor._cmd_calculate(expression="10-5") == "5"
        assert command_executor._cmd_calculate(expression="3*4") == "12"
    
    def test_cmd_calculate_invalid(self, command_executor):
        """Test calculate with invalid expression"""
        result = command_executor._cmd_calculate(expression="invalid;;;___")
        assert "Chyba" in result or "error" in result.lower()
    
    def test_cmd_system_info(self, command_executor):
        """Test system_info command"""
        result = command_executor._cmd_system_info()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain some system info keywords
        assert any(kw in result.lower() for kw in ["cpu", "ram", "disk", "%"])
    
    @patch('commands.apps.webbrowser.open')
    def test_cmd_open_url(self, mock_browser, command_executor):
        """Test open_url command"""
        result = command_executor._cmd_open_url(url="https://example.com")
        mock_browser.assert_called_once_with("https://example.com")
        assert result == "ok"
    
    @patch('commands.apps.webbrowser.open')
    def test_cmd_search_web(self, mock_browser, command_executor):
        """Test search_web command"""
        result = command_executor._cmd_search_web(query="Python programming")
        mock_browser.assert_called_once()
        assert result == "ok"
    
    @patch('commands.media.pyautogui')
    def test_cmd_type_key(self, mock_press, command_executor):
        """Test type_key command"""
        with patch("commands.media.HAS_PYAUTOGUI", True):
            result = command_executor._cmd_type_key(key="Return")
            assert result == "ok"
    
    @patch('commands.media.pyautogui')
    def test_cmd_write_text(self, mock_typewrite, command_executor):
        """Test write_text command"""
        with patch("commands.media.HAS_PYAUTOGUI", True):
            result = command_executor._cmd_write_text(text="hello world")
            assert result == "ok"
    
    def test_cmd_clipboard_set(self, command_executor):
        """Test clipboard_set command"""
        with patch('pyperclip.copy') as mock_copy:
            result = command_executor._cmd_clipboard_set(text="test")
            mock_copy.assert_called_with("test")
            assert result == "ok"


class TestAppMap:
    """Test APP_MAP configuration"""
    
    def test_app_map_not_empty(self):
        """Ensure APP_MAP is not empty"""
        from commands import APP_MAP
        assert len(APP_MAP) > 0
    
    def test_app_map_structure(self):
        """Ensure APP_MAP has correct structure"""
        from commands import APP_MAP
        for app_name, aliases in APP_MAP.items():
            assert isinstance(app_name, str)
            assert isinstance(aliases, list)
            assert len(aliases) > 0
            assert all(isinstance(alias, str) for alias in aliases)
    
    def test_app_map_has_common_apps(self):
        """Ensure APP_MAP contains common applications"""
        from commands import APP_MAP
        common_apps = ["chrome", "firefox", "code", "vlc"]
        for app in common_apps:
            assert app in APP_MAP or any(app in aliases for aliases in APP_MAP.values())


class TestSafeRun:
    """Unit testy pro safe_run helper."""

    def test_success(self):
        from commands.utils import safe_run
        r = safe_run(["true"])
        assert r["rc"] == 0
        assert r["timeout"] is False

    def test_nonzero_returncode(self):
        from commands.utils import safe_run
        r = safe_run(["false"])
        assert r["rc"] != 0
        assert r["timeout"] is False

    def test_stdout_captured(self):
        from commands.utils import safe_run
        r = safe_run(["echo", "hello"])
        assert r["rc"] == 0
        assert "hello" in r["stdout"]

    @patch("commands.utils.subprocess.run")
    def test_timeout(self, mock_run):
        import subprocess
        from commands.utils import safe_run
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep"], timeout=1)
        r = safe_run(["sleep", "99"], timeout=1)
        assert r["rc"] == -1
        assert r["timeout"] is True

    @patch("commands.utils.subprocess.run")
    def test_file_not_found(self, mock_run):
        from commands.utils import safe_run
        mock_run.side_effect = FileNotFoundError()
        r = safe_run(["nonexistent_binary_xyz"])
        assert r["rc"] == -1
        assert r["timeout"] is False
        assert "nenalezen" in r["stderr"]

    def test_invalid_cmd_raises(self):
        from commands.utils import safe_run
        with pytest.raises(ValueError):
            safe_run("not a list")
        with pytest.raises(ValueError):
            safe_run([])

    @patch("commands.utils.subprocess.Popen")
    def test_bg_success(self, mock_popen):
        from commands.utils import safe_run
        r = safe_run(["sleep", "10"], bg=True)
        assert r["rc"] == 0
        mock_popen.assert_called_once()

    @patch("commands.utils.subprocess.Popen")
    def test_bg_file_not_found(self, mock_popen):
        from commands.utils import safe_run
        mock_popen.side_effect = FileNotFoundError()
        r = safe_run(["nonexistent_bg_xyz"], bg=True)
        assert r["rc"] == -1
        assert "nenalezen" in r["stderr"]


@pytest.mark.integration
class TestCommandIntegration:
    """Integration tests requiring partial system access"""
    
    @patch('commands.system.psutil.cpu_percent')
    @patch('commands.system.psutil.virtual_memory')
    @patch('commands.system.psutil.disk_usage')
    def test_system_info_with_mocked_psutil(self, mock_disk, mock_mem, mock_cpu, command_executor):
        """Test system_info with mocked psutil"""
        mock_cpu.return_value = 25.5
        mock_mem.return_value = MagicMock(percent=50.0, available=4000000000)
        mock_disk.return_value = MagicMock(percent=60.0, free=100000000000)
        
        result = command_executor._cmd_system_info()
        assert isinstance(result, str)
        assert len(result) > 0
