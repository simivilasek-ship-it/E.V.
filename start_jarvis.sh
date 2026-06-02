#!/usr/bin/env bash
# JARVIS — spustí backend a otevře UI v prohlížeči
# Volby: --webview (nativní pywebview okno), --tray (tray ikona)
# Poznámka: --gui (Tkinter) byl odebrán; primární UI je Next.js / pywebview.

JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$JARVIS_DIR"

# Aktivace venv
if   [ -d "$JARVIS_DIR/venv" ];           then source "$JARVIS_DIR/venv/bin/activate"
elif [ -d "$HOME/Stažené/jarvis-env" ];   then source "$HOME/Stažené/jarvis-env/bin/activate"
else echo "Venv nenalezen — spusť: ./install.sh"; exit 1; fi

# Auto-start Ollama pokud neběží
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Spouštím Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

exec python jarvis.py "$@"
