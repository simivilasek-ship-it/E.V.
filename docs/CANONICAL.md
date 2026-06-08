# Canonical module layout

At runtime, **root-level modules are canonical**. The app is started from the repository root (`app_core.py`, `dashboard.py`, tests, CLI), so imports like `from routing import CommandRouter` resolve to the top-level files.

`src/` holds the **web API package** (`src/api/`) and thin **namespace packages** that re-export from root. Duplicate implementations under `src/` were removed; only shims remain where external code still imports `src.<pkg>.<module>` directly.

## Layout

| Area | Canonical (root) | `src/` role |
|------|------------------|-------------|
| Routing / chat | `routing.py`, `local_router.py` | — |
| LLM | `llm.py`, `cloud_router.py`, `llm_router.py`, `prompt_tuner.py`, `router_dsl.py` | `src/llm/__init__.py` re-exports |
| Memory | `memory.py`, `memory_graph.py`, `graph_extractor.py`, `cache_manager.py`, `user_profile.py` | `src/memory/__init__.py` re-exports |
| Agents | `agent_*.py`, `agents.py`, `mission_manager.py`, `missions.py` | `src/agents/__init__.py` re-exports |
| Work Timeline | `activity_store.py`, `activity_collector.py`, `activity_bridge.py` | `src/api/routers/activity.py` |
| Workers | `event_bus.py`, `scheduler.py`, `proactive.py`, `autonomous_workers.py`, `notification_engine.py`, `workflow_engine.py` | `src/workers/__init__.py` re-exports; `context_suggestions.py` is src-only |
| Plugins | `mcp_bridge.py`, `plugin_system.py`, `mcp_hub.py`, `mcp_installer.py`, `plugin_marketplace.py` | — |
| Audio | `vad.py`, `tts.py`, `stt.py`, `whisper_live.py`, `duplex_audio.py`, `wake_word_detector.py` | `src/audio/vad.py` shim (API imports `src.audio.vad`) |
| Vision | `vision.py`, `vision_v2.py`, `vision_computer_use.py`, `computer_use.py`, `vision_pipeline.py` | `src/vision/__init__.py` re-exports |
| Security | `security_v2.py`, `shadow_mode.py` | `src/security/__init__.py` re-exports |
| App lifecycle | `app_core.py` | — |
| Web dashboard | `dashboard.py` | `src/api/` (FastAPI app, routers, runtime) |

## Shims

Only one duplicate path still exists as a file shim (direct `src.*` import elsewhere):

- `src/audio/vad.py` → `from vad import *`

## Rules

1. **Edit root** when changing core behavior (LLM, memory, agents, workers, plugins, audio, vision, security).
2. **Edit `src/api/`** for HTTP/WebSocket dashboard endpoints and web runtime wiring.
3. **Do not reintroduce** full copies under `src/`; use root modules or a one-line re-export shim if a `src.` import path must stay stable.
4. Package `__init__.py` files under `src/llm`, `src/memory`, `src/agents`, `src/workers`, `src/vision`, and `src/security` import from root — they are not alternate implementations.
