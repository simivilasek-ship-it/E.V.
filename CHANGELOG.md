# CHANGELOG

## [5.19.0] - 2026-06-14

### Added — 8.5/10 parity push
- **Swagger / ReDoc v dev módu** — `E.V._DEV=1` zapíná `/api/docs`, `/api/redoc`, `/api/openapi.json`; v produkci stále vypnuto
- **Simple/Advanced mode** — toggle v Sidebar skrývá pokročilé panely (Workflow, Missions, Agent…) pro nové uživatele
- **API contract testy** — `tests/test_api_contracts.py` pokrývá všechny registrované routery
- **Vitest 10+ nových testů** — WorkTimeline, DashboardPanel, VoicePanel, ErrorBoundary
- **src/ migrace** — `morning_briefing`, `doc_ingestion`, `config_schema` přesunuto do `src/` se zpětně-kompatibilními shimmy
- **CONTRIBUTING.md** — kompletní průvodce pro přispěvatele, struktura projektu, CI kroky
- **start.sh bezpečnost** — automatické generování API tokenu při bind na non-localhost

### Fixed
- `requirements.txt` header verze aktualizována na 5.19.0
- README verze badge aktualizován
- `docs/architecture.md` verze synchronizovány

### Changed
- Bump 5.18.0 → 5.19.0

## [5.18.0] - 2026-06-14

### Fixed — RAG + Voice + DnD
- **RAG do chatu** — `query_docs()` nyní volán v `llm._build_messages()` s user textem; relevantní pasáže z dokumentů injektovány do system promptu LLM
- **Voice config unifikace** — VoicePanel duplex toggle nyní posílá `audio_ws_enabled` + `duplex_audio_enabled` (oba klíče); eliminováno 3-klíčové peklo
- **VoicePanel reálné STT** — Web Speech API (SpeechRecognition) pro test tlačítko místo hardcoded REST; reálný AnalyserNode mic visualizer místo Math.random()
- **Drag & drop dokumenty** — `handleDrop` v ChatPanel nyní zpracovává PDF/DOCX/TXT (nejen obrázky); přetažení souboru = automatický upload do RAG
- **doc_ingestion chunking** — text dělen na 500-char chunks s 100-char překryvem; lepší relevance pro dlouhé dokumenty
- **doc_id content hash** — hash počítán z obsahu dokumentu (ne z temp cesty) → eliminovány duplicity při re-uploadu
- **Embedding re-ranking** — pokud je EmbeddingEngine dostupný, použije kosinusovou podobnost pro re-ranking

### Added
- `tests/test_doc_ingestion.py` — 7 testů pro RAG (ingest, dedup, query, delete, chunking, hash stabilita)

### Changed
- Bump 5.17.0 → 5.18.0

## [5.17.0] - 2026-06-09

### Fixed — UI↔API contract bugs
- **VoicePanel** — added `PATCH /api/settings`, `POST /api/chat/message`; health check now returns `voice` object (STT/TTS/duplex status)
- **WorkflowEditor** — fixed save/load schema mismatch; UI graph format now accepted and persisted by backend; `WorkflowEngine` callback wired to `CommandExecutor` in lifespan
- **PluginMarketplace** — fixed `NameError: Request not imported` crash on review submit
- **SkillGenerator** — now calls `reload_plugin()` after save; no restart needed
- **AgentGraph** — fixed node name mismatch (`planning/executing/routing` vs `planner/executor/router`)

### Added
- **Document ingestion + RAG** (`doc_ingestion.py`) — PDF, DOCX, TXT/MD ingestion; keyword RAG; context injection into LLM; `/api/docs/upload`, `/api/docs`, `/api/docs/query`, `/api/docs/{id}` endpoints
- **File upload in ChatPanel** — paperclip button to upload docs directly from chat; doc count badge
- **Responsive/mobile UI** — collapsible sidebar, hamburger menu, backdrop overlay, touch-friendly chat bubbles; `@media` breakpoints in `globals.css`
- **Morning briefing in web** — `schedule_briefing()` called in lifespan startup; `GET /api/briefing/today`; ChatPanel injects briefing on first open

