#!/usr/bin/env bash
# JARVIS Desktop App — spouštěč
set -e
cd "$(dirname "$0")"

# ── Aktivuj venv ──────────────────────────────────────
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
elif [ -f ~/Stažené/jarvis-env/bin/activate ]; then
    source ~/Stažené/jarvis-env/bin/activate
else
    echo "Venv nenalezen — spusť: ./install.sh"
    exit 1
fi

# ── Závislosti ────────────────────────────────────────
pip install --quiet pywebview fastapi uvicorn 2>/dev/null || true

# GTK pro pywebview (pokud chybí)
if ! python -c "import gi" 2>/dev/null; then
    echo "Instaluji python3-gi (GTK backend pro pywebview)..."
    sudo apt-get install -y -qq python3-gi python3-gi-cairo \
        gir1.2-gtk-3.0 gir1.2-webkit2-4.1 2>/dev/null || \
    echo "  GTK se nepodařilo nainstalovat — použije se prohlížeč jako fallback"
fi

# ── Sestav React (pouze pokud je novější než build) ───
if [ -d web ] && { [ ! -f web_dist/index.html ] || \
    find web/src -newer web_dist/index.html -name "*.jsx" -o -name "*.js" -o -name "*.css" \
    2>/dev/null | grep -q .; }; then
    echo "Sestavuji React frontend..."
    (cd web && npm install --legacy-peer-deps -s 2>/dev/null && npm run build -s)
fi

# ── Spusť Ollama ─────────────────────────────────────
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "Spouštím Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

# ── Spusť JARVIS Desktop ─────────────────────────────
echo "Spouštím JARVIS Desktop..."
exec python app_desktop.py "$@"
