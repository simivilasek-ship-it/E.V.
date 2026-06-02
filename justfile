set dotenv-load := true

@default:
  just --list

backend:
  python -m pip install -r requirements.txt
  python dashboard.py

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
  python -m pytest tests/ test_jarvis.py -v

docker-build:
  docker build -t jarvis:local .