### Changed
- `pypdf` + `python-docx` added as optional `[docs]` dependency group
- Bumped to `5.17.0`

## [5.16.0] - 2026-06-09

### Fixed
- **Memory conflict bug** — `store_with_conflict_check()` called `_conn()` which didn't exist on `_SQLiteMemoryStore`; fixed to use `_connect()` context manager — conflict resolution now works correctly
- **UTF-8 mojibake** — fixed corrupted Czech strings in `context_orchestrator.py` (`Schránka`, `Systém`) that were rendering garbled in LLM context

### Added
- **Daily morning briefing** (`morning_briefing.py`) — proactive `notify-send` briefing with yesterday's work summary, git dirty state, and day overview; `jarvis briefing` CLI command
- **Voice panel** (`web/components/VoicePanel.tsx`) — first-class voice UI: mic visualizer, STT/TTS status, duplex toggle, test phrase, graceful offline fallback; added to sidebar
- **Pydantic config schema** (`config_schema.py`) — `E.V.Settings` with grouped `VoiceSettings`, `SecuritySettings`, `AgentSettings`; `jarvis config validate` CLI
- **Router domain modules** (`router/`) — split 1034-line `local_router.py` into `constants.py`, `apps.py`, `media.py`, `system.py`, `memory_routes.py`; `moodle` site moved to user-overridable `custom_sites` config key
- **Vitest + RTL** — `web/vitest.config.ts`, `web/vitest.setup.ts`, `web/__tests__/SettingsPanel.test.tsx`, `web/__tests__/ChatPanel.test.tsx`; added to CI web job
- **Full-stack E2E** — Playwright now starts Python backend on `:8002` with `E.V._TEST_MODE=1`; tests cover API health, chat, confirm modal, settings; `data-testid` attrs on key components
- **Security startup warning** — `runner.py` prints visible banner when `api_auth_required=False` and host is not localhost
- **Memory conflict regression test** (`tests/test_memory_conflict.py`)
- **Keyboard shortcuts section** in README
- **Features at a Glance table** in README
- **Demo section** placeholder in README

### Changed
- Version bumped to `5.16.0` in `config.py`, `pyproject.toml`, README badge
- README test count badge updated to `730+`
- `custom_sites` config key: add your own site shortcuts in `config.json`

## [5.15.2] - 2026-06-08

### Changed — Complete design system unification
- **AgentGraphV2** — 61 hex colors → CSS vars; `color-mix()` for opacity tints; SVG attrs → `style={}`
- **PluginMarketplace** — 16 hex colors → CSS vars; category badges, status, stars, action buttons
- **MemoryGraph** — GROUP_COLORS, SVG edges/labels, detail panel → CSS vars
- **WorkTimeline, SettingsPanel, CenterDashboard, ActivityFeed, AuditLogPanel, SystemWidget, SkillGenerator** — remaining hex → CSS vars
- **Chat** — remark-gfm tables, Copilot-style markdown rendering, wider bubbles
- All 32 panels now use single design system; light theme works everywhere


## [5.15.0] - 2026-06-08

### Changed — Unified Design System
- **Single design system** — eliminated two competing visual languages (glass/indigo + retro HUD)
- **`globals.css`** — added `.panel`, `.panel-header`, `.panel-title`, `.arc-label`, `.arc-row`, `.btn-hud`, `.metric-badge`, `.skeleton`; CSS vars `--bg-hud`, `--text2`, `--border-hud`, `--metric-*`
- **`tailwind.config.ts`** — aligned with globals.css (matching colors, IBM Plex Mono as `hud` font)
- **DashboardPanel** — fully ported to CSS vars, `.panel` classes, skeleton loader, error states
- **SystemPanel** — fixed all undefined CSS classes; 24 `var(--font-hud)` refs → real font stack
- **HeroPanel** — status bar colors unified to CSS vars
- **WorkflowEditor** — node colors, toolbar, canvas, config panel all use CSS vars; SVG fills via `style={}`
- **AgentTimeline** — `color-mix()` for opacity tints; IBM Plex Mono throughout
- **MemoryGraph** — container/toolbar on CSS vars; graph SVG untouched
- **PluginMarketplace + SkillGenerator** — `S` style objects replaced with CSS vars
- Light theme now works across all panels


