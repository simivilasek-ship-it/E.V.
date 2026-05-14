"""Systémové příkazy: vypnutí, restart, jas, hlasitost, systémové info."""

import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

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
        subprocess.run(["shutdown", "/s", "/t", str(delay)], check=False)
    else:
        cmd = ["shutdown", "-h", f"+{delay // 60}"] if delay else ["shutdown", "-h", "now"]
        subprocess.run(cmd, check=False)
    return "ok"


def cmd_restart(delay: int = 0) -> str:
    if _IS_WINDOWS:
        subprocess.run(["shutdown", "/r", "/t", str(delay)], check=False)
    else:
        subprocess.run(["reboot"], check=False)
    return "ok"


def cmd_sleep_pc() -> str:
    if _IS_WINDOWS:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
    else:
        subprocess.run(["systemctl", "suspend"], check=False)
    return "ok"


def cmd_update_system() -> str:
    if _IS_LINUX:
        subprocess.Popen(["pkexec", "bash", "-c", "apt update && apt upgrade -y"])
    return "Spouštím aktualizaci..."


def _set_volume_linux(level: int) -> None:
    """Nastaví hlasitost přes pactl (PulseAudio) nebo amixer."""
    if subprocess.run(["which", "pactl"], capture_output=True).returncode == 0:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
                       capture_output=True)
    else:
        subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%"],
                       capture_output=True)


def cmd_volume(level: int = None, action: str = None) -> str:
    try:
        if action == "mute":
            if _IS_LINUX:
                subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"],
                                capture_output=True)
            return "Ztlumeno."
        if action == "unmute":
            if _IS_LINUX:
                subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"],
                                capture_output=True)
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
        if subprocess.run(["which", "brightnessctl"], capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", f"{level}%"], capture_output=True)
        else:
            try:
                displays = subprocess.check_output(
                    "xrandr | grep ' connected' | awk '{print $1}'",
                    shell=True, text=True,
                ).strip().split("\n")
                for d in displays:
                    if d:
                        subprocess.run(["xrandr", "--output", d,
                                        "--brightness", str(level / 100)])
            except Exception as e:
                return f"Chyba jasu: {e}"
    return f"Jas: {level}%"
