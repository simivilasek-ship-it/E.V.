#!/usr/bin/env bash
# Dev mode — backend na 8002, Next.js dev server na 3000 (s HMR).
# Použití: bash scripts/dev.sh
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source venv/bin/activate 2>/dev/null || true

echo "==> Spouštím backend (port 8002)..."
python3 -c "
import uvicorn, sys
sys.path.insert(0, '.')
from dashboard import app
uvicorn.run(app, host='127.0.0.1', port=8002, reload=True, log_level='info')
" &
BACKEND_PID=$!

echo "==> Spouštím Next.js dev server (port 3000)..."
cd "$ROOT/web"
npm run dev &
NEXT_PID=$!

echo ""
echo "  Backend  → http://localhost:8002"
echo "  Frontend → http://localhost:3000  (Next.js + HMR)"
echo ""
echo "  Ctrl+C pro zastavení obou serverů."

cleanup() {
  kill $BACKEND_PID $NEXT_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
