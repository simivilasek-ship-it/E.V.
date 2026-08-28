"""Detekce oken na Waylandu (bez xdotool)."""

from __future__ import annotations

from window_info import _label_for_comm, get_desktop_windows


def test_label_for_known_apps():
    assert _label_for_comm("cursor") == "Cursor"
    assert _label_for_comm("firefox") == "Firefox"
    assert _label_for_comm("gnome-control-c") == "Nastavení"
    assert _label_for_comm("chrome_crashpad") == ""


def test_get_desktop_windows_merges_atspi_and_process(monkeypatch):
    monkeypatch.setattr("window_info._atspi_windows", lambda: ("Nastavení", ["Nastavení"]))
    monkeypatch.setattr("window_info._process_windows", lambda: ("Cursor", ["Cursor", "Firefox"]))
    active, names = get_desktop_windows(force=True)
    assert active == "Nastavení"
    assert names == ["Nastavení", "Cursor", "Firefox"]


def test_linux_collector_uses_window_info_without_xdotool(monkeypatch):
    import subprocess
    import platform
    from activity_collector import ActivityCollector

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("xdotool")),
    )
    monkeypatch.setattr(
        "window_info.get_desktop_windows",
        lambda **k: ("Cursor", ["Cursor", "Firefox"]),
    )
    assert ActivityCollector()._get_active_window() == "Cursor"
