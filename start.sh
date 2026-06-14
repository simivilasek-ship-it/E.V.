#!/usr/bin/env bash
# JARVIS — jeden příkaz pro spuštění
# Automaticky nainstaluje vše co chybí a spustí server.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
info() { echo -e "  → $1"; }
warn() { echo -e "${YELLOW}  ! $1${NC}"; }

echo ""
echo "  🤖  JARVIS"
echo ""

# ── 1. Python ────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "  ✗ Python 3.11+ není nainstalován."
    echo "    Ubuntu/Debian:  sudo apt install python3.11"
    echo "    Fedora:         sudo dnf install python3.11"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MINOR" -lt 11 ] 2>/dev/null; then
    echo "  ✗ Vyžadován Python 3.11+, nalezena verze $PY_VER"
    exit 1
fi

# ── 2. Virtualenv (pokud neexistuje, spusť install.sh) ───────────────────────
if [ ! -f "venv/bin/activate" ]; then
    warn "Prostředí venv nenalezeno — spouštím install.sh..."
    echo ""
    bash "$SCRIPT_DIR/install.sh"
    echo ""
fi

source venv/bin/activate

# ── 3. Ollama daemon ─────────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
        info "Spouštím Ollama na pozadí..."
        ollama serve &>/dev/null &
        sleep 2
    fi
fi

# ── 4. Bezpečnost — generuj token pokud bind != localhost ────────────────────
BIND_HOST="${JARVIS_BIND_HOST:-127.0.0.1}"
if [ "$BIND_HOST" != "127.0.0.1" ] && [ "$BIND_HOST" != "localhost" ]; then
    if ! grep -q "JARVIS_API_TOKEN" .env 2>/dev/null; then
        warn "Bind na $BIND_HOST bez tokenu — generuji API token..."
        source venv/bin/activate
        python3 scripts/generate_token.py --write 2>/dev/null && ok "API token vygenerován do .env" || \
            warn "Token se nepodařilo vygenerovat — spusť: python scripts/generate_token.py --write"
    fi
fi

# ── 5. Spuštění JARVIS ───────────────────────────────────────────────────────
info "Spouštím JARVIS → http://localhost:8002/app"
echo ""
exec python3 dashboard.py "$@"
