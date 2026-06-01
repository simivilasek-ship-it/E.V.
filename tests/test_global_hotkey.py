"""
Testy pro global_hotkey.py
"""
from __future__ import annotations
import sys
import types
from unittest.mock import MagicMock, patch


def test_init_no_pynput():
    """Bez pynput: available=False, žádná výjimka."""
    # Ujisti se, že pynput není dostupné v tomto kontextu
    with patch.dict(sys.modules, {"pynput": None}):
        # Reload modulu aby přepsal _available
        import importlib
        import global_hotkey as gh_mod
        importlib.reload(gh_mod)

        gh = gh_mod.GlobalHotkey(callback=lambda t: None)
        assert gh.available is False


def test_init_with_mock_pynput():
    """S mock pynput: available=True."""
    mock_pynput = types.ModuleType("pynput")
    mock_pynput.keyboard = MagicMock()

    with patch.dict(sys.modules, {"pynput": mock_pynput, "pynput.keyboard": mock_pynput.keyboard}):
        import importlib
        import global_hotkey as gh_mod
        importlib.reload(gh_mod)

        gh = gh_mod.GlobalHotkey(callback=lambda t: None)
        assert gh.available is True


def test_start_returns_false_no_deps():
    """Bez pynput: start() vrátí False a nepadne."""
    with patch.dict(sys.modules, {"pynput": None}):
        import importlib
        import global_hotkey as gh_mod
        importlib.reload(gh_mod)

        gh = gh_mod.GlobalHotkey(callback=lambda t: None)
        result = gh.start()
        assert result is False


def test_stop_no_crash():
    """stop() na neinitialized instanci nepadne."""
    with patch.dict(sys.modules, {"pynput": None}):
        import importlib
        import global_hotkey as gh_mod
        importlib.reload(gh_mod)

        gh = gh_mod.GlobalHotkey(callback=lambda t: None)
        # Nesmí vyhodit žádnou výjimku
        gh.stop()
        gh.stop()  # druhý stop je také bezpečný
        assert gh._running is False
        assert gh._listener is None
