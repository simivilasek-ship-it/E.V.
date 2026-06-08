# Architektura JARVIS v5.9

## Přehled

JARVIS je vrstvená aplikace složená z Python backendu, Next.js frontendu a desktopového wrapperu. Každá vrstva komunikuje přes jasně definované rozhraní — REST API, WebSocket streamy nebo přímé Python importy.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Uživatelská vrstva                        │
│   Hlas (mikrofon)  ·  Text (chat UI)  ·  Klávesová zkratka     │
└───────────────┬──────────────────────────────────┬──────────────┘
                │                                  │
                ▼                                  ▼
┌───────────────────────────┐      ┌───────────────────────────────┐
│    Whisper Live (STT)     │      │   Next.js UI → :8002/app      │
│  WebRTC VAD → Groq/local  │      │  Chat · Timeline · Feed · Mise │
│  ~200ms latence           │      │  Workflow · Release checklist │
└──────────┬────────────────┘      └────────────┬──────────────────┘
           │                                    │
           ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend :8002                          │
│                                                                  │
│   POST /api/command   WS /ws/chat   WS /ws/graph   WS /ws/audio │
│   WS /ws/confirm (ELEVATED action approval)                     │
│                                                                 │
│   FastAPI routes: src/api/routers/{monitoring,chat,plugins,...} │
│   Entrypoint shim: dashboard.py → src/api/app.py                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       App Core (app_core.py)                     │
│                                                                  │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │  LLM Engine  │  │ Local Router│  │  Command Executor    │   │
│  │  llm.py      │  │ local_router│  │  commands/           │   │
│  └──────┬───────┘  └──────┬──────┘  └──────────────────────┘   │
│         │                 │                                      │
│         ▼                 ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Hybrid LLM Router                          │    │
│  │  cloud_router.py + llm_router.py                       │    │
│  │  regex match → local  |  complex → Groq/OpenRouter     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────────┐    │
│  │  Memory     │  │  Agent Graph  │  │  Plugin System     │    │
│  │  + GraphRAG │  │  ReAct 2.0    │  │  MCP Bridge        │    │
│  └─────────────┘  └───────────────┘  └────────────────────┘    │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Mission Manager │  │  Autonomous  │  │  Vision v2       │   │
│  │ (agent mise)    │  │  Workers     │  │  OCR + Computer  │   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Release         │  │  Activity    │  │  ActivityBridge  │   │
│  │ Checklist       │  │  Store       │  │  + Collector     │   │
│  │ (missions.py)   │  │  (timeline)  │  │  (WS feed)       │   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Moduly a jejich odpovědnosti

### Vstupní vrstva

| Soubor | Odpovědnost |
|--------|-------------|
| `jarvis.py` | Hlavní entry point, spouští App Core |
| `app_core.py` | Inicializace všech systémů, orchestrátor životního cyklu |
| `dashboard.py` | FastAPI aplikace, všechny REST + WebSocket endpointy |
| `stt.py` | Speech-to-Text (Google STT + Vosk offline fallback) |
| `whisper_live.py` | Real-time Whisper STT s WebRTC VAD a barge-in podporou |
| `tts.py` | Text-to-Speech (Edge-TTS streaming) |
| `wake_word_detector.py` | Detekce wake slova pro hands-free aktivaci |
| `global_hotkey.py` | Alt+Space globální klávesová zkratka |

### LLM a routing

| Soubor | Odpovědnost |
|--------|-------------|
| `llm.py` | `LLMEngine` — hlavní orchestrátor LLM volání, cache, history |
| `llm_router.py` | `LLMRouter` — detekce typu úkolu, výběr lokálního modelu |
| `cloud_router.py` | `CloudRouter` — Groq + OpenRouter hybridní routing |
| `local_router.py` | `LocalRouter` — regex-based rychlý router pro OS příkazy |
| `prompt_tuner.py` | Optimalizace systémového promptu |

### Paměť

