#!/usr/bin/env bash
# Spustí JARVIS backend a otevře UI v prohlížeči.
# Použití: bash scripts/start.sh [--webview] [--tray]
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source venv/bin/activate 2>/dev/null || true

python -m desktop.launcher "$@"
