# Contributing to JARVIS

## Quick start for contributors

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis
./install.sh
source venv/bin/activate
pytest tests/ -x -q  # run tests
cd web && npm run test:unit  # frontend tests
```

## Project structure

| Directory | Purpose |
|-----------|---------|
| `src/api/` | FastAPI backend — routers, lifespan, middleware |
| `src/` | Core modules (doc_ingestion, morning_briefing, config_schema) |
| `web/` | Next.js 16 frontend |
| `tests/` | Python tests (pytest) |
| `web/__tests__/` | Frontend tests (Vitest + RTL) |
| `router/` | Local command router domain modules |
| `plugins/` | Plugin system + built-in skills |
| `commands/` | Command executors |
| `docs/` | Documentation |

## Adding a new feature

1. Backend endpoint → `src/api/routers/your_feature.py`
2. Register in `src/api/routers/__init__.py`
3. Tests → `tests/test_your_feature.py`
4. Frontend panel → `web/components/YourPanel.tsx`
5. Add to Sidebar in `web/components/Sidebar.tsx`

## Code style

- Python: ruff format + ruff lint (CI enforced)
- TypeScript: ESLint + Prettier
- Commits: conventional commits (`feat:`, `fix:`, `docs:`)

## Running CI locally

```bash
ruff check . && ruff format --check .
mypy src/ --ignore-missing-imports
pytest tests/ --cov=. --cov-fail-under=70
cd web && npm run lint && npm run test:unit && npm run build
```

## Submitting changes

1. Fork the repo and create a feature branch: `git checkout -b feat/my-feature`
2. Make changes, write tests, and run the CI checks above
3. Open a PR against `main` — CI will run lint, tests, Docker build
4. Reference any relevant issues in the PR description

## Release process

Use the built-in release assistant:

```bash
python jarvis.py release --bump patch --dry-run   # preview
python jarvis.py release --bump patch              # apply
```

This bumps the version, drafts a changelog entry, and prints the release checklist.

## Reporting bugs

Open a GitHub Issue with:
- OS and Python version (`python3 --version`)
- Steps to reproduce
- Output of `curl http://localhost:8002/api/health/check` (if backend-related)
