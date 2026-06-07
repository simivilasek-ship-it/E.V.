"""Unified JARVIS launcher — one command for backend + web UI."""
from __future__ import annotations

import argparse
import os
import signal
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from src.api.paths import ROOT

PID_FILE = Path.home() / ".jarvis" / "dashboard.pid"


def ensure_web_dist(*, force: bool = False) -> bool:
    """Build Next.js static export into web_dist/ when missing."""
    web_dist = ROOT / "web_dist"
    if not force and (web_dist / "index.html").is_file():
        return True

    web_dir = ROOT / "web"
    if not web_dir.is_dir():
        print("⚠ Složka web/ neexistuje — UI nebude dostupné.")
        return False

    if shutil.which("npm") is None:
        print("⚠ npm není v PATH — nainstaluj Node.js pro webové UI.")
        return False

    print("==> Sestavuji frontend (první spuštění trvá ~1 minutu)...")
    try:
        subprocess.run(
            ["bash", str(ROOT / "scripts" / "build.sh")],
            cwd=ROOT,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"⚠ Build frontendu selhal (exit {exc.returncode}).")
        return False

    ok = (web_dist / "index.html").is_file()
    if ok:
        print("==> Frontend připraven.")
    return ok


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _port_owner_pid(port: int) -> int | None:
    """Return PID listening on TCP port, or None."""
    if shutil.which("ss"):
        try:
            r = subprocess.run(
                ["ss", "-tlnp", f"sport = :{port}"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            import re

            for line in r.stdout.splitlines():
                m = re.search(r"pid=(\d+)", line)
                if m:
                    return int(m.group(1))
        except Exception:
            pass
    if shutil.which("lsof"):
        try:
            r = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            for line in r.stdout.strip().splitlines():
                if line.strip().isdigit():
                    return int(line.strip())
        except Exception:
            pass
    if shutil.which("fuser"):
        try:
            r = subprocess.run(
                ["fuser", f"{port}/tcp"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            for tok in (r.stdout + r.stderr).split():
                if tok.isdigit():
                    return int(tok)
        except Exception:
            pass
    return None


def _read_pid_file() -> int | None:
    try:
        raw = PID_FILE.read_text().strip()
        pid = int(raw)
        if pid > 0:
            return pid
    except (OSError, ValueError):
        pass
    return None


def _write_pid_file() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _remove_pid_file() -> None:
    try:
        if PID_FILE.is_file() and int(PID_FILE.read_text().strip()) == os.getpid():
            PID_FILE.unlink()
    except (OSError, ValueError):
        pass


def _kill_graceful(pid: int, timeout: float = 10.0) -> bool:
    """Send SIGTERM, wait, then SIGKILL if needed."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        print(f"⚠ Nemám oprávnění ukončit PID {pid}")
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.25)
        except ProcessLookupError:
            return True

    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.3)
    except ProcessLookupError:
        pass
    return True


def _restart_from_pid_file() -> None:
    pid = _read_pid_file()
    if pid is None:
        print("==> Žádný PID soubor — pokračuji čistým startem.")
        return
    print(f"==> Ukončuji předchozí JARVIS (PID {pid})…")
    if not _kill_graceful(pid):
        owner = _port_owner_pid(8002)
        if owner:
            print(f"==> Zkouším PID z portu: {owner}")
            _kill_graceful(owner)
    time.sleep(0.5)
    try:
        if PID_FILE.is_file():
            PID_FILE.unlink()
    except OSError:
        pass


def _free_port(port: int) -> None:
    owner = _port_owner_pid(port)
    if owner:
        print(f"==> Port {port} obsazen PID {owner} — ukončuji…")
        _kill_graceful(owner)
        time.sleep(0.5)
        return
    if shutil.which("fuser"):
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
        time.sleep(0.5)


def _open_browser(url: str, delay: float = 1.2) -> None:
    def _go() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_go, daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="JARVIS — backend + web UI")
    parser.add_argument("--port", type=int, default=8002, help="HTTP port (default: 8002)")
    parser.add_argument("--no-open", action="store_true", help="Neotevírat prohlížeč")
    parser.add_argument("--no-build", action="store_true", help="Nespouštět build frontendu")
    parser.add_argument("--rebuild", action="store_true", help="Vynutit rebuild web_dist/")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Ukončit proces z ~/.jarvis/dashboard.pid a spustit znovu",
    )
    args = parser.parse_args(argv)

    if args.restart:
        _restart_from_pid_file()
        if _port_in_use(args.port):
            _free_port(args.port)
    elif _port_in_use(args.port):
        owner = _port_owner_pid(args.port)
        url = f"http://localhost:{args.port}/app"
        if owner:
            print(f"⚠ Port {args.port} už běží (PID {owner}) → {url}")
        else:
            print(f"⚠ Port {args.port} už běží → {url}")
        print(f"  Pro restart: python3 dashboard.py --restart")
        return

    if not args.no_build:
        ensure_web_dist(force=args.rebuild)

    from src.api.app import mount_web_app, run_dashboard

    mount_web_app()

    url = f"http://localhost:{args.port}/app"
    _write_pid_file()

    def _on_exit(*_a) -> None:
        _remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_exit)
    signal.signal(signal.SIGINT, _on_exit)

    print(f"JARVIS ready {url}")
    if not args.no_open:
        _open_browser(url)

    try:
        run_dashboard(port=args.port)
    finally:
        _remove_pid_file()

