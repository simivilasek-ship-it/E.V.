"""Systémové příkazy: vypnutí, restart, jas, hlasitost, systémové info."""

import logging
import platform
from datetime import datetime

import psutil

from commands.utils import safe_run

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux"


def cmd_get_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def cmd_get_date() -> str:
    fmt = "%-d. %-m. %Y" if _IS_LINUX else "%#d. %#m. %Y"
    return datetime.now().strftime(fmt)


def cmd_system_info() -> str:
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return (
        f"CPU: {cpu:.0f}% | "
        f"RAM: {ram.percent:.0f}% ({ram.used // 1024 // 1024} / {ram.total // 1024 // 1024} MB) | "
        f"Disk: {disk.percent:.0f}%"
    )


def cmd_shutdown(delay: int = 0) -> str:
    if _IS_WINDOWS:
        safe_run(["shutdown", "/s", "/t", str(delay)], timeout=5)
    else:
        cmd = ["shutdown", "-h", f"+{delay // 60}"] if delay else ["shutdown", "-h", "now"]
        safe_run(cmd, timeout=5)
    return "ok"


def cmd_restart(delay: int = 0) -> str:
    if _IS_WINDOWS:
        safe_run(["shutdown", "/r", "/t", str(delay)], timeout=5)
    else:
        safe_run(["reboot"], timeout=5)
    return "ok"


def cmd_sleep_pc() -> str:
    if _IS_WINDOWS:
        safe_run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], timeout=5)
    else:
        safe_run(["systemctl", "suspend"], timeout=5)
    return "ok"


def cmd_update_system() -> str:
    if _IS_LINUX:
        safe_run(["pkexec", "apt", "update"], bg=True)
        safe_run(["pkexec", "apt", "upgrade", "-y"], bg=True)
    return "Spouštím aktualizaci..."


def _set_volume_linux(level: int) -> None:
    """Nastaví hlasitost přes pactl (PulseAudio) nebo amixer."""
    if safe_run(["which", "pactl"], timeout=3)["rc"] == 0:
        safe_run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], timeout=5)
    else:
        safe_run(["amixer", "-q", "sset", "Master", f"{level}%"], timeout=5)


def cmd_volume(level: int = None, action: str = None) -> str:
    try:
        if action == "mute":
            if _IS_LINUX:
                safe_run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], timeout=5)
            return "Ztlumeno."
        if action == "unmute":
            if _IS_LINUX:
                safe_run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], timeout=5)
            return "Odtlumeno."
        if level is not None:
            level = max(0, min(100, int(level)))
            if _IS_LINUX:
                _set_volume_linux(level)
            return f"Hlasitost: {level}%"
    except Exception as e:
        return f"Chyba: {e}"
    return "ok"


def cmd_set_brightness(level: int = 50) -> str:
    level = max(1, min(100, int(level)))
    if _IS_LINUX:
        if safe_run(["which", "brightnessctl"], timeout=3)["rc"] == 0:
            safe_run(["brightnessctl", "set", f"{level}%"], timeout=5)
        else:
            try:
                r = safe_run(["xrandr"], timeout=5)
                displays = [
                    line.split()[0]
                    for line in r["stdout"].splitlines()
                    if " connected" in line
                ]
                for d in displays:
                    if d:
                        safe_run(["xrandr", "--output", d,
                                  "--brightness", str(level / 100)], timeout=5)
            except Exception as e:
                return f"Chyba jasu: {e}"
    return f"Jas: {level}%"
