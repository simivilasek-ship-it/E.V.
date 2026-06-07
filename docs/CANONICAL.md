# Canonical module layout

At runtime, **root-level modules are canonical**. The app is started from the repository root (`app_core.py`, `dashboard.py`, tests, CLI), so imports like `from routing import CommandRouter` resolve to the top-level files.

`src/` is a **partial migration** toward a package layout. Some subsystems already live under `src/` (e.g. `src/api/`, `src/agents/`), but several core modules still exist in both places. Until migration is complete, treat the root copy as source of truth and avoid editing or importing stale `src/` duplicates.

## Key module pairs

| Canonical (root) | Partial copy (`src/`) | Notes |
|------------------|----------------------|-------|
| `routing.py` | *(removed — was orphan)* | `CommandRouter`, web chat pipeline |
| `local_router.py` | `src/llm/local_router.py` | Regex/fuzzy local command handling |
| `llm.py` | `src/llm/llm.py` | `LLMEngine`, Ollama/cloud inference |
| `app_core.py` | *(no `src/` copy)* | GUI lifecycle, wires routers and executor |

When adding features or fixing bugs in these areas, change the **root** file unless you are explicitly continuing the `src/` migration.
