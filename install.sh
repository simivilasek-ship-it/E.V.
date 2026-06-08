#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
JARVIS_VERSION=$(python3 -c "from config import __version__; print(__version__)" 2>/dev/null || echo "5.4.0")
DEFAULT_MODEL="qwen2.5:3b"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ! $1${NC}"; }
err()  { echo -e "${RED}  ✗ $1${NC}"; }

echo "============================================"
echo "  JARVIS v${JARVIS_VERSION} — Instalace"
echo "============================================"
echo

# ── Python verze ──────────────────────────────
echo "[1/6] Kontrola Python..."
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    err "Vyžadován Python 3.11+, nalezena verze $PY_VER"
    echo "  Instalace: https://www.python.org/downloads/"
    exit 1
fi
ok "Python $PY_VER"

# ── Virtuální prostředí ───────────────────────
echo "[2/6] Virtuální prostředí..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "venv vytvořeno"
else
    ok "venv již existuje"
fi
source venv/bin/activate
python3 -m pip install --upgrade pip --quiet

# ── Systémové závislosti ──────────────────────
echo "[3/6] Systémové závislosti..."
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y -qq \
        portaudio19-dev python3-pyaudio espeak espeak-ng ffmpeg \
        tesseract-ocr tesseract-ocr-ces libnotify-bin 2>/dev/null || warn "Některé apt balíčky se nepodařilo nainstalovat (pokračuji)"
    ok "apt závislosti"
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm --needed portaudio espeak-ng ffmpeg tesseract 2>/dev/null || warn "Některé pacman balíčky selhaly"
    ok "pacman závislosti"
elif command -v brew &>/dev/null; then
    brew install portaudio espeak ffmpeg tesseract 2>/dev/null || warn "Některé brew balíčky selhaly"
    ok "brew závislosti"
else
    warn "Neznámý package manager — systémové závislosti přeskoč a nainstaluj ručně: portaudio, ffmpeg, tesseract"
fi

# ── Python balíčky ────────────────────────────
echo "[4/6] Python závislosti..."
pip install -r requirements.txt --quiet
ok "requirements.txt nainstalováno"

if python3 -c "import mcp" 2>/dev/null; then
    ok "mcp SDK (MCP servery)"
else
    echo "  Instaluji mcp SDK..."
    pip install mcp --quiet 2>/dev/null && ok "mcp nainstalován" || warn "mcp se nepodařilo nainstalovat — zkus ručně: pip install mcp"
fi

# Volitelné — doporučené
echo "  Instaluji doporučené balíčky (rapidfuzz, sentence-transformers)..."
pip install rapidfuzz sentence-transformers --quiet 2>/dev/null && \
    ok "rapidfuzz + sentence-transformers" || \
    warn "sentence-transformers se nepodařilo nainstalovat — paměť bude bez embeddings"

# ── Ollama ────────────────────────────────────
echo "[5/6] Ollama..."
if ! command -v ollama &>/dev/null; then
    warn "Ollama není nainstalovaná — stahuji..."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama nainstalována"
else
    ok "Ollama nalezena ($(ollama --version 2>/dev/null || echo 'verze neznámá'))"
fi

# Spusť Ollama daemon pokud neběží
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "  Spouštím ollama serve na pozadí..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Stáhni výchozí model
echo "  Stahuji model ${DEFAULT_MODEL}..."
if ollama pull "${DEFAULT_MODEL}" 2>/dev/null; then
    ok "Model ${DEFAULT_MODEL} připraven"
else
    warn "Model ${DEFAULT_MODEL} se nepodařilo stáhnout — zkus ručně: ollama pull ${DEFAULT_MODEL}"
fi

# ── Systemd (volitelné) ─────────────────────
echo "[6/6] Systemd user služba (volitelné)..."
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_DEST="$UNIT_DIR/jarvis.service"
if [ -f "desktop/jarvis.service" ]; then
    mkdir -p "$UNIT_DIR"
    sed "s|@JARVIS_DIR@|${SCRIPT_DIR}|g" desktop/jarvis.service > "$UNIT_DEST"
    ok "Unit zapsán → $UNIT_DEST"
    echo "    systemctl --user enable --now jarvis.service   # autostart"
    echo "    systemctl --user status jarvis.service"
    # Create config dir for .env
    mkdir -p "$HOME/.config/jarvis"
    if [ ! -f "$HOME/.config/jarvis/.env" ] && [ -f ".env" ]; then
        cp .env "$HOME/.config/jarvis/.env"
        ok ".env copiado a ~/.config/jarvis/.env"
    elif [ ! -f "$HOME/.config/jarvis/.env" ]; then
        echo "# JARVIS configuration" > "$HOME/.config/jarvis/.env"
        echo "# Run: python scripts/generate_token.py --write" >> "$HOME/.config/jarvis/.env"
        ok "Created empty ~/.config/jarvis/.env"
    fi
else
    warn "desktop/jarvis.service nenalezen — přeskočeno"
fi

# ── .env bootstrap ────────────────────────────
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    ok ".env criado a partir de .env.example — edite os valores"
fi

# ── Hotovo ────────────────────────────────────
echo
echo "============================================"
echo -e "  ${GREEN}Instalace dokončena!${NC}"
echo "============================================"
echo
echo "  Rychlý start:"
echo "    source venv/bin/activate"
echo "    python jarvis.py --setup   # průvodce prvního spuštění"
echo "    python dashboard.py        # http://localhost:8002/app"
echo
echo "  Work Timeline:"
echo "    python jarvis.py log --today"
echo "    python jarvis.py log --markdown --today"
echo "============================================"
