"""
JARVIS — Desktop aplikace
Ovládá celý počítač hlasem nebo textem.
"""

from config import __version__


def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description=f"JARVIS v{__version__} — lokální AI asistent",
    )
    parser.add_argument("--setup", action="store_true",
                        help="Spustit průvodce prvního spuštění")
    parser.add_argument("--dashboard", action="store_true",
                        help="Spustit pouze web dashboard (localhost:8002)")
    parser.add_argument("--version", action="version",
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

    from app_core import JarvisApp
    print(f"JARVIS v{__version__}")
    JarvisApp().run()


if __name__ == "__main__":
    main()
