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


def cmd_pc_overview() -> str:
    """Kompletní přehled PC — jako Copilot/Gemini s vědomím o systému."""
    import socket
    import time as _time

    lines: list[str] = []
    host = socket.gethostname()
    lines.append(f"🖥️ {host} — {platform.system()} {platform.release()}")

    uptime_h = int((_time.time() - psutil.boot_time()) // 3600)
    lines.append(f"⏱️ Uptime: {uptime_h} hodin")

    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    lines.append(
        f"📊 CPU {cpu:.0f}% | RAM {ram.percent:.0f}% "
        f"({ram.used // 2**30}/{ram.total // 2**30} GB) | "
        f"Disk {disk.percent:.0f}% (volno {disk.free // 2**30} GB)"
    )

    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            plug = "nabíjí se" if bat.power_plugged else "na baterii"
            lines.append(f"🔋 Baterie {bat.percent:.0f}% ({plug})")
    except Exception:
        pass

    try:
        from context_orchestrator import get_context_orchestrator
        ctx = get_context_orchestrator().get_context()
        if ctx:
            lines.append("")
            lines.append(ctx)
    except Exception:
        pass

    try:
        procs: list[tuple[float, str]] = []
        for p in psutil.process_iter(["name", "cpu_percent"]):
            try:
                procs.append((p.info.get("cpu_percent") or 0.0, p.info.get("name") or "?"))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(reverse=True)
        top = [f"{n} ({c:.0f}%)" for c, n in procs[:5] if c > 0.5]
        if top:
            lines.append(f"🔥 Top procesy: {', '.join(top)}")
    except Exception:
        pass

    return "\n".join(lines)


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


def _filter_gpu_names(gpus: list[str]) -> list[str]:
    """Vyfiltruje audio/duplicitní GPU — nechá hlavní grafiku."""
    import re

    skip = re.compile(r"audio controller|high definition audio|hdmi audio", re.I)
    integrated = re.compile(r"raphael|integrated|basic render|uhd graphics|vega \d", re.I)
    discrete = re.compile(r"radeon rx|geforce|rtx |gtx |arc a\d|quadro|nav[ií] \d", re.I)

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in gpus:
        name = raw.strip()
        if not name or skip.search(name):
            continue
        key = re.sub(r"\s+", " ", name.lower())
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    if any(discrete.search(g) for g in cleaned):
        cleaned = [g for g in cleaned if not integrated.search(g)]

    return cleaned


def _collect_gpus() -> list[str]:
    """Sebere GPU z nvidia-smi a lspci."""
    import subprocess
    import re

    gpus: list[str] = []
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                if line.strip():
                    gpus.append(line.strip())
    except Exception:
        pass

    try:
        r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if re.search(r"VGA|3D controller|Display controller", line, re.I):
                gpus.append(re.sub(r"^.*:\s*", "", line).strip())
    except Exception:
        pass

    return _filter_gpu_names(gpus)


def cmd_hardware_info() -> str:
    """Zjistí hardwarové komponenty PC — přehledný markdown výstup."""
    import subprocess
    import re

    sections: list[str] = ["### 🖥️ Hardwarové komponenty", ""]

    # ── CPU ──────────────────────────────────────────
    cpu_name = ""
    try:
        r = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if re.match(r"^Model name", line, re.I):
                cpu_name = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    if not cpu_name:
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
    if not cpu_name:
        cpu_name = platform.processor() or "neznámý"

    cores = psutil.cpu_count(logical=False) or 0
    threads = psutil.cpu_count(logical=True) or 0
    freq = psutil.cpu_freq()
    freq_str = f" · {freq.max / 1000:.1f} GHz" if freq and freq.max else ""

    sections += [
        "**Procesor**",
        f"- {cpu_name}",
        f"- {cores} jader / {threads} vláken{freq_str}",
        "",
    ]

    # ── RAM ──────────────────────────────────────────
    ram = psutil.virtual_memory()
    ram_total = ram.total / 1024 ** 3
    ram_free = ram.available / 1024 ** 3
    sections += [
        "**Paměť RAM**",
        f"- {ram_total:.0f} GB celkem",
        f"- {ram.percent:.0f}% obsazeno · {ram_free:.1f} GB volné",
        "",
    ]

    # ── Disk ─────────────────────────────────────────
    disk_lines: list[str] = []
    try:
        for part in psutil.disk_partitions(all=False):
            if "loop" in part.device:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = usage.total / 1024 ** 3
                free_gb = usage.free / 1024 ** 3
                disk_lines.append(
                    f"- `{part.device}` — **{total_gb:.0f} GB** {part.fstype} "
                    f"({usage.percent:.0f}% obsazeno, volné {free_gb:.0f} GB)"
                )
            except Exception:
                pass
    except Exception:
        pass
    if disk_lines:
        sections += ["**Úložiště**", *disk_lines, ""]

    # ── GPU ──────────────────────────────────────────
    gpus = _collect_gpus()
    if gpus:
        sections += ["**Grafika**", *[f"- {g}" for g in gpus], ""]
    else:
        sections += ["**Grafika**", "- Nezjištěno (nvidia-smi / lspci)", ""]

    # ── Základní deska ───────────────────────────────
    try:
        r = subprocess.run(
            ["lshw", "-class", "system", "-short"],
            capture_output=True, text=True, timeout=8,
        )
        for line in r.stdout.splitlines():
            if "system" in line.lower() and "/" not in line[:5]:
                parts = line.strip().split(None, 2)
                if len(parts) >= 3 and parts[-1]:
                    sections += ["**Systém / deska**", f"- {parts[-1]}", ""]
                    break
    except Exception:
        pass

    # ── OS ───────────────────────────────────────────
    sections += [
        "**Operační systém**",
        f"- {platform.system()} {platform.release()} ({platform.machine()})",
    ]

    return "\n".join(sections)


def cmd_disk_space(path: str = "/") -> str:
    """Zobrazí místo na disku — celkové, obsazené, volné."""
    import shutil
    lines = []

    # Hlavní disk
    try:
        total, used, free = shutil.disk_usage(path)
        pct = round(used / total * 100)
        lines.append(
            f"Disk ({path}):\n"
            f"  Celkem: {total / 1024**3:.1f} GB\n"
            f"  Obsazeno: {used / 1024**3:.1f} GB ({pct}%)\n"
            f"  Volné: {free / 1024**3:.1f} GB"
        )
    except Exception as e:
        lines.append(f"Chyba čtení disku: {e}")

    # Všechny oddíly
    try:
        for part in psutil.disk_partitions(all=False):
            if "loop" in part.device or part.mountpoint == path:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                free_gb = usage.free / 1024**3
                total_gb = usage.total / 1024**3
                pct = round(usage.percent)
                lines.append(
                    f"Oddíl {part.device} ({part.mountpoint}):\n"
                    f"  {usage.used/1024**3:.1f} / {total_gb:.1f} GB "
                    f"({pct}% obsazeno, volné: {free_gb:.1f} GB)"
                )
            except Exception:
                pass
    except Exception:
        pass

    return "\n\n".join(lines) if lines else "Nelze zjistit místo na disku."


def cmd_list_directory(path: str = "~", max_items: int = 30) -> str:
    """Vypíše obsah složky s velikostmi a informacemi."""
    from pathlib import Path

    try:
        p = Path(path.strip()).expanduser().resolve()
        if not p.exists():
            return f"Složka neexistuje: {path}"
        if not p.is_dir():
            # Vrátí info o souboru
            stat = p.stat()
            size = stat.st_size
            if size > 1024**3:
                size_str = f"{size/1024**3:.2f} GB"
            elif size > 1024**2:
                size_str = f"{size/1024**2:.1f} MB"
            elif size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} B"
            return f"Soubor: {p.name}\nVelikost: {size_str}\nCesta: {p}"

        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = [f"📁 {p}\n"]

        dirs, files = [], []
        for item in items[:max_items]:
            try:
                if item.is_dir():
                    # Počet položek ve složce
                    try:
                        count = sum(1 for _ in item.iterdir())
                        dirs.append(f"  📂 {item.name}/  [{count} položek]")
                    except PermissionError:
                        dirs.append(f"  📂 {item.name}/  [přístup odmítnut]")
                else:
                    size = item.stat().st_size
                    if size > 1024**3:
                        size_str = f"{size/1024**3:.1f} GB"
                    elif size > 1024**2:
                        size_str = f"{size/1024**2:.1f} MB"
                    elif size > 1024:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size} B"
                    files.append(f"  📄 {item.name}  ({size_str})")
            except Exception:
                pass

        lines.extend(dirs)
        lines.extend(files)

        total_items = sum(1 for _ in p.iterdir())
        if total_items > max_items:
            lines.append(f"\n  ... a {total_items - max_items} dalších položek")
        lines.append(f"\nCelkem: {len(dirs)} složek, {len(files)} souborů")

        return "\n".join(lines)

    except PermissionError:
        return f"Přístup ke složce odmítnut: {path}"
    except Exception as e:
        return f"Chyba čtení složky: {e}"


