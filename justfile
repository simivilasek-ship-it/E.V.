set dotenv-load := true

@default:
  just start

# Jeden příkaz — backend + UI na http://localhost:8002/app
start:
  python3 dashboard.py

backend:
  python3 -m pip install -r requirements.txt
  python3 dashboard.py --no-open

# Volitelně: Next.js HMR (dva procesy, jeden skript)
dev-hmr:
  bash scripts/dev.sh

web-dev:
  cd web && npm ci && npm run dev

web-lint:
  cd web && npm run lint

web-typecheck:
  cd web && npm run typecheck

web-build:
  bash scripts/build.sh

python-lint:
  ruff check .
  ruff format --check .

python-test:
  python3 -m pytest tests/ test_jarvis.py -v

docker-build:
  docker build -t jarvis:local .