## [5.14.0] - 2026-06-08

### Added
- **Web panels hardened** — all panels have loading spinners, error states, backend-offline banners, auto-refresh
- **WorkTimeline.tsx** — rebuilt with refresh button, commit/build stats, markdown preview
- **MissionPanel.tsx** — error handling on list fetch and actions
- **SettingsPanel.tsx** — health check auto-refresh (60s), MCP warning banner, "Generovat token" button
- **DashboardPanel.tsx** — summary button shows loading state, catches errors
- **`POST /api/settings/generate-token`** — backend token generation endpoint
- **Docker hardening** — `cap_drop: ALL`, `no-new-privileges`, tmpfs, mem/CPU limits, Python healthcheck, jarvis_net network
- **Type annotations** — `project_profiles.py`, `config.py` fully typed; `py.typed` PEP 561 marker
- **`scripts/__init__.py`** — scripts importable as package
- **.env.example** — template with all documented env vars
- **README** — ASCII architecture diagram, screenshots panel table, Quick CLI reference
- **CONTRIBUTING.md** — full English contributor guide


## [5.13.0] - 2026-06-08

### Added / Changed
- (no new commits since last tag)


## [5.12.0] - 2026-06-08

### Added
- **Work Timeline → LLM context injection** — dnešní aktivita (commity, selhané buildy, projekty) se automaticky přidá do systém promptu
- **Project profiles** — auto-detekce git repo + jazyka; `/api/project` endpoint; injekce do kontextu
- **`jarvis release` CLI** — bumping verze, changelog draft, release checklist (`--bump patch/minor/major --dry-run`)
- **`scripts/make_deb.sh`** — Debian `.deb` packaging script
- **`gui_legacy/`** — Tkinter GUI přesunuto do legacy; `gui/` odstraněna
- **install.sh** — auto-instalace `mcp` SDK pokud chybí
- **`mcp>=1.0.0`** přidáno do hlavních závislostí v `pyproject.toml`


## [5.11.0] - 2026-06-08

### Added
- **`jarvis log --today`** — CLI přehled Work Timeline (`jarvis_cli.py`)
- **`GET /api/activity/report?format=md`** — denní markdown report
- **Alt+D** + tlačítko „Shrnutí dne" v dashboardu
- **Systemd user unit** — `desktop/jarvis.service`, instalace v `install.sh`
- **Desktop notifikace** pro proaktivní alerty (warning/error → `notify-send`)
- **UTF-8 CI gate** — `scripts/check_utf8.py`
- **MCP docs** — `docs/mcp-servers.md` (doporučená sada pro Linux)

### Fixed
- **`dashboard.py`** — obnoven `if __name__ == "__main__"` entrypoint
- **`memory.py`** — převedeno na UTF-8 (školní cp1250 export)
- **`install.sh`** — explicitní kontrola `mcp`, `libnotify-bin`, 6 kroků včetně systemd

### Changed
- Verze **5.11.0** sjednocena (`config.py`, `pyproject.toml`, Docker, requirements, README)
- Sidebar **v5.11 · Work OS**
- `.gitignore` — `.claude/`, `web_vite_backup/`

---

## [5.10.0] - 2026-06-08

### Added
- **E2E API testy** — `tests/test_e2e_api.py`, `api_client` fixture v `conftest.py`
- CI krok `Run E2E / integration API tests` (`pytest -m integration`)
- **Windows ActivityCollector** — `source/repos`, OneDrive, Documents, foreground process fallback
- `tests/test_collector_windows.py` — unit testy Windows paths a project inference

