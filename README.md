<div align="center">

<img src="jarvis.png" width="100" alt="JARVIS" />

# JARVIS

### The Open-Source AI Operating System for Your Desktop

*Not a chatbot. An autonomous agent that sees, hears, remembers, and acts.*

<br/>

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Version](https://img.shields.io/badge/version-5.0-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)

<br/>

**[Začít za 60 sekund](#začít-za-60-sekund) · [Demo](#demo) · [Výkon](#výkon) · [Architektura](#architektura) · [📚 Docs](docs/index.md)**

</div>

---

## Proč "AI Operating System"?

Chatbot čeká na otázku a odpovídá. JARVIS **žije na pozadí a jedná autonomně**.

```
├── Hlídá váš e-mail, Slack, GitHub, kalendář — nepřetržitě
├── Vidí obrazovku a ovládá jakoukoliv aplikaci jako člověk
├── Pamatuje si vás přes týdny díky knowledge grafu
├── Plánuje vícedenní mise a provádí je sám
└── Odpovídá za 200 ms díky hybridnímu cloud routingu
```

Tohle není chatbot s hlasovým vstupem. Je to **vrstva inteligence nad vaším počítačem**.

---

## Demo

> 📹 **[YouTube demo — přidáme brzy]** · **[GIF: Vision Computer Use]** · **[GIF: Real-time voice]**

### Co JARVIS udělá když mu řeknete:

```
"Najdi na internetu nejlevnější letenky do Říma na tento víkend,
 vyplň formulář s mými údaji a pak mi pošli shrnutí na Slack."
```

```
JARVIS:  Otevírám prohlížeč...                        ✓  0.3s
         Vyhledávám letenky (Skyscanner + Google)...  ✓  2.1s
         Nejlevnější: Ryanair pá 19:40, 2 340 Kč
         Vyplňuji jméno, e-mail, datum...              ✓  4.8s
         Čeká na potvrzení platby (bezpečnost)         ⏸
         Posílám shrnutí na Slack #travel...           ✓  5.2s
         Hotovo. Uložil jsem do paměti pro příště.
```

### Multi-day mise

```
Vy:     "Napiš tento týden každý den shrnutí AI novinek."

JARVIS: Plánuji 5 kroků (Po–Pá)...
        [Pondělí 8:00] Prohledal jsem 23 zdrojů → shrnutí uloženo ✓
        [Úterý  8:00]  Nové: GPT-5 announced → shrnutí + tweet ✓
        ...automaticky každý den bez vyzvání
```

---

## Výkon

Měřeno na: Intel i7, 30 GB RAM, RTX 3060 (nebo bez GPU), Ubuntu 24.04

### Latence odpovědí

| Typ dotazu | Zpracování | Latence |
|------------|-----------|---------|
| OS příkaz (`otevři Chrome`) | LocalRouter regex | **< 1 ms** |
| Překlad, krátká fráze | Ollama qwen2.5:3b | **~200 ms** (cache hit) |
| Chat, obecná odpověď | Ollama qwen2.5:3b | **~570 ms** avg |
| Kód, analýza, reasoning | Groq LLaMA 3.3-70B | **~200 ms** |
| Vision OCR (kliknutí) | pytesseract | **~50 ms** |
| Vision LLM (fallback) | Groq vision | **~400 ms** |
| STT transkripce | Groq Whisper | **~200 ms** |

### Spotřeba zdrojů

| Komponenta | RAM | VRAM |
|------------|-----|------|
| Python proces (idle) | **34 MB** | — |
| Ollama qwen2.5:3b | **+268 MB** | ~2.0 GB |
| faster-whisper base | +120 MB | ~0.5 GB |
| LLaVA 7b (vision, uvolní se po použití) | — | ~4.5 GB → **0 po use** |
| JARVIS celkem (bez GPU) | **~1.2 GB RAM** | 0 GB |
| JARVIS celkem (s GPU) | ~1.5 GB RAM | ~2.5 GB VRAM |

### Rychlost modelů (lokálně)

| Model | Tok/s | Paměť | Nejlepší pro |
|-------|--------|-------|-------------|
| `qwen2.5:1.5b` | ~180 tok/s | 1.1 GB | Překlady, fakta |
| `qwen2.5:3b` | **~84 tok/s** | 2.0 GB | Chat, příkazy (výchozí) |
| `llama3.1:8b` | ~35 tok/s | 5.5 GB | Reasoning, agenti |
| Groq LLaMA 3.3 70B ☁️ | **~500 tok/s** | cloud | Kód, analýza |

### Propustnost agentů

| Úkol | Kroky | Čas |
|------|-------|-----|
| "Najdi všechna TODO v projektu" | 3 | **~4 s** |
| "Napiš a otestuj Python funkci" | 5 | **~12 s** |
| "Prohledej web, shrň, ulož do paměti" | 6 | **~18 s** |
| LocalRouter 1000× dotazů | — | **4.4 ms** (0.004 ms/dotaz) |

---

## Začít za 60 sekund

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git
cd Jarvis
./install.sh
bash start_desktop.sh
```

> Vyžaduje: Python 3.11+ a [Ollama](https://ollama.com). Nic víc.

### S webovým dashboardem

```bash
python dashboard.py    # backend :8002
cd web && npm run dev  # dashboard :3000
```

### Přidej rychlost (volitelné)

```bash
# Groq API — odpovědi za 200 ms místo 1 s
echo "GROQ_API_KEY=gsk_..." >> .env

# Real-time Whisper STT
pip install faster-whisper sounddevice webrtcvad soundfile

# Vision + UI automation
pip install pyautogui pillow pytesseract opencv-python
```

---

## Co JARVIS umí

### 🎙️ Slyší — real-time, bez prodlevy

- **Whisper Live** — WebRTC VAD detekuje řeč, Groq Whisper přepíše za ~200 ms
- **Barge-in** — přerušíte JARVIS uprostřed věty, on ihned naslouchá
- Bez tlačítka, bez čekání — prostě mluvíte

### 👁️ Vidí — a kliká

- Pořídí screenshot, přečte text přes OCR (~50 ms), klikne přesně
- Fallback na vision model (LLaVA / Groq) pokud OCR nestačí
- Funguje v **jakékoliv aplikaci** — prohlížeč, Excel, Photoshop, terminál

### 🧠 Pamatuje si — týdny, ne minuty

- **GraphRAG** — knowledge graph s entitami a vztahy
- Automaticky extrahuje: `(Petr, pracuje na, projekt Alpha)` z každé věty
- "Ten projekt z minulého úterý" → JARVIS ví co tím myslíte

### 🤖 Jedná — autonomně na pozadí

| Worker | Monitoruje | Při události |
|--------|-----------|-------------|
| Email | Klíčová slova, urgentní odesílatelé | Hlasové shrnutí |
| Git | Nové commity, PR, opravy | "Kolega pushnil do main" |
| Kalendář | Schůzky < 30 min | "Za 15 min standup, podklady?" |
| Slack | Přímé zmínky, klíčová slova | Přečte + navrhne odpověď |
| GitHub | Review requests, mentions | Upozornění |

### ⚡ Reaguje — 200 ms díky hybridnímu routingu

```
Dotaz přijde
    │
    ├─ Regex match? ──────────────────────────► OS příkaz  < 1 ms
    │
    └─ LLM potřeba?
         │
         ├─ Jednoduchý ───────────► Ollama lokálně  ~500 ms
         └─ Složitý/kód ──────────► Groq cloud      ~200 ms
```

---

## Architektura

```
src/
├── agents/      ReactAgent, GraphAgent, HierarchicalSupervisor, MissionManager
├── llm/         LLMEngine, CloudRouter (Groq+OpenRouter), LocalRouter
├── memory/      SQLiteStore, GraphRAG, UserProfile, Embeddings
├── vision/      VisionOCRPipeline, VisionAgent, RealTimeScreenMonitor
├── workers/     AutonomousWorkers, Scheduler, EventBus, WorkflowEngine
├── plugins/     PluginSystem, Marketplace, MCPBridge
├── security/    SecurityManager, ShellBlacklist, AuditLog
└── audio/       WhisperLive, DuplexEngine, VAD, TTS
```

### Stack

| | |
|--|--|
| **AI** | Ollama · Groq API · OpenRouter |
| **Agenti** | ReAct 2.0 · Graf (Planner→Critic) · Hierarchical |
| **Paměť** | SQLite + embeddingy · GraphRAG knowledge graph |
| **STT** | Whisper Live (Groq) · faster-whisper · Vosk offline |
| **Vision** | pytesseract · OpenCV · LLaVA · Groq Vision |
| **Backend** | FastAPI · WebSocket streaming · asyncio |
| **Frontend** | Next.js · TypeScript · Tailwind CSS |
| **Nástroje** | MCP Protocol (10 serverů) |

---

## Instalace — detaily

### Minimální (offline, bez cloudu)

```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
python jarvis.py
```

### Plná instalace

```bash
# Whisper Live (real-time STT)
pip install faster-whisper sounddevice webrtcvad soundfile

# Vision Computer Use
pip install pyautogui pillow pytesseract opencv-python pyperclip
sudo apt install tesseract-ocr tesseract-ocr-ces

# Desktop app
bash start_desktop.sh
```

### `.env` — klíče pro cloud

```env
# Groq — zdarma na console.groq.com (nutné pro <200ms)
GROQ_API_KEY=gsk_...

# OpenRouter — záloha, více modelů
OPENROUTER_API_KEY=sk-or-...

# Monitoring (vše volitelné)
IMAP_HOST=imap.gmail.com
IMAP_USER=vas@gmail.com
IMAP_PASS=app-password
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
CALENDAR_ICAL_URL=https://...
```

---

## Bezpečnost

```python
# Shell blacklist — vždy blokováno, bez výjimky:
rm -rf /    dd if=    mkfs.    :(){ :|:& };:    curl | sh    ...

# Shell whitelist — agent smí volat pouze:
git  pip  python3  ls  find  grep  curl  wget  npm  ...

# ELEVATED akce vyžadují potvrzení uživatele
# V headless/CI režimu jsou automaticky zamítnuty
export JARVIS_HEADLESS_APPROVE_ELEVATED=1  # jen na důvěryhodných serverech
```

Každá akce je auditována do `~/.jarvis_audit.jsonl`.

---

## API přehled

| Endpoint | Popis |
|----------|-------|
| `WS /ws/chat` | Streaming LLM odpovědi |
| `WS /ws/graph` | Real-time agent pipeline vizualizace |
| `WS /ws/audio` | Duplex audio (WebRTC) |
| `POST /api/command` | Synchronní příkaz |
| `POST /api/missions` | Vytvoř autonomní misi |
| `GET /api/marketplace` | Katalog pluginů |
| `GET /api/vision/analyze` | OCR analýza obrazovky |
| `GET /api/system` | CPU, RAM, GPU metriky |

→ Kompletní reference: **[docs/api-reference.md](docs/api-reference.md)**

---

## Testy

```bash
pytest tests/ test_jarvis.py -v        # 531 testů
pytest tests/test_confirm_action_headless.py -q  # security testy
```

---

## Přispívání

→ **[docs/plugin-development.md](docs/plugin-development.md)** — jak napsat plugin  
→ **[CONTRIBUTING.md](CONTRIBUTING.md)** — jak přispět do core  
→ **[CHANGELOG.md](CHANGELOG.md)** — co se změnilo

```bash
just web-dev      # Next.js dev server
just web-build    # produkční build
just docker-build # Docker image
```

---

<div align="center">

**Váš počítač. Vaše data. Váš asistent.**

MIT © 2026 · [simivilasek-ship-it](https://github.com/simivilasek-ship-it) · [Dokumentace](docs/index.md)

</div>
