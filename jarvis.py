"""
JARVIS — hlavní vstupní bod
Výchozí: spustí backend + otevře prohlížeč na http://localhost:8002/app
"""

from config import __version__


def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description=f"JARVIS v{__version__} — lokální AI asistent",
    )
    parser.add_argument("--gui",       action="store_true",
                        help="Klasické Tkinter okno (místo webového UI)")
    parser.add_argument("--webview",   action="store_true",
                        help="Nativní pywebview okno (místo prohlížeče)")
    parser.add_argument("--tray",      action="store_true",
                        help="Minimalizovat do systémového traye")
    parser.add_argument("--dashboard", action="store_true",
                        help="Spustit pouze backend bez otevírání UI")
    parser.add_argument("--setup",     action="store_true",
                        help="Průvodce prvního spuštění")
    parser.add_argument("--version",   action="version",
                        version=f"JARVIS {__version__}")
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
        from app_core import JarvisApp
        print(f"JARVIS v{__version__} (Tkinter GUI)")
        JarvisApp().run()
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
