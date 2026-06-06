"""
JARVIS — Web Dashboard (backward-compatible entrypoint).

Implementation lives in src/api/.
"""
from src.api.app import app, run, run_dashboard, run_dashboard_background

__all__ = ["app", "run", "run_dashboard", "run_dashboard_background"]

if __name__ == "__main__":
    run_dashboard()
