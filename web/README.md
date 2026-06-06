# JARVIS Web UI (Next.js)

Frontend pro JARVIS v5 — HUD dashboard napojený na FastAPI backend (`:8002`).

## Stack

- **Next.js 16** + **React 19** + **TypeScript**
- **Tailwind CSS 4** + glassmorphism theme (dark/light)
- **Zustand** — global state + WebSocket connections

## Spuštění (dev)

```bash
# Terminal 1 — backend
python dashboard.py

# Terminal 2 — frontend
cd web
npm ci
npm run dev
```

Otevři [http://localhost:3000](http://localhost:3000). API/WS proxy v dev módu jde přímo na `127.0.0.1:8002`.

## Produkční build

```bash
bash scripts/build.sh   # vytvoří ../web_dist
python dashboard.py     # UI na http://localhost:8002/app
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

## WebSocket kanály

| Endpoint | Účel |
|----------|------|
| `/ws/chat` | Streaming LLM odpovědi |
| `/ws/logs` | Live logy |
| `/ws/agents` | CPU/RAM metriky (2s) |
| `/ws/graph` | Agent graph events |
| `/ws/confirm` | Potvrzování nebezpečných akcí |
| `/ws/audio` | VAD / duplex audio (backend) |

## Voice v prohlížeči

Tlačítko mikrofonu v chatu používá **Web Speech API** (nejlepší v Chrome).
Pro plný duplex STT/TTS použij desktop mód (`whisper_live.py`).

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
