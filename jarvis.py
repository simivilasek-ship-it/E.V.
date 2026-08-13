"""
E.V. — hlavní vstupní bod
Výchozí: spustí backend + otevře prohlížeč na http://localhost:8002/app
"""

from config import __version__


def _check_setup() -> None:
    """Zkontroluje závislosti a upozorní na chybějící."""
    import shutil
    missing = []
    if not shutil.which("ollama"):
        missing.append("ollama (https://ollama.com)")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (sudo apt install ffmpeg)")
    if not shutil.which("node"):
        missing.append("Node.js 18+ (pro MCP servery)")
    if missing:
        print("\n⚠️  Chybí závislosti:")
        for m in missing:
            print(f"   • {m}")
        print("   Spusť: ./install.sh\n")


def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "log":
        from jarvis_cli import cmd_log
        raise SystemExit(cmd_log(sys.argv[2:]))

    if len(sys.argv) > 1 and sys.argv[1] == "release":
        from jarvis_cli import cmd_release
        raise SystemExit(cmd_release(sys.argv[2:]))

    if len(sys.argv) > 1 and sys.argv[1] == "config":
        from jarvis_cli import cmd_config_validate
        raise SystemExit(cmd_config_validate(sys.argv[2:]))

    import argparse
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description=f"E.V. v{__version__} — lokální AI asistent",
    )
    parser.add_argument("--gui",       action="store_true",
                        help="[LEGACY] Tkinter GUI (deprecated; výchozí je Next.js web UI na /app)")
    parser.add_argument("--webview",   action="store_true",
                        help="Nativní pywebview okno (místo prohlížeče)")
    parser.add_argument("--tray",      action="store_true",
                        help="Minimalizovat do systémového traye")
    parser.add_argument("--dashboard", action="store_true",
                        help="Spustit pouze backend bez otevírání UI")
    parser.add_argument("--setup",     action="store_true",
                        help="Průvodce prvního spuštění")
    parser.add_argument("--version",   action="version",
                        version=f"E.V. {__version__}")
    args = parser.parse_args()

    if args.setup:
        import setup_wizard
        setup_wizard.run()
        return

    if args.dashboard:
        import dashboard
        dashboard.run()
        return

    if args.gui:
        # --gui příznak ponechán pro zpětnou kompatibilitu,
        # ale Tkinter okno bylo nahrazeno headless backendem.
        # Použij výchozí launcher (Next.js + dashboard) pro webové UI.
        print(f"E.V. v{__version__} — příznak --gui je deprecated, spouštím headless backend.")
        print("Webové UI: http://localhost:8002/app  (spusť: cd web && npm run dev)")
        import dashboard
        dashboard.run()
        return

    # Výchozí: web launcher — backend + prohlížeč
    import sys
    if args.webview:
        sys.argv.append("--webview")
    if args.tray:
        sys.argv.append("--tray")

    from desktop.launcher import main as _launch
    _launch()


if __name__ == "__main__":
    main()