| Soubor | Odpovědnost |
|--------|-------------|
| `memory.py` | `JarvisMemory` — hlavní paměťový systém, SQLite + embeddingy |
| `memory_graph.py` | `SQLiteGraphStore` — knowledge graph (entity + relace) |
| `graph_extractor.py` | `GraphRAGMemory` — automatická extrakce entit z konverzací |
| `user_profile.py` | Profil uživatele, preference, extrakce faktů |
| `cache_manager.py` | In-memory + disk cache pro LLM odpovědi |

### Agenti

| Soubor | Odpovědnost |
|--------|-------------|
| `agent_react.py` | ReAct agent — think → act → observe smyčka |
| `agent_graph.py` | Graf agent — Planner → Router → Executor → Critic |
| `agent_hierarchical.py` | Hierarchical Supervisor — koordinátor sub-agentů |
| `agent_tools.py` | Registr nástrojů dostupných agentům |
| `agent_roles.py` | Specializované role (Researcher, Coder, SelfDebugger) |
| `mission_manager.py` | Dlouhodobé autonomní mise s multi-day plánováním |

### Vision a Computer Use

| Soubor | Odpovědnost |
|--------|-------------|
| `vision.py` | `VisionEngine` — OCR + screenshot describe + webcam |
| `vision_v2.py` | V2: `RealTimeScreenMonitor`, `VisionOCRPipeline`, `VisualActionPlanner` |
| `vision_pipeline.py` | GPU detekce, LLaVA wrapper, OCR cache |
| `vision_computer_use.py` | `VisionAgent` — vision-guided klikání, vyplňování formulářů |
| `computer_use.py` | AT-SPI / UIA accessibility backend |

### Background systémy

| Soubor | Odpovědnost |
|--------|-------------|
| `autonomous_workers.py` | Email, Git, Calendar, Slack, GitHub monitoring |
| `proactive.py` | Context-aware triggery (VS Code file → TODO scan) |
| `scheduler.py` | Task scheduler — jednorázové i opakující se úlohy |
| `notification_engine.py` | Desktop notifikace s urgency levely |
| `event_bus.py` | Publish-subscribe event bus mezi moduly |
| `workflow_engine.py` | Trigger-based workflow automation |

### Bezpečnost

| Soubor | Odpovědnost |
|--------|-------------|
| `security_v2.py` | `SecurityManager` — permission check, shell blacklist, audit log |
| `shadow_mode.py` | Developer assistant — read-only suggestions / autofix |

### Plugin systém

| Soubor | Odpovědnost |
|--------|-------------|
| `plugin_system.py` | Plugin loader, sandbox, health check |
| `plugin_marketplace.py` | Marketplace — install, uninstall, sandbox execution, ratings |
| `mcp_hub.py` | MCP server manager |
| `mcp_bridge.py` | Bridge pro volání MCP nástrojů z agentů |

---

## Datové toky

### Unified runtime (web + desktop)

```
POST /api/chat  nebo  WS /ws/chat
       │
       ▼
src/api/runtime.py  →  process_chat()
       │
       ▼
JarvisApp (singleton, web_mode=true)
       │
       ▼
CommandRouter.process_for_web()  [routing.py]
       │
   ┌───┴────────────┬────────────────┐
   ▼                ▼                ▼
LocalRouter      Agent pipeline    Copilot LLM
(priorita)    (Hierarchical/Graph/ReAct)  (+ ContextOrchestrator)
   │                │                │
   ▼                ▼                ▼
CommandExecutor   agent_tools     stream_ask()
```

**Pořadí fast path:** LocalRouter → pluginy (MCP) → agenti.  
**Copilot fallback:** LLM se systémovým promptem + `Kontext prostředí` z `context_orchestrator.py`.

Klíčové soubory: `src/api/runtime.py`, `src/api/lifespan.py`, `routing.py`, `app_core.py`.

---

### Tok textového příkazu

