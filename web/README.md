# JARVIS Web UI (Next.js)

Frontend pro JARVIS v5 — HUD dashboard napojený na FastAPI backend (`:8002`).

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

## Panely (Alt+1..0)

| Klávesa | Panel | Komponenta |
|---------|-------|------------|
| Alt+1 | Chat | `ChatPanel` — streaming WS, mikrofon |
| Alt+2 | Systém | `SystemPanel` |
| Alt+3 | Pluginy | `PluginMarketplace` |
| Alt+4 | Skill Gen | `SkillGenerator` |
| Alt+5 | Agent | `AgentGraphV2` — live graph + reasoning |
| Alt+6 | Timeline | `AgentTimeline` |
| Alt+7 | Paměť | `MemoryGraph` |
| Alt+8 | Dashboard | `DashboardPanel` |
| Alt+9 | Nastavení | `SettingsPanel` + `AuditLogPanel` |
| Alt+0 | Workflow | `WorkflowEditor` |

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
├── components/       # UI panely
├── store/jarvis.ts   # Zustand + WS
└── lib/api.ts        # API base helper
```

→ Backend API: [docs/api-reference.md](../docs/api-reference.md)
