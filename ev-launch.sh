#!/usr/bin/env bash
# E.V. — spustí server a otevře prohlížeč
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Zkontroluj jestli server už běží
if curl -s --max-time 1 http://localhost:8002/api/health > /dev/null 2>&1; then
    # Server běží — jen otevři prohlížeč
    xdg-open http://localhost:8002/app &
    exit 0
fi

# Spusť server na pozadí v terminálu
if command -v gnome-terminal &>/dev/null; then
    gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && ./start.sh; exec bash" &
elif command -v xterm &>/dev/null; then
    xterm -title "E.V." -e "cd '$SCRIPT_DIR' && ./start.sh; exec bash" &
elif command -v konsole &>/dev/null; then
    konsole --workdir "$SCRIPT_DIR" -e bash -c "./start.sh; exec bash" &
else
    bash "$SCRIPT_DIR/start.sh" &
fi

# Počkej až server nastartuje (max 30s)
for i in $(seq 1 30); do
    sleep 1
    if curl -s --max-time 1 http://localhost:8002/api/health > /dev/null 2>&1; then
        break
    fi
done

# Otevři prohlížeč
xdg-open http://localhost:8002/app &
