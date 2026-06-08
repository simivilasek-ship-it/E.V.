# Contributing to JARVIS

Thank you for your interest! This document explains how to set up the dev environment and contribute.

## Quick setup

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git
cd Jarvis
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"          # installs dev + lint + test extras
pre-commit install               # ruff + eslint hooks
```

## Running tests

```bash
# Unit tests (fast, no external services needed)
pytest tests/ test_jarvis.py -q --timeout=30

# Integration tests (needs Ollama running)
pytest -m integration -q

# Frontend
cd web && npm ci && npm run lint && npm run build
```

## Code style

- **Python** — [ruff](https://docs.astral.sh/ruff/) for lint + format. Config in `pyproject.toml`.
- **TypeScript** — ESLint + Prettier. Config in `web/eslint.config.mjs`.
- Both are enforced as pre-commit hooks and in CI.

## Project layout

See [docs/CANONICAL.md](docs/CANONICAL.md) for the authoritative module ownership map.

Key locations:
| Path | Purpose |
|------|---------|
| `src/api/routers/` | FastAPI route handlers (~20 routers) |
| `jarvis.py` | CLI entry point |
| `jarvis_cli.py` | `jarvis log`, `jarvis release` subcommands |
| `config.py` | Central configuration (env vars → typed config) |
| `web/components/` | React/Next.js UI components |
| `tests/` | All automated tests |
| `scripts/` | Dev utilities (UTF-8 check, .deb packaging) |

## Submitting changes

1. Fork the repo and create a feature branch: `git checkout -b feat/my-feature`
2. Make changes, write tests, run `pytest` and `npm run build`
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
