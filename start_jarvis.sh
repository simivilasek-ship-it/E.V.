#!/usr/bin/env bash
# Spouštěč JARVIS — aktivuje venv a spustí aplikaci
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/Stažené/jarvis-env"

# Spusť Ollama na pozadí pokud neběží
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

# Aktivuj venv a spusť JARVIS
source "$VENV/bin/activate"
cd "$SCRIPT_DIR"
python jarvis.py
