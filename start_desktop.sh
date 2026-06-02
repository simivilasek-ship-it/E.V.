#!/usr/bin/env bash
# JARVIS v4.4 Desktop — launcher
set -e
cd "$(dirname "$0")"

# Aktivuj venv
if   [ -f venv/bin/activate ];              then source venv/bin/activate
elif [ -f ~/Stažené/jarvis-env/bin/activate ]; then source ~/Stažené/jarvis-env/bin/activate
else echo "Venv nenalezen — spusť: ./install.sh"; exit 1; fi

# Závislosti pro web
pip install --quiet fastapi uvicorn 2>/dev/null || true

# Spusť Ollama
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Spouštím Ollama..."
    ollama serve &>/dev/null & sleep 2
fi

# Web build (jen pokud chybí)
if [ -d web ] && [ ! -f web_dist/index.html ]; then
    echo "Sestavuji web frontend..."
    bash scripts/build.sh
fi

echo "Spouštím JARVIS..."
exec python jarvis.py "$@"