```
Uživatel zadá text
       │
       ▼
CommandRouter._fast_path() / process_for_web()
       │
       ▼
LocalRouter.route(text)   ← priorita před pluginy
       │
   ┌───┴───────────────────────────────┐
   │ Regex match?                       │
   ▼ ANO                               ▼ NE
CommandExecutor.execute()        Agent? → agent_*.py
                                       │
                                       ▼ NE
                               LLMEngine.stream_ask()  [Copilot]
   │                                   │
   ▼                               ┌───┴─────────────────────┐
Výsledek                          │ CloudRouter.should_use?  │
(otevři app, napiš, ...)          ▼ ANO           ▼ NE       │
                             Groq/OpenRouter   Ollama         │
                                   │               │          │
                                   └───────┬───────┘          │
                                           ▼                  │
                                    GraphRAG.recall_context() │
                                    Memory.recall_context()   │
                                           │                  │
                                           ▼                  │
                                    LLM odpověď               │
                                           │                  │
                                    GraphRAG.extract()        │
                                    Memory.store()            │
```

### Tok hlasového příkazu

```
Mikrofon (PCM 16kHz)
       │
       ▼
WhisperLive._capture_loop()  ← sounddevice callback
       │
       ▼
VADFilter.feed(pcm)  ← WebRTC VAD detekuje řeč
       │ utterance dokončena
       ▼
WhisperTranscriber.transcribe(wav)
  ├── Groq Whisper API (~200ms)
  └── faster-whisper lokálně (fallback)
       │
       ▼
on_transcript(text)  → stejný tok jako textový příkaz
```

### Tok agent mise

```
create_mission("Napiš blog post o AI každý den tento týden")
       │
       ▼
MissionPlanner.create_mission()
  └── LLM → decompose → 7 steps s due_date
       │
       ▼
SQLite: missions + mission_steps uloženy
       │
       ▼ (každých 15 minut)
MissionExecutor.tick()
  └── najde due steps → ReactAgent.run(step.description)
       │
       ▼
MissionEvaluator.evaluate() (po dokončení všech steps)
  └── LLM → success/partial/failed + report
```

---

## Konfigurace a priorita

Konfigurace se načítá v tomto pořadí (vyšší přebíjí nižší):

```
1. DEFAULT_CONFIG (config.py)         ← výchozí hodnoty
2. config.json                        ← lokální overrides
3. .env soubor                        ← sensitive values (API klíče)
```

Viz [configuration.md](configuration.md) pro kompletní referenci všech klíčů.

---

## Závislosti mezi moduly

```
app_core.py
  ├── llm.py
  │     ├── llm_router.py
  │     ├── cloud_router.py
  │     ├── local_router.py
  │     ├── memory.py
  │     │     └── memory_graph.py
  │     └── graph_extractor.py
  ├── commands/ (CommandExecutor)
  ├── agent_graph.py
  │     ├── agent_react.py
  │     │     └── agent_tools.py
  │     └── agent_roles.py
  ├── mission_manager.py
  │     └── agent_react.py
  ├── autonomous_workers.py
  ├── vision_v2.py
  │     └── vision_computer_use.py
  ├── plugin_system.py
  │     └── plugin_marketplace.py
  ├── mcp_hub.py → mcp_bridge.py
  ├── scheduler.py
  ├── event_bus.py
  ├── notification_engine.py
  ├── security_v2.py
  └── proactive.py
```

---

## Výkon a škálování

### Latence typických operací

| Operace | Typická latence |
|---------|----------------|
| Local router (regex match) | < 1 ms |
| Ollama qwen2.5:3b (lokálně) | 800–2000 ms |
| Groq LLaMA 3.3 (cloud) | 150–300 ms |
| Groq Whisper STT | 150–250 ms |
| faster-whisper (lokálně, base) | 300–600 ms |
| Vision OCR (pytesseract) | 200–500 ms |
| LLaVA vision (Ollama) | 2000–5000 ms |
| SQLite memory recall | < 10 ms |
| GraphRAG entity lookup | < 20 ms |

### Cache vrstvy

1. **LLM Cache** (`_LLMCache` v `llm.py`) — LRU, TTL 10 min, 200 záznamů
2. **OllamaClient Cache** (`CacheManager`) — memory backend, TTL 5 min
3. **OCR Cache** (`vision_pipeline.py`) — disk cache dle SHA1 souboru
4. **Ollama model cache** — `keep_alive=0` po vision volání uvolní VRAM
