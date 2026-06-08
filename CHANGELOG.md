# CHANGELOG

## [5.7.0] - 2026-06-08

### Added — Work Timeline + Memory
- `activity_store.py` — SQLite append-only log pracovní aktivity (`~/.jarvis/activity.db`)
- `activity_collector.py` — sledování aplikací, git commitů, Docker kontejnerů
- `activity_bridge.py` — EventBus → ActivityStore → WebSocket feed
- `missions.py` — Mission Control checklist (doplňuje `mission_manager.py`)
- `src/api/routers/activity.py` — API `/api/activity/*`, `/api/workspace`, `/api/proactive`, `WS /ws/activity`
- UI komponenty v `web_vite_backup/`: `WorkTimeline`, `ActivityFeed`, `MissionControl`

### Added — Proaktivní AI
- CPU/RAM alerty → toast + návrh akce
- Docker RAM > 4 GB → alert s návrhem restartu
- 3× build fail → návrh GitHub issue

### Changed
- `context_orchestrator.py` — workspace bundle (git + docker + nedávná aktivita)
- `DailySummarizer` zahrnuje i pracovní aktivitu z Work Timeline
- `memory.py` emituje `MEMORY_STORED` přes EventBus
- `src/api/lifespan.py` spouští ActivityCollector + ActivityBridge

### Tests
- `tests/test_activity.py` — ActivityStore, MissionStore, ActivityBridge

---

## [5.6.0] - 2026-06-07

### Added
- **Onboarding wizard** — first-run checks: Ollama, snap, microphone (`OnboardingWizard.tsx`, `GET /api/onboarding`)
- **Install UX** — progress bar in chat (0→100 %), cancel button, structured snap/pkexec errors
- **E2E tests** — `tests/test_e2e_real.py` (WS chat, audio, install, context)
- **README gallery** — dashboard screenshot + demo GIF; WHY sentence; Who is it for; short quickstart

### Changed
- **Canonical module tree** — root modules are source of truth; duplicate `src/*` implementations removed (`docs/CANONICAL.md`)
- **Secure defaults** — `api_bind_host: 127.0.0.1`; Docker Compose enables `JARVIS_API_AUTH_REQUIRED=1`
- Verze **5.6.0** across `config.py`, `pyproject.toml`, Docker, requirements
- **563 tests** passing in CI

### Fixed
- Full test suite green: MCP bridge mocks, memory isolation, Chrome dual-launch, VAD `audioop` fallback (Python 3.13+)

---

## [5.5.0] - 2026-06-06

### Added
- **UI redesign** — DM Sans, glass panels, collapsible Advanced sidebar, hardware markdown
- **LAN API auth** — `JARVIS_API_AUTH_REQUIRED`, `JARVIS_API_TOKEN`, middleware in `src/api/middleware/auth.py`
- **Unified API pipeline** — `/api/chat`, `/ws/chat` via `process_chat()`; `/api/command` deprecated
- **Install events** — WebSocket progress via `event_bus` + `install_notify.py`

### Changed
- Verze **5.5.0**, README Linux-out-of-the-box section

---

## [5.4.0] - 2026-06-06

### Added
- **Web duplex voice** — `/ws/audio`: mic PCM16 → VAD → Whisper STT → unified chat → Edge-TTS playback v prohlížeči
- **Copilot tool-calling** — Ollama tools pro `open_app`, `weather`, `pc_overview`, …
- **UI**: ContextSidebar, mode badges, quick actions, proactive `GET /api/suggestions`
- **PC commands**: `top_processes`, `network_status`, `pc_overview`
- **Demo GIF** v README (`docs/demo.gif`, `scripts/generate_demo_gif.py`)
- Integrační testy `tests/test_unified_runtime.py` (11 testů)

### Changed
- Verze **5.4.0**, merge do `main`
- Agent plan preview v chatu, PID file pro `--restart`
- User memory: město, preferuji, oblíbené aplikace

---

## [5.3.0] - 2026-06-06

### Added
- **Unified runtime** — `src/api/runtime.py` + `src/api/runner.py`; web chat = stejný pipeline jako desktop
- **Copilot + Agent + PC Manager** — automatické tři režimy v `routing.py` (status v UI)
- **`pc_overview`** — kompletní přehled PC (CPU, RAM, disk, okna, top procesy)
- **`GET /api/context`** — živý kontext prostředí pro dashboard
- LocalRouter patterny: *co mám na obrazovce*, *přehled o PC*, počasí v Praze (CZ geocoding)