### Changed
- **Unified Mission DB** — checklisty (`missions.py`) migrovány do SQLite `missions.db` (`mission_type='checklist'`)
- `missions.py` je tenký shim nad `mission_manager.py`
- Autonomní mise (`/api/missions`) a checklisty (`/api/missions/checklist`) sdílí jednu DB, oddělené `mission_type`
- `activity_store.reset_activity_store()` + env `E.V._ACTIVITY_DB` pro izolované testy

---

## [5.9.0] - 2026-06-08

### Changed — sjednocení projektu
- **Jeden frontend** — odstraněn `web_vite_backup/` a lokální legacy `web/src/` (Vite)
- Smazány nepoužívané komponenty `AgentGraph.tsx`, `PluginStore.tsx`
- Mission Control sjednocen v dokumentaci a UI:
  - **Agent mise** (Alt+M) → `mission_manager.py` → `/api/missions`
  - **Release** (Alt+C) → `missions.py` → `/api/missions/checklist`
- `DELETE /api/missions/checklist/{id}` — smazání checklistu
- Odstraněn hardcoded seed „Release v5.0“ z `missions.py`

### Docs
- Všechny docs aktualizovány na v5.9 (`architecture`, `api-reference`, `agents`, `CANONICAL`, `web/README`)
- Diagram architektury: produkční UI na `:8002/app`, Work Timeline moduly

---

## [5.8.0] - 2026-06-08

### Added
- **Next.js UI parity** — `WorkTimeline`, `ActivityFeed`, `MissionChecklist` v primárním `web/`
- Sidebar taby: **Dnes**, **Feed**, **Checklist** (Alt+W/F/C)
- `jarvis.ts` — `connectActivity()`, `activityFeed`, `proactiveSuggestions`, `workSummary`
- Dashboard — dnešní přehled, proaktivní návrhy, live feed
- `src/api/routers/missions_checklist.py` — checklist API oddělené od agent missions
- Proaktivní akce — tlačítka volají chat příkazy (procesy, GitHub issue, Docker restart)
- `tests/test_activity_api.py` — integrační testy activity API

### Fixed
- WS activity broadcast race — `wire_activity_broadcaster()` v lifespan místo při importu
- Agent timeline schema — `/api/agent/timeline` vrací `answer`, `duration_ms`, `started_at`
- ActivityCollector shutdown při ukončení dashboardu

---

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
- **Secure defaults** — `api_bind_host: 127.0.0.1`; Docker Compose enables `E.V._API_AUTH_REQUIRED=1`
- Verze **5.6.0** across `config.py`, `pyproject.toml`, Docker, requirements
- **563 tests** passing in CI

### Fixed
- Full test suite green: MCP bridge mocks, memory isolation, Chrome dual-launch, VAD `audioop` fallback (Python 3.13+)

---

## [5.5.0] - 2026-06-06

### Added
- **UI redesign** — DM Sans, glass panels, collapsible Advanced sidebar, hardware markdown
- **LAN API auth** — `E.V._API_AUTH_REQUIRED`, `E.V._API_TOKEN`, middleware in `src/api/middleware/auth.py`
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
- Heuristic extractor + GraphStore integration in E.V.Memory (writes triplets to memory_data/memory_graph.db).
- Dashboard integration: /api/memory/graph includes graph entities and relations in UI.
- Tests: basic unit tests for graph store and retriever.

---

## [4.6] - 2026-06-02

### Added
- ProactiveEngine: context-aware triggers that monitor active window (VS Code) and suggest continuation tasks (scan TODO/FIXME, recent failures, git summary).
- Daily markdown summaries: automatic per-day report saved to ~/jarvis_reports/YYYY-MM-DD.md with commits and recent events.
- Unit tests covering headless confirm behavior and proactive features.

### Changed
- Security: headless mode no longer auto-approves ELEVATED actions. Introduced env var E.V._HEADLESS_APPROVE_ELEVATED to allow explicit override.
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
