# JARVIS v5.12 — Dokumentace

Vítejte v dokumentaci JARVIS — lokálního AI asistenta ve stylu **Copilot / Gemini**, s **agentním** plánováním a **plnou správou PC**.

---

## Rychlý přehled

| Chci... | Stránka |
|---------|---------|
| Pochopit jak JARVIS funguje uvnitř | [Architektura](architecture.md) |
| Integrovat JARVIS přes API | [API Reference](api-reference.md) |
| Nastavit JARVIS pro své potřeby | [Konfigurace](configuration.md) |
| Napsat vlastní plugin | [Vývoj pluginů](plugin-development.md) |
| Pochopit agentní systém | [Agenti](agents.md) |
| Rozumět paměti a GraphRAG | [Paměť](memory.md) |
| Work Timeline — co jsem dělal | [Paměť → Work Timeline](memory.md#work-timeline) |
| Které MCP servery fungují | [MCP servery](mcp-servers.md) |
| CLI denní log | `jarvis log --today` / `jarvis log --markdown` |
| Ovládat počítač přes vision | [Vision & Computer Use](vision-computer-use.md) |

---

## Tři režimy (automaticky)

Jeden chat — systém sám vybere režim:

### 1. Copilot (konverzace)
- Odpovídá LLM (Ollama / Groq) se **živým kontextem PC**
- Vidí: aktivní okno, otevřená okna, CPU/RAM/disk, schránku, čas
- V UI: status *„Copilot…"*
- Příklady: *„vysvětli asyncio"*, *„na čem právě pracuju?"*

### 2. Akce (správa PC)
- Lokální router (`local_router.py`) — regex/fuzzy, **&lt; 1 ms**, bez LLM
- Priorita před MCP pluginy (čas, počasí, obrazovka vždy lokálně)
- Příklady: *„otevři chrome"*, *„screenshot"*, *„přehled o PC"*, *„co mám na obrazovce?"*

### 3. Agent (vícekrokové úkoly)
- Hierarchical → Graph → ReAct pipeline
- V UI: status *„Agent pracuje…"* + kroky přes WebSocket
- Příklady: *„najdi X a ulož"*, *„zkontroluj repo a shrň"*

---

## Spuštění

```bash
python3 dashboard.py              # jeden příkaz: backend + UI
python3 dashboard.py --restart    # restart po změně kódu (port 8002)
python3 dashboard.py --rebuild    # vynutit rebuild Next.js → web_dist/
```

UI: **http://localhost:8002/app**

---

## Co je JARVIS?

JARVIS je lokální AI asistent s těmito schopnostmi:

### Mluví a slyší v reálném čase
Whisper Live, Web Speech API v prohlížeči, barge-in.

### Vidí obrazovku a ovládá UI
OCR (~50 ms), vision AI fallback, `screen_describe` z reálných oken (bez halucinací).

### Přehled o počítači
`ContextOrchestrator` + příkaz `pc_overview` — CPU, RAM, disk, okna, procesy. API: `GET /api/context`.

### Pamatuje si přes týdny
GraphRAG + SQLite paměť.

### Plánuje dlouhodobé mise
Mission Manager — vícedenní autonomní úkoly.

### Hlídá na pozadí
Autonomous Workers — e-mail, git, Slack, GitHub.

### Hybridní rychlost
Groq (~200 ms) pro složité dotazy, Ollama lokálně bez API klíče.

---

## Architektura v kostce

```
Text/Hlas → CommandRouter (routing.py)
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 LocalRouter  Agenti   Copilot LLM
 (akce)    (multi-step) (+ kontext PC)
```

Web API používá stejný pipeline přes `src/api/runtime.py` → `JarvisApp` singleton.

Viz [Architektura](architecture.md).

---

## Stack

| Vrstva | Technologie |
|--------|-------------|
| AI | Ollama, Groq API, OpenRouter |
| STT | Whisper Live, faster-whisper, Vosk |
| TTS | Edge-TTS streaming |
| Vision | LLaVA, pytesseract, Xlib okna |
| Backend | FastAPI, WebSocket, unified runtime |
| Frontend | Next.js static export → `/app` |
| Desktop | pywebview |
| Paměť | SQLite, sentence-transformers, GraphRAG |
| Nástroje | MCP (Model Context Protocol) |

---

## Verze

Aktuální: **v5.4.0** — viz [CHANGELOG](../CHANGELOG.md).