### Changed
- **Pořadí routingu:** LocalRouter má prioritu před MCP pluginy (čas, počasí bez „MCP není dostupný")
- **ContextOrchestrator** — hostname, OS, disk, RAM GB; Xlib fallback bez ewmh
- **SYSTEM_PROMPT** — Copilot/Gemini styl s vědomím o PC
- **Logging** — oprava crash při `{}` v log zprávách (`logging_setup.py`, `app_core.py`)
- `python3 dashboard.py --restart` — restart bez konfliktu portu 8002
- WebSocket chat: `chunk`, `agent_step`, `status`, `done`

### Fixed
- WebSocket 403 (chybějící `WebSocket` import v routerech)
- Screen describe halucinace — faktický popis z oken
- Plugin calculator nechytá „kolik je hodin"
- MCP Time fallback na lokální `get_time`

---

## [5.2.0] - 2026-06-06

### Added
- **Vision Sandbox** — dry-run náhled kliknutí (`vision_sandbox.py`, panel Alt+V, API `/api/vision/sandbox/*`)
- **Multi-agent mise** — režimy `single` | `multi` | `parallel` (`MissionPanel`, Alt+M)
- **Workflow UX** — zoom, snap grid, undo, duplikát, test run (`POST /api/workflows/graph/test`)

### Changed
- `VisualActionPlanner.locate()` — hledání bez kliknutí
- `mission_manager` — `agent_mode` sloupec v SQLite

---

## [5.1.0] - 2026-06-06

### Added
- **Fáze 2 — produkční kvalita**
- `src/api/routers/*` — rozdělený FastAPI backend (17 router modulů)
- **Audit log panel** v Nastavení (`AuditLogPanel.tsx`, `GET /api/audit?limit=`)
- CI **coverage gate ≥70 %**

### Changed
- `dashboard.py` → tenký shim nad `src/api/app.py`
- `GET /` přesměrovává na `/app` (legacy HTML dashboard odstraněn)
- `pyproject.toml` — balíček `src*`

### Removed
- `gui_legacy/` — nepoužívaná duplicita Tkinter GUI
- `templates/dashboard.html` — nahrazeno Next.js UI
- `src/api/dashboard.py` — stará duplicitní kopie

---

## [5.0.1] - 2026-06-06

### Added
- **Web confirmation modal** — ELEVATED/RESTRICTED akce čekají na schválení v prohlížeči (`/ws/confirm`, `ConfirmModal.tsx`)
- **Voice input v chatu** — tlačítko mikrofonu přes Web Speech API (Chrome)
- **V2 UI zapojeno** — `AgentGraphV2`, `PluginMarketplace`, `WorkflowEditor` (Alt+0) v hlavní navigaci
- `confirmation_bridge.py` + testy `tests/test_confirmation_bridge.py`

### Changed
- Verze sjednocena na **5.0.0** (`config.py`, `pyproject.toml`)
- `audio_ws_enabled` default `true` (VAD websocket připraven pro duplex)
- Dokumentace aktualizována (`README`, `web/README`, `docs/`)

### Security
- Headless režim: pokud je připojen web klient, `confirm_action()` čeká na UI místo tichého zamítnutí

---

## [5.0] - 2026-06-03

### Added

**Hybridní Cloud Router (`cloud_router.py`)**
- Groq LLaMA 3.1/3.3 + OpenRouter routing — komplexní dotazy odpovídají za ~200 ms
- Automatický fallback: Groq → OpenRouter → Ollama (lokálně)
- Streaming podpora, konfigurace přes GROQ_API_KEY / OPENROUTER_API_KEY v .env

**Vision-Guided Computer Use (`vision_computer_use.py`, `vision_v2.py`)**
- `VisionAgent.smart_click()` — OCR-first (~50 ms), LLaVA fallback (~2 s)
- `RealTimeScreenMonitor` — 1 FPS capture, pixel diff detekce změn
- `VisionOCRPipeline` — pytesseract OCR + OpenCV button/input/label klasifikace
- `VisualActionPlanner` — fuzzy OCR match → koordináty pro klikání
- `VisionAgent.run_task()` — autonomní ReAct smyčka pro UI úkoly

**GraphRAG Paměť (`graph_extractor.py`)**
- Automatická extrakce entit+relací z každé konverzace (regex + LLM)
- SQLite knowledge graph s vektory pro sémantické hledání
- Kontext grafu injektován do každého LLM dotazu

**Autonomní Background Workers (`autonomous_workers.py`)**
- Email (IMAP), Git, Calendar (iCal), Slack, GitHub monitoring
- Proaktivní notifikace s LLM shrnutím důležitých událostí
- Konfigurovatelný interval, filtrování podle urgence

**Whisper Live Duplex Audio (`whisper_live.py`)**
- Real-time STT: WebRTC VAD → Groq Whisper (~200 ms) nebo faster-whisper
- Barge-in podpora — přerušení TTS uprostřed věty
- Edge-TTS streaming s podporou přerušení

**Mission Manager (`mission_manager.py`)**
- LLM rozdělí long-term úkol na kroky s due_date přes více dní
- Background executor (každých 15 min via Scheduler)
- Evaluace výsledku po dokončení (success/partial/failed)
- REST API: GET/POST/PUT/DELETE /api/missions

**Plugin Marketplace v2 (`plugin_marketplace.py`, `PluginMarketplace.tsx`)**
- `run_sandboxed()` — subprocess isolation, ulimit (memory+CPU), timeout
- `submit_review()` — hodnocení s komentáři, persistováno do JSON
- `start_update_checker()` — background thread s notifikacemi
- React UI: katalog, filtry, install/uninstall, hvězdičkové hodnocení

**Workflow Editor (`WorkflowEditor.tsx`)**
- Canvas SVG drag & drop editor — trigger/condition/action/delay/notify bloky
- Bezier propojování uzlů, Save/Load REST API, Export/Import JSON
- Dynamické editační fieldy dle typu bloku

**Agent Graph v2 (`AgentGraphV2.tsx`)**
- Animované hrany s pohyblivými tečkami (strokeDashoffset animate)
- Reasoning chain panel: 🤔 Thought / 🔧 Action / 👁️ Observation / ✅ Result
- Node pass-count badges, step counter, debug panel s raw JSON
- Timeline posledních 30 minut

**LLM Router v2.1 (`llm_router.py`)**
- `_score_model()` — rankovanie kandidátů dle cost_score + průměrné latence + error rate
- `get_model_for_task()` — výběr nejlepšího dostupného modelu (ne jen prvního matching)

**AgentGraph hover efekty (`AgentGraph.tsx`)**
- Glassmorphism-style fills při hover/active stavech
- Glow efekty, plynulejší animace, pointer cursor

### Performance
- VRAM agresivní uvolňování po každém LLaVA volání (`keep_alive=0`)
- WebSocket ConnectionManager — thread-safe, čistí mrtvá spojení v `finally`
- `ws_chat` stream přesunut do thread poolu přes `run_in_executor` + `asyncio.Queue`
- SQLite indexy: `last_access`, `access_score` přidány do memories
- Background auto-pruning přes Scheduler (každou hodinu, non-blocking)

### Security
- Shell command blacklist: 30+ regex patternů (rm -rf /, dd, mkfs, reverse shell...)
- Shell whitelist: pouze explicitně povolené prefixy (git, pip, ls, ...)
- `check_shell_command()` integrován do SecurityManager pro shell/mcp_tool akce

### Documentation
- Vytvořen `docs/` adresář s kompletní dokumentací:
  - `architecture.md` — systémová architektura, moduly, datové toky
  - `api-reference.md` — všechny REST + WebSocket endpointy
  - `configuration.md` — kompletní reference všech konfiguračních klíčů
  - `plugin-development.md` — průvodce vývojem pluginů
  - `agents.md` — ReAct, Graf, Hierarchical, Mission agenti
  - `memory.md` — paměťový systém, GraphRAG, embeddingy
  - `vision-computer-use.md` — vision pipeline, computer use

---

## [unreleased] - Memory Graph MVP

### Added
- SQLite-backed Memory Graph (entities + relations) with timestamps, source and confidence.
- Heuristic extractor + GraphStore integration in JarvisMemory (writes triplets to memory_data/memory_graph.db).
- Dashboard integration: /api/memory/graph includes graph entities and relations in UI.
- Tests: basic unit tests for graph store and retriever.

---

## [4.6] - 2026-06-02

### Added
- ProactiveEngine: context-aware triggers that monitor active window (VS Code) and suggest continuation tasks (scan TODO/FIXME, recent failures, git summary).
- Daily markdown summaries: automatic per-day report saved to ~/jarvis_reports/YYYY-MM-DD.md with commits and recent events.
- Unit tests covering headless confirm behavior and proactive features.

### Changed
- Security: headless mode no longer auto-approves ELEVATED actions. Introduced env var JARVIS_HEADLESS_APPROVE_ELEVATED to allow explicit override.
- README: documented headless security behavior and proactive feature notes.

### Fixed
- Integrations: ProactiveEngine integrated with EventBus, NotificationEngine and Scheduler.


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
