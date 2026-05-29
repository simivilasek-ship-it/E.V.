"""
Backward-compat shim — JARVIS API je nyní integrováno v dashboard.py (port 8002).
Tento soubor spouští dashboard jako standalone (port 8001 přesměrován → 8002).
"""
from dashboard import app, run_dashboard as run_api, run_dashboard_background as run_api_background  # noqa: F401

if __name__ == "__main__":
    print("JARVIS API → http://localhost:8002/docs (přesunuto do dashboard.py)")
    run_api(port=8001)
