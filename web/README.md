# JARVIS Web UI (Next.js)

Jediný frontend pro JARVIS v5.9 — HUD dashboard napojený na FastAPI backend (`:8002`).

> Legacy Vite stack (`web/src/`, `web_vite_backup/`) byl odstraněn v5.9. Všechny panely jsou v `web/components/`.

## Stack

- **Next.js 16** + **React 19** + **TypeScript**
- **Tailwind CSS 4** + glassmorphism theme (dark/light)
- **Zustand** — global state + WebSocket connections

## Spuštění (jeden příkaz)

```bash
python3 dashboard.py
# nebo: just start
```

Otevře [http://localhost:8002/app](http://localhost:8002/app) — backend, API i UI na **jednom portu**.
Při prvním spuštění se automaticky sestaví `web_dist/` (~1 min).

```bash
python3 dashboard.py --no-open    # bez otevření prohlížeče
python3 dashboard.py --rebuild    # vynutit rebuild frontendu
```

### Volitelně: Next.js HMR (vývoj UI)

```bash
just dev-hmr   # backend :8002 + Next dev :3000 v jednom skriptu
```

## Panely

| Klávesa | Panel | Komponenta |
|---------|-------|------------|
| Alt+1 | Chat | `ChatPanel` — streaming WS, mikrofon |
| Alt+2 | Systém | `SystemPanel` |
| Alt+3 | Pluginy | `PluginMarketplace` |
| Alt+4 | Skill Gen | `SkillGenerator` |
| Alt+0 | Workflow | `WorkflowEditor` |
| Alt+W | Dnes | `WorkTimeline` — Work Timeline + dotazy |
| Alt+F | Feed | `ActivityFeed` — live WS feed + proaktivní AI |
| Alt+C | Release | `MissionChecklist` — ruční release checklisty |
| Alt+5 | Agent | `AgentGraphV2` — live graph + reasoning |
| Alt+M | Agent mise | `MissionPanel` — autonomní LLM mise |
| Alt+V | Vision | `VisionSandboxPanel` |
| Alt+6 | Timeline | `AgentTimeline` — historie agent běhů |
| Alt+7 | Paměť | `MemoryGraph` |
| Alt+8 | Dashboard | `DashboardPanel` — metriky + work summary + feed |
| Alt+9 | Nastavení | `SettingsPanel` + `AuditLogPanel` |

## Mission Control — dva systémy

| UI | API | Backend |
|----|-----|---------|
| **Agent mise** (Alt+M) | `/api/missions` | `mission_manager.py` — LLM plánuje a executor běží kroky |
| **Release** (Alt+C) | `/api/missions/checklist` | `missions.py` — ruční checklist, toggle položek |

## Chat — Copilot · Agent · Akce

Web chat (`/ws/chat`, `POST /api/chat`) používá **unified runtime** — stejný pipeline jako desktop:

1. **Akce** — lokální příkazy (*otevři chrome*, *přehled o PC*, *co mám na obrazovce*)
2. **Agent** — vícekrokové úkoly (kroky přes `agent_step`)
3. **Copilot** — konverzace s živým kontextem PC (streaming `chunk`)

Status zprávy: `💬 Copilot…` · `⚡ Provádím akci…` · `🤖 Agent pracuje…`

Živý kontext PC: `GET /api/context`

## WebSocket kanály

| Endpoint | Účel |
|----------|------|
| `/ws/chat` | Unified chat — chunk, agent_step, status, done |
| `/ws/logs` | Live logy |
| `/ws/agents` | CPU/RAM metriky (2s) |
| `/ws/graph` | Agent graph events |
| `/ws/activity` | Work Timeline feed + proaktivní návrhy |
| `/ws/confirm` | Potvrzování nebezpečných akcí |
| `/ws/audio` | VAD / duplex audio (backend) |

## Voice v prohlížeči

**Duplex** (když `audio_ws_enabled: true` v config):
- Mikrofon → `/ws/audio` → VAD → Whisper STT → unified chat → Edge-TTS v prohlížeči
- **Barge-in:** mluv během odpovědi — server i klient přeruší TTS (`interrupt` / `tts_cancel`)
- Implementace: `web/lib/audioDuplex.ts`

**Wake word** je pouze v desktopové aplikaci (pywebview), ne v prohlížeči.

**Fallback:** Web Speech API (Chrome) pokud duplex není dostupný.

## Skripty

```bash
npm run dev        # dev server :3000
npm run build      # static export → web/out
npm run lint       # ESLint
npm run typecheck  # tsc --noEmit
```

## Struktura

```
web/
├── app/              # Next.js App Router
├── components/       # UI panely (jediný zdroj pravdy)
├── store/jarvis.ts   # Zustand + WS
└── lib/api.ts        # API base helper
```

→ Backend API: [docs/api-reference.md](../docs/api-reference.md)
