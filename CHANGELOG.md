# CHANGELOG

## [4.2] - 2026-05-28

### Added
- Graf agent (Planner → Router → Executor → Critic) pro složité vícesvůlové úkoly.
- ReAct agent jako fallback pro méně složité vícesvůlové úkoly.
- TTS streaming — řeč přehrávána větu po větě, nečeká na celou odpověď.
- Neural memory systém (brain-inspired) s embeddingsy + TF-IDF fallback.
- DailySummarizer — denní extrakce faktů do UserProfile.
- LLM Router 2.0 — routing na různé modely podle typu úkolu (kód, překlad, math…).
- Plugin systém s manifest validací, sandbox importy a permission modelem.
- MCP Bridge pro integraci externích nástrojů (filesystem, brave, fetch, memory).
- Event Bus pro decoupled komunikaci mezi moduly.
- Background agenti (CPU/RAM/Disk monitoring) s alertingem.
- Wake word detektor.
- Security v2 — audit log, permission check, potvrzení nebezpečných akcí.
- Fuzzy matching příkazů (rapidfuzz) pro toleranci překlepů.
- Health check systém pro monitoring komponent.
- Offline mode s lokální znalostní bází.

### Changed
- `_process_command` refaktorován do `_try_fast_path` + `_run_llm_path` — lepší čitelnost.
- `quick_match` přejmenováno z `_quick_match` na veřejné API.
- Duplikát `_norm()` odstraněn z `agent_graph.py`, sdílena implementace z `llm.py`.
- Globální timeout 120s v graph agentu jako circuit breaker.
- Lazy imports těžkých modulů pro zkrácení startu o ~2–4s.

### Fixed
- `self.cmd` → `self.cmds` v `app_core.py` — ReAct a Graf agent dostávají správný executor.
- `AgentState.last_args: Dict[str, Any]` přidáno do dataclassu (chybělo typed pole).
- `health_check.py` — health check Ollamy testuje `/api/tags` (GET), ne `/api/chat` (POST).
- `offline_mode.py` — relativní cesty `.offline_queue.json` a `.offline_kb.json` → `Path(__file__).parent / ...`.
- `stt.py set_language()` — validuje oproti whitelistu 23 jazyků, vrací `False` pro neplatné.
- `.gitignore` — doplněny `jarvis.log`, `.offline_queue.json`, `venv/`, `pytest_cache/`.

## [2.0] - 2026-05-08

### Added
- Uživatelské rozhraní pro výběr Ollama modelu přímo v aplikaci.
- Automatické uložení vybraného modelu do `config.json`.
- Logování do souboru `jarvis.log` pro přehled chyb a provozu.
- Verze aplikace uvedena v `README.md`.
- Doporučení Python 3.11+ v `README.md`.

### Fixed
- Vylepšené UI označení pro uložený model.
