#!/usr/bin/env bash
# JARVIS v3.0 — Launcher
JARVIS_DIR="/home/simi/Stažené/nepojmenovaná složka"
VENV="$HOME/Stažené/jarvis-env"

# Auto-start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "Spouštím Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

source "$VENV/bin/activate"
cd "$JARVIS_DIR"

# Dashboard na pozadí (port 8002)
if ! curl -s --max-time 1 http://localhost:8002/ > /dev/null 2>&1; then
    nohup python dashboard.py > /tmp/jarvis_dashboard.log 2>&1 &
    sleep 1
fi

python jarvis.py