def cmd_file_info(path: str = "") -> str:
    """Detailní informace o souboru nebo složce."""
    from pathlib import Path
    from datetime import datetime

    if not path:
        return "Zadej cestu k souboru nebo složce."
    try:
        p = Path(path.strip()).expanduser().resolve()
        if not p.exists():
            return f"Soubor/složka neexistuje: {path}"

        stat = p.stat()
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
        created  = datetime.fromtimestamp(stat.st_ctime).strftime("%d.%m.%Y %H:%M")

        if p.is_dir():
            try:
                items = list(p.iterdir())
                total_size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                info = (
                    f"Složka: {p.name}\n"
                    f"Cesta: {p}\n"
                    f"Položky: {len(items)}\n"
                    f"Celková velikost: {total_size/1024**2:.1f} MB\n"
                    f"Změněno: {modified}"
                )
            except Exception:
                info = f"Složka: {p}\nZměněno: {modified}"
        else:
            size = stat.st_size
            size_str = (f"{size/1024**3:.2f} GB" if size > 1024**3
                       else f"{size/1024**2:.1f} MB" if size > 1024**2
                       else f"{size/1024:.1f} KB" if size > 1024
                       else f"{size} B")
            info = (
                f"Soubor: {p.name}\n"
                f"Cesta: {p}\n"
                f"Velikost: {size_str}\n"
                f"Typ: {p.suffix or 'bez přípony'}\n"
                f"Změněno: {modified}\n"
                f"Vytvořeno: {created}"
            )
        return info
    except Exception as e:
        return f"Chyba: {e}"


