#!/bin/bash
# JARVIS Desktop App — spouštěč
set -e

cd "$(dirname "$0")"

# Aktivuj virtualenv
if [ -f ~/Stažené/jarvis-env/bin/activate ]; then
    source ~/Stažené/jarvis-env/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Sestav React frontend pokud je novější než web_dist
if [ -d web ] && [ web/src -nt web_dist/index.html 2>/dev/null ] || [ ! -f web_dist/index.html ]; then
    echo "Sestavuji React frontend..."
    cd web && npm install --legacy-peer-deps -s && npm run build -s && cd ..
fi

# Spusť Ollama pokud neběží
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Spouštím Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

echo "Spouštím JARVIS Desktop..."
exec python app_desktop.py "$@"
