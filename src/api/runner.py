"""Unified JARVIS launcher — one command for backend + web UI."""
from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from src.api.paths import ROOT


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


def _free_port(port: int) -> None:
    if not shutil.which("fuser"):
        return
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
    parser.add_argument("--restart", action="store_true", help="Ukončit starý proces na portu a spustit znovu")
    args = parser.parse_args(argv)

    if args.restart and _port_in_use(args.port):
        print(f"==> Port {args.port} obsazený — ukončuji starý proces...")
        _free_port(args.port)
    elif _port_in_use(args.port):
        print(f"⚠ Port {args.port} už běží → http://localhost:{args.port}/app")
        print(f"  Pro restart: python3 dashboard.py --restart")
        return

    if not args.no_build:
        ensure_web_dist(force=args.rebuild)

    from src.api.app import mount_web_app, run_dashboard

    mount_web_app()

    url = f"http://localhost:{args.port}/app"
    print(f"JARVIS → {url}")
    print("         API + WebSocket na stejném portu")
    if not args.no_open:
        _open_browser(url)

    run_dashboard(port=args.port)