def cmd_top_processes(limit: int = 10, sort_by: str = "cpu") -> str:
    """Top procesy podle CPU nebo RAM (výchozí top 10)."""
    limit = max(1, min(int(limit or 10), 50))
    sort_key = (sort_by or "cpu").strip().lower()
    by_ram = sort_key in ("ram", "memory", "mem")

    if not by_ram:
        psutil.cpu_percent(interval=0.3)

    rows: list[tuple[float, int, str]] = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            pid = int(info.get("pid") or 0)
            name = info.get("name") or "?"
            val = (
                float(info.get("memory_percent") or 0.0)
                if by_ram
                else float(info.get("cpu_percent") or 0.0)
            )
            rows.append((val, pid, name))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    rows.sort(key=lambda x: x[0], reverse=True)
    top = rows[:limit]
    if not top:
        return "Žádné procesy k zobrazení."

    label = "RAM" if by_ram else "CPU"
    lines = [f"Top {len(top)} procesů ({label}):"]
    for i, (val, pid, name) in enumerate(top, 1):
        lines.append(f"  {i}. {name} (PID {pid}) — {val:.1f}%")
    return "\n".join(lines)


def cmd_network_status() -> str:
    """Stav WiFi/sítě — nmcli na Linuxu, ip fallback."""
    import subprocess

    lines: list[str] = []

    if _IS_LINUX:
        nmcli = safe_run(["which", "nmcli"], timeout=3)
        if nmcli.get("rc") == 0:
            dev = safe_run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], timeout=5)
            if dev.get("stdout"):
                lines.append("📡 Zařízení (nmcli):")
                for raw in dev["stdout"].strip().splitlines():
                    parts = raw.split(":")
                    if len(parts) >= 3:
                        device, typ, state = parts[0], parts[1], parts[2]
                        conn = parts[3] if len(parts) > 3 else ""
                        extra = f" → {conn}" if conn and conn != "--" else ""
                        lines.append(f"  • {device} ({typ}): {state}{extra}")
            active = safe_run(
                ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                timeout=5,
            )
            if active.get("stdout"):
                lines.append("🔗 Aktivní připojení:")
                for raw in active["stdout"].strip().splitlines():
                    parts = raw.split(":")
                    if len(parts) >= 2:
                        lines.append(f"  • {parts[0]} ({parts[1]})" + (f" na {parts[2]}" if len(parts) > 2 else ""))
            wifi = safe_run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY", "dev", "wifi"], timeout=5)
            if wifi.get("stdout"):
                for raw in wifi["stdout"].strip().splitlines():
                    parts = raw.split(":")
                    if len(parts) >= 4 and parts[0] == "yes":
                        lines.append(f"📶 WiFi: {parts[1]} ({parts[2]}%, {parts[3]})")
                        break

    if not lines:
        link = safe_run(["ip", "-br", "link"], timeout=5)
        if link.get("stdout"):
            lines.append("🌐 Rozhraní (ip):")
            for raw in link["stdout"].strip().splitlines():
                lines.append(f"  • {raw}")
        route = safe_run(["ip", "route", "show", "default"], timeout=5)
        if route.get("stdout"):
            lines.append(f"🛣️ Výchozí brána: {route['stdout'].strip()}")

    if not lines:
        return "Nelze zjistit stav sítě (nmcli/ip nedostupné)."

    try:
        import socket
        host = socket.gethostname()
        lines.insert(0, f"🖥️ {host}")
    except Exception:
        pass

    return "\n".join(lines)


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
