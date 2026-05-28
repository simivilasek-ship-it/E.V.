#!/usr/bin/env bash
# JARVIS v4.3 — Launcher

JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Aktivace venv — hledáme lokální venv nebo starý jarvis-env
if [ -d "$JARVIS_DIR/venv" ]; then
    source "$JARVIS_DIR/venv/bin/activate"
elif [ -d "$HOME/Stažené/jarvis-env" ]; then
    source "$HOME/Stažené/jarvis-env/bin/activate"
else
    echo "Venv nenalezen. Spusť: ./install.sh"
    exit 1
fi

cd "$JARVIS_DIR"

# Auto-start Ollama pokud neběží
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Spouštím Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

# Dashboard na pozadí (port 8002) pokud není spuštěný
if ! curl -s --max-time 1 http://localhost:8002/ > /dev/null 2>&1; then
    nohup python dashboard.py > /tmp/jarvis_dashboard.log 2>&1 &
    sleep 1
    echo "Dashboard: http://localhost:8002"
fi

echo "Spouštím JARVIS..."
exec python jarvis.py "$@"

# Web frontend (React)
if command -v npm &>/dev/null && [ -d "web" ]; then
  echo "Spouštím JARVIS Web UI na http://localhost:3000"
  cd web && npm run dev &>/dev/null &
  cd ..
fi
