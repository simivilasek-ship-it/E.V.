<div align="center">

<img src="jarvis.png" width="90" alt="JARVIS" />

# JARVIS

**Local AI Operating System for autonomous computer control.**

<br/>

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Version](https://img.shields.io/badge/version-5.4-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)

</div>

---

## Demo

```
You:    "Open Chrome, research the best Python async libraries,
         summarize findings, and save a note."

JARVIS: Opening Chrome...                      ✓  0.3s
        Searching: best Python async libraries ✓  1.8s
        Reading top 5 results...               ✓  4.2s
        Summarizing with Groq LLaMA 3.3...     ✓  5.1s
        Saving note to ~/notes/async-libs.md   ✓  5.4s
        Done. Want me to read it aloud?
```

![JARVIS demo — Copilot, Agent, PC overview](docs/demo.gif)

> 📹 YouTube demo — coming soon

---

## 3 things that make it different

### 1 · AI controls your PC

JARVIS sees your screen, clicks buttons, fills forms, reads content — in any app.

```python
agent.run_task("Open Gmail, find invoice from last week, download attachment")
# → opens browser → navigates → clicks → downloads. Watches it happen.
```

It uses OCR first (50 ms), falls back to vision AI (400 ms). Works in Chrome, Excel, Photoshop, terminal — anything visible on screen.

---

### 2 · Agent Graph Orchestration

Not a single LLM call. A full pipeline: **Plan → Route → Execute → Critique → Repeat**.

```
PLANNER   breaks the task into ordered steps
    │
ROUTER    picks the right tool for each step
    │
EXECUTOR  runs the tool, captures output
    │
CRITIC    validates result — retry, replan, or done
```

If a step fails, the agent backs up and tries a different path. Self-correcting. Visible in real-time in the dashboard.

---

### 3 · Plugin + MCP Ecosystem

Every external tool is a plugin. Install in one command, sandboxed by default.

```bash
"install plugin brave-search"
"install plugin github-copilot"
"install plugin slack-notifier"
```

Built on [Model Context Protocol](https://modelcontextprotocol.io/) — the same standard used by Claude, Cursor, and Zed. 10 MCP servers included out of the box.

---

## Copilot · Agent · PC Manager

One chat, three automatic modes:

| Mode | When | Examples |
|------|------|----------|
| **Copilot** | Conversation, code, explanations | *"Explain asyncio"*, *"What am I working on?"* |
| **Action** | OS commands (regex router, &lt;1 ms) | *"Open Chrome"*, *"Screenshot"*, *"Weather in Prague"* |
| **Agent** | Multi-step tasks | *"Find X and save a note"*, *"Check repo and summarize"* |

JARVIS always sees your **live PC context** — active window, open apps, CPU/RAM/disk, clipboard — injected into every Copilot reply (no hallucinated apps).

```bash
"PC overview"          # full system snapshot + windows + top processes
"What's on my screen?" # factual window list (Cursor, Firefox, …)
```

---

## Quickstart

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git
cd Jarvis && ./install.sh
python3 dashboard.py          # backend + UI → http://localhost:8002/app
python3 dashboard.py --restart   # kill old process on :8002, reload code
```

Alternativa s nativním oknem: `bash scripts/start.sh` · Makefile: `just start`

Add speed (optional — free API key at [console.groq.com](https://console.groq.com)):
```bash
echo "GROQ_API_KEY=gsk_..." >> .env
```

---

## Performance

| What | How fast |
|------|----------|
| OS command (`open Chrome`) | **< 1 ms** — regex, no LLM |
| Chat response (local, warm) | **~120 ms** — Ollama cached |
| Chat response (Groq cloud) | **~200 ms** — LLaMA 3.3 70B |
| Voice transcription | **~200 ms** — Groq Whisper |
| Screen click via OCR | **~50 ms** — pytesseract |
| Voice → answer end-to-end | **~580 ms** total |

RAM: **34 MB** idle · **~650 MB** with Ollama · runs on any modern laptop.

---

## What else it does

- **Listens continuously** — WebRTC VAD + Whisper Live, barge-in supported
- **Remembers across weeks** — GraphRAG knowledge graph, not just chat history
- **Monitors in background** — email, git, Slack, GitHub, calendar — notifies you when something matters
- **Long-horizon missions** — plan a multi-day task, JARVIS executes steps each day autonomously
- **100% local option** — no API key needed, everything runs on-device via Ollama

---

## Architecture

```
src/
├── agents/    ReactAgent · GraphAgent · MissionManager
├── llm/       Engine · CloudRouter (Groq + OpenRouter) · LocalRouter
├── memory/    SQLite + embeddings · GraphRAG knowledge graph
├── vision/    OCR pipeline · VisionAgent · Screen monitor
├── workers/   Email · Git · Slack · Calendar · GitHub watchers
├── plugins/   Marketplace · Sandbox · MCP bridge (10 servers)
├── security/  Shell blacklist · Audit log · Permission levels
└── audio/     Whisper Live · Duplex · VAD · Edge-TTS
```

Backend: **FastAPI** (`src/api/routers/`) · Frontend: **Next.js** · Desktop: **pywebview**

**Web dashboard (v5):** Unified runtime (`src/api/runtime.py`) — web chat uses the same pipeline as desktop (LocalRouter → Agents → Copilot LLM). Agent Graph V2 (Alt+5), Plugin Marketplace (Alt+3), Workflow Editor (Alt+0), Vision Sandbox (Alt+V), Missions (Alt+M), live PC context API (`GET /api/context`), voice in chat, security confirmation modal.

→ Full docs: **[docs/index.md](docs/index.md)** · Web UI: **[web/README.md](web/README.md)** · API: **[docs/api-reference.md](docs/api-reference.md)**

---

## Security

- Shell commands go through a **blacklist** (`rm -rf /`, `dd`, reverse shells, fork bombs — always blocked)
- Agent actions require **permission levels** — destructive ops need user confirmation
- **Web UI confirmation modal** — when the browser is connected, ELEVATED actions wait for approve/deny (`/ws/confirm`)
- Every action is **audit-logged** to `~/.jarvis_audit.jsonl`
- Headless/CI without web client blocks `ELEVATED` by default (opt-in: `JARVIS_HEADLESS_APPROVE_ELEVATED=1`)

---

## Tests · Docs · Contributing

```bash
pytest tests/ test_jarvis.py -v   # 531 tests
```

[API Reference](docs/api-reference.md) · [Configuration](docs/configuration.md) · [Plugin Dev](docs/plugin-development.md) · [Benchmarks](docs/benchmarks.md) · [CHANGELOG](CHANGELOG.md)

---

<div align="center">

MIT © 2026 · [simivilasek-ship-it](https://github.com/simivilasek-ship-it)

*Your computer. Your data. Your OS.*

</div>
