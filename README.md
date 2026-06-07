<div align="center">

<img src="jarvis.png" width="90" alt="JARVIS" />

# JARVIS

**Local AI assistant for Linux — chat, system commands, and optional autonomous control.**

<br/>

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Version](https://img.shields.io/badge/version-5.6-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)
[![Linux-first](https://img.shields.io/badge/Linux--first-22c55e?style=flat-square&logo=linux&logoColor=white)](#linux-out-of-the-box)
[![License](https://img.shields.io/badge/license-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)

</div>

---

## Demo

![JARVIS dashboard — chat, quick actions, live PC context](docs/dashboard.jpg)

*Web UI: chat, rychlé akce, živý kontext PC (aktivní okno, CPU/RAM/disk).*

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

![JARVIS demo — chat, agent graph, PC overview](docs/demo.gif)

> 📹 YouTube demo — coming soon

---

## Linux out of the box

> **Linux-first:** JARVIS is developed and tested primarily on Linux (Ubuntu/Debian). macOS and Windows support exists but is less complete.

After `./install.sh` and `python3 dashboard.py`, these work **without extra configuration**:

| Feature | Notes |
|---------|-------|
| **Czech chat** | Regex router + fallback replies; cloud LLM optional |
| **Local command router** | Open apps, weather, time, screenshots — &lt;1 ms, no LLM |
| **Hardware info** | CPU, RAM, disk, GPU via `/proc` and system tools |
| **Live PC context** | Active window, open apps, top processes — injected into chat |
| **Weather & time** | Built-in commands, no API key |
| **Snap app install** | `"install spotify"` etc. — requires `sudo` for `snap install` |

**Needs setup before it works:**

| Feature | Setup |
|---------|-------|
| **Local LLM chat (Ollama)** | Install [Ollama](https://ollama.com), pull a model (`ollama pull qwen2.5:3b`) |
| **Voice input (Whisper)** | Whisper model download on first use; mic permissions |
| **Background workers** | `.env` tokens for Slack, email (IMAP), GitHub, calendar |
| **Screen / UI automation** | Opt-in: `computer_use_enabled=true` in `config.json` (AT-SPI on Linux) |
| **LAN dashboard access** | `JARVIS_BIND_HOST=0.0.0.0` + `JARVIS_API_AUTH_REQUIRED=1` + token |

API binds to **`127.0.0.1` by default** — not exposed on your network unless you change it.

---

## 3 things that make it different

### 1 · Optional PC automation (opt-in)

With **`computer_use_enabled`** and vision sandbox, JARVIS can preview and execute UI actions — OCR first, vision model fallback. This is **disabled by default**; enable only when you need it.

```python
# Requires computer_use_enabled + vision sandbox approval
agent.run_task("Open Firefox and search for Python async libraries")
# → navigates visible UI when AT-SPI / vision pipeline is configured
```

Works best on Linux with AT-SPI; quality varies by app and desktop environment. Not a guarantee of control in every application.

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

External tools integrate via plugins and [Model Context Protocol](https://modelcontextprotocol.io/). Install from the marketplace when available; many require API keys in `.env`.

```bash
"install plugin brave-search"    # needs BRAVE_API_KEY
"install plugin slack-notifier"  # needs SLACK_BOT_TOKEN
```

Several MCP servers ship with the repo (filesystem, git, fetch, …). Availability depends on your OS and configured tokens — not every plugin works on every platform.

---

## Copilot · Agent · PC Manager

One chat, three automatic modes:

| Mode | When | Examples |
|------|------|----------|
| **Copilot** | Conversation, code, explanations | *"Explain asyncio"*, *"What am I working on?"* |
| **Action** | OS commands (regex router, &lt;1 ms) | *"Open Firefox"*, *"Screenshot"*, *"Weather in Prague"*, *"What time is it?"* |
| **Agent** | Multi-step tasks (needs LLM) | *"Find X and save a note"*, *"Check repo and summarize"* |

JARVIS injects **live PC context** — active window, open apps, CPU/RAM/disk — into Copilot replies when available.

```bash
"PC overview"          # system snapshot + windows + top processes
"What's on my screen?" # factual window list
"install vlc"          # snap install (sudo)
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

Local LLM (recommended for offline chat):
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

---

## Performance

| What | How fast |
|------|----------|
| OS command (`open Firefox`) | **< 1 ms** — regex, no LLM |
| Chat response (Ollama, warm) | **~120 ms+** — depends on model/GPU |
| Chat response (Groq cloud) | **~200 ms** — LLaMA 3.3 70B |
| Voice transcription (Whisper) | **~200 ms+** — first run downloads model |
| Screen click via OCR | **~50 ms** — when vision pipeline enabled |

RAM: **~34 MB** idle backend · **~650 MB+** with Ollama loaded · runs on any modern laptop.

---

## What else it does

- **Voice in web UI** — mic button / duplex stream (`/ws/audio`); Whisper STT when configured
- **Wake word** (“jarvis”) — desktop app only
- **Long-term memory** — GraphRAG knowledge graph (SQLite MVP)
- **Background workers** — email, git, Slack, GitHub, calendar — need `.env` tokens
- **Long-horizon missions** — multi-step plans executed over time
- **100% local option** — Ollama + on-device Whisper; no cloud API key required

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

- API listens on **`127.0.0.1` by default** — override with `JARVIS_BIND_HOST` only if you need LAN access
- When binding to `0.0.0.0`, set **`JARVIS_API_AUTH_REQUIRED=1`** and a strong `JARVIS_API_TOKEN`
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
