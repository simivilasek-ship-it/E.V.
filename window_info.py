"""Detekce aktivního okna a seznamu oken (X11, AT-SPI, Wayland procesy)."""

from __future__ import annotations

import glob
import os
import time
from typing import Iterable

_CACHE_TTL = 2.0
_cache_at = 0.0
_cache_val: tuple[str, list[str]] = ("", [])

_IGNORE_NAMES = {
    "horní panel", "spodní panel", "pracovní plocha", "desktop",
    "top panel", "bottom panel", "panel", "main stage",
}
_IGNORE_SUBSTR = (
    "uložit snímek", "save screenshot", "screenshot", "snímek obrazovky",
)

# comm (z /proc/pid/comm, max 15 znaků) → popisek v UI
_COMM_LABELS = {
    "cursor": "Cursor",
    "code": "VS Code",
    "code-oss": "VS Code",
    "codium": "VSCodium",
    "firefox": "Firefox",
    "firefox-bin": "Firefox",
    "chrome": "Chrome",
    "chromium": "Chromium",
    "chromium-brows": "Chromium",
    "brave": "Brave",
    "brave-browser": "Brave",
    "nautilus": "Soubory",
    "gnome-control-c": "Nastavení",
    "gnome-software": "Software",
    "gnome-terminal": "Terminál",
    "gnome-term": "Terminál",
    "gnome-text-ed": "Textový editor",
    "ptyxis": "Terminál",
    "kgx": "Terminál",
    "kgx-wrapped": "Terminál",
    "konsole": "Konsole",
    "kitty": "Kitty",
    "alacritty": "Alacritty",
    "wezterm": "WezTerm",
    "wezterm-gui": "WezTerm",
    "ghostty": "Ghostty",
    "foot": "Foot",
    "tilix": "Tilix",
    "slack": "Slack",
    "discord": "Discord",
    "spotify": "Spotify",
    "telegram-deskto": "Telegram",
    "telegram": "Telegram",
    "evince": "Evince",
    "eog": "Prohlížeč obrázků",
    "libreoffice": "LibreOffice",
    "soffice.bin": "LibreOffice",
    "gedit": "gedit",
    "thunderbird": "Thunderbird",
    "evolution": "Evolution",
    "steam": "Steam",
    "steamwebhelper": "Steam",
    "vlc": "VLC",
    "mpv": "mpv",
    "obs": "OBS",
    "obsidian": "Obsidian",
    "signal-desktop": "Signal",
    "zoom": "Zoom",
    "zoomus": "Zoom",
    "remmina": "Remmina",
    "virt-manager": "Virt Manager",
    "gnome-boxes": "Boxes",
}

_SKIP_PREFIX = (
    "gnome-shell", "gnome-session", "gnome-keyring", "gsd-",
    "xdg-desktop-por", "xdg-document-po", "xdg-permission",
    "ibus", "pipewire", "wireplumber", "pulseaudio",
    "chrome_crashpad", "crashpad", "evolution-alarm",
)


def _should_ignore(name: str) -> bool:
    low = (name or "").lower().strip()
    if not low or low in _IGNORE_NAMES:
        return True
    return any(s in low for s in _IGNORE_SUBSTR)


def _label_for_comm(comm: str) -> str:
    return _COMM_LABELS.get((comm or "").lower().strip(), "")


def _cpu_ticks(pid: int) -> int:
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as fh:
            parts = fh.read().split()
        return int(parts[13]) + int(parts[14])
    except (OSError, IndexError, ValueError):
        return 0


def _fd_targets(pid: int) -> Iterable[str]:
    try:
        for fd in glob.glob(f"/proc/{pid}/fd/*"):
            try:
                yield os.readlink(fd)
            except OSError:
                continue
    except OSError:
        return


def _is_wayland_window_process(pid: int) -> bool:
    for target in _fd_targets(pid):
        if (
            "wayland-cursor" in target
            or "wayland-keymap" in target
            or "wayland-0" in target
            or "wayland-proxy" in target
        ):
            return True
    return False


def _atspi_windows() -> tuple[str, list[str]]:
    """GTK/AT-SPI titulky, pokud je PyGObject dostupné."""
    try:
        import gi  # type: ignore

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi  # type: ignore
    except Exception:
        return "", []

    try:
        Atspi.init()
        desktop = Atspi.get_desktop(0)
        names: list[str] = []
        active = ""
        best_score = -1
        for i in range(int(desktop.get_child_count() or 0)):
            app = desktop.get_child_at_index(i)
            app_name = str(app.get_name() or "").strip()
            if not app_name or app_name.lower() in ("gnome-shell", "ibus-extension-gtk3"):
                continue
            for j in range(min(int(app.get_child_count() or 0), 12)):
                child = app.get_child_at_index(j)
                title = str(child.get_name() or "").strip() or app_name
                if _should_ignore(title):
                    continue
                role = str(child.get_role_name() or "")
                if role not in ("window", "frame", "dialog", "filler", "application"):
                    continue
                if title not in names:
                    names.append(title[:80])
                score = 0
                try:
                    st = child.get_state_set()
                    if st.contains(Atspi.StateType.ACTIVE):
                        score += 4
                    if st.contains(Atspi.StateType.FOCUSED):
                        score += 2
                    if st.contains(Atspi.StateType.SHOWING):
                        score += 1
                except Exception:
                    pass
                if score > best_score:
                    best_score = score
                    active = title[:100]
        if not active and names:
            active = names[0]
        return active, names
    except Exception:
        return "", []


def _process_windows() -> tuple[str, list[str]]:
    """Wayland: GUI procesy podle socketů / comm (bez titulků compositoru)."""
    scored: dict[str, int] = {}
    uid = os.getuid()
    for comm_path in glob.glob("/proc/[0-9]*/comm"):
        try:
            pid = int(comm_path.split("/")[2])
            st = os.stat(comm_path)
            if st.st_uid != uid:
                continue
            comm = open(comm_path, encoding="utf-8", errors="replace").read().strip()
        except (OSError, ValueError):
            continue
        low = comm.lower()
        if any(low.startswith(p) for p in _SKIP_PREFIX):
            continue
        label = _label_for_comm(comm)
        if not label:
            continue
        if not _is_wayland_window_process(pid):
            # Některé GTK aplikace nemají wayland-cursor v fd, ale comm je známý.
            if low not in ("gnome-control-c", "nautilus", "ptyxis", "kgx"):
                continue
        ticks = _cpu_ticks(pid)
        scored[label] = scored.get(label, 0) + ticks

    if not scored:
        return "", []
    ordered = sorted(scored, key=lambda name: scored[name], reverse=True)
    return ordered[0], ordered


def get_desktop_windows(*, force: bool = False) -> tuple[str, list[str]]:
    """Vrátí (aktivní okno, seznam otevřených oken). Výsledek je krátce cachován."""
    global _cache_at, _cache_val
    now = time.monotonic()
    if not force and (now - _cache_at) < _CACHE_TTL:
        return _cache_val

    active, names = _atspi_windows()
    proc_active, proc_names = _process_windows()

    merged: list[str] = []
    for title in names + proc_names:
        if title and title not in merged and not _should_ignore(title):
            merged.append(title)
    if not active:
        active = proc_active
    elif proc_active and proc_active not in merged:
        merged.insert(0, proc_active)

    _cache_val = (active, merged)
    _cache_at = now
    return _cache_val
