#!/usr/bin/env bash
# Spouštěč JARVIS v3.0 — aktivuje venv a spustí web server
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/Stažené/jarvis-env"

# Spusť Ollama na pozadí pokud neběží
if ! pgrep -x "ollama" > /dev/null; then
    echo "Spouštím Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

# Aktivuj venv a spusť server
source "$VENV/bin/activate"
cd "$SCRIPT_DIR"
echo "  JARVIS v3.0 — http://localhost:8000"
python server.py
