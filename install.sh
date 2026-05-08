#!/usr/bin/env bash
set -e

echo "============================================"
echo "  JARVIS v2.0 — Instalace (Linux/Mac)"
echo "============================================"
echo

echo "[1/4] Aktualizuji pip..."
python3 -m pip install --upgrade pip --quiet

echo "[2/4] Systémové závislosti pro PyAudio..."
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y portaudio19-dev python3-pyaudio espeak espeak-ng 2>/dev/null || true
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm portaudio espeak-ng 2>/dev/null || true
elif command -v brew &>/dev/null; then
    brew install portaudio espeak 2>/dev/null || true
fi

echo "[3/4] Instaluji Python závislosti..."
pip3 install -r requirements.txt

echo "[4/4] Kontroluji Ollama..."
if ! command -v ollama &>/dev/null; then
    echo
    echo "============================================"
    echo "  POZOR: Ollama není nainstalovaná!"
    echo "  Instalace: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Poté spusť: ollama pull llama3.1:8b"
    echo "============================================"
else
    echo "Ollama nalezena. Stahuji model llama3.1:8b..."
    ollama pull llama3.1:8b
fi

echo
echo "============================================"
echo "  Hotovo! Spusť JARVIS příkazy:"
echo "    1. ollama serve"
echo "    2. python3 jarvis.py"
echo "============================================"
