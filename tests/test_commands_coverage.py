"""Unit testy pro cmd_* funkce — commands/system.py, apps.py, files.py, utils.py"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── commands/system.py ────────────────────────────────────────────────────────

from commands.system import (
    cmd_get_time,
    cmd_get_date,
    cmd_system_info,
    cmd_disk_space,
    cmd_hardware_info,
    cmd_list_directory,
    cmd_file_info,
    cmd_volume,
)


def test_get_time_format():
    result = cmd_get_time()
    assert isinstance(result, str)
    assert ":" in result  # HH:MM:SS
    parts = result.split(":")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_get_date_returns_string():
    result = cmd_get_date()
    assert isinstance(result, str)
    assert len(result) > 0


def test_system_info_contains_cpu_ram_disk():
    result = cmd_system_info()
    assert isinstance(result, str)
    assert "CPU" in result
    assert "RAM" in result
    assert "Disk" in result


def test_disk_space_root():
    result = cmd_disk_space("/")
    assert isinstance(result, str)
    assert "Celkem" in result
    assert "GB" in result


def test_hardware_info_has_cpu():
    result = cmd_hardware_info()
    assert isinstance(result, str)
    assert "CPU" in result


def test_list_directory_home():
    result = cmd_list_directory("~")
    assert isinstance(result, str)
    # Should mention složek (folders) or souborů (files)
    assert "složek" in result or "souborů" in result or "Chyba" in result or "odmítnut" in result


def test_file_info_tmp():
    result = cmd_file_info("/tmp")
    assert isinstance(result, str)
    assert len(result) > 0


def test_volume_set_level():
    result = cmd_volume(level=50)
    assert isinstance(result, str)
    assert "Hlasitost: 50%" in result


def test_volume_mute():
    result = cmd_volume(action="mute")
    assert isinstance(result, str)
    assert "Ztlumeno" in result


# ── commands/apps.py ─────────────────────────────────────────────────────────

from commands.apps import cmd_open_app, cmd_kill_process, find_app


def test_open_nonexistent_app_no_exception():
    """Neexistující app nesmí vyhodit výjimku — musí vrátit string."""
    result = cmd_open_app("neexistujici_app_xyz")
    assert isinstance(result, str)


def test_kill_nonexistent_process_no_exception():
    """Killing process that doesn't exist should return a string, not raise."""
    result = cmd_kill_process("neexistujici_12345")
    assert isinstance(result, str)
    # Typically returns "Proces '...' nenalezen"
    assert len(result) > 0


def test_find_app_chrome_by_alias():
    result = find_app("chrome")
    assert result == "chrome"


def test_find_app_google_chrome():
    result = find_app("google chrome")
    assert result == "chrome"


def test_find_app_unknown_returns_name():
    """Unknown app name should just be returned as-is (lowercase)."""
    result = find_app("somethingunknown")
    assert result == "somethingunknown"


# ── commands/files.py ─────────────────────────────────────────────────────────

from commands.files import cmd_create_folder, cmd_delete_file, cmd_find_files, cmd_clipboard_set


def test_create_folder(tmp_path):
    new_folder = str(tmp_path / "test_new_folder")
    result = cmd_create_folder(path=new_folder)
    assert isinstance(result, str)
    assert Path(new_folder).is_dir()


def test_delete_file_nonexistent_returns_error_string():
    result = cmd_delete_file("/nonexistent/path/does_not_exist_xyz.txt")
    assert isinstance(result, str)
    # Should contain some error message
    assert len(result) > 0


def test_find_files_py_in_home():
    """cmd_find_files hledá *.py soubory v domovském adresáři — vrací string."""
    result = cmd_find_files("*.py", str(Path.home()))
    assert isinstance(result, str)
    assert len(result) > 0  # either files found or "Nic nenalezeno."


def test_clipboard_set_returns_string():
    """Mock pyperclip.copy — v headless CI prostředí clipboard není dostupný."""
    import pyperclip
    with patch.object(pyperclip, "copy", return_value=None):
        result = cmd_clipboard_set("test text")
    assert isinstance(result, str)
    # Should return "ok" on success
    assert result == "ok"


# ── commands/utils.py ─────────────────────────────────────────────────────────

from commands.utils import cmd_calculate, cmd_note_add, cmd_weather, cmd_currency_convert


def test_calculate_addition():
    result = cmd_calculate("2+2")
    assert result == "4"


def test_calculate_sqrt():
    result = cmd_calculate("sqrt(16)")
    assert result == "4"


def test_calculate_blocked_import():
    """Pokus o __import__ musí vrátit chybový string, nikoliv spustit kód."""
    result = cmd_calculate("__import__('os')")
    assert isinstance(result, str)
    assert "Chyba" in result


def test_calculate_division():
    result = cmd_calculate("10/2")
    assert result == "5"


def test_note_add_returns_ok_or_ulozeno(tmp_path):
    """cmd_note_add uloží poznámku — vrátí potvrzovací string."""
    notes_file = str(tmp_path / "jarvis_notes.txt")
    with patch("commands.utils._HOME", str(tmp_path)):
        result = cmd_note_add("test poznámka")
    assert isinstance(result, str)
    assert "Uloženo" in result or "uložena" in result or "ok" in result.lower()


def test_weather_mocked():
    """Testuje cmd_weather s mockovaným requests.get — bez reálného síťového volání."""
    geo_response = MagicMock()
    geo_response.json.return_value = {
        "results": [{
            "latitude": 50.0875,
            "longitude": 14.4213,
            "name": "Praha",
            "country": "Česká republika",
        }]
    }

    weather_response = MagicMock()
    weather_response.json.return_value = {
        "current": {
            "temperature_2m": 18,
            "apparent_temperature": 16,
            "relative_humidity_2m": 65,
            "wind_speed_10m": 12,
            "precipitation": 0,
            "weather_code": 1,
        }
    }

    with patch("requests.get", side_effect=[geo_response, weather_response]):
        result = cmd_weather("Praha")

    assert isinstance(result, str)
    assert len(result) > 0
    assert "Praha" in result


def test_weather_network_failure_returns_string():
    """Při výpadku sítě cmd_weather nesmí vyhodit výjimku."""
    try:
        with patch("requests.get", side_effect=Exception("síť nedostupná")):
            result = cmd_weather("Praha")
        assert isinstance(result, str)
    except Exception:
        pytest.fail("cmd_weather vyhodila výjimku místo vrácení chybového stringu")


def test_currency_convert_usd_to_czk():
    result = cmd_currency_convert(100, "USD", "CZK")
    assert isinstance(result, str)
    # Result should contain a number
    assert any(c.isdigit() for c in result)
    assert "CZK" in result or "czk" in result.lower()


def test_currency_convert_eur_to_czk():
    result = cmd_currency_convert(1, "EUR", "CZK")
    assert isinstance(result, str)
    assert any(c.isdigit() for c in result)


def test_currency_convert_unsupported():
    result = cmd_currency_convert(100, "XYZ", "ABC")
    assert isinstance(result, str)
    assert "Nepodporované" in result or "nepodporované" in result.lower()
