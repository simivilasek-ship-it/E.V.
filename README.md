<div align="center">

<img src="jarvis.png" width="120" alt="JARVIS" />

# JARVIS

### Váš osobní AI, který skutečně ovládá váš počítač

*Mluví. Vidí. Pamatuje si. Jedná.*

<br/>

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Version](https://img.shields.io/badge/verze-5.0-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/licence-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/testy-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)

<br/>

**[Začít za 60 sekund](#-začít-za-60-sekund) · [Co umí](#-co-jarvis-dokáže) · [Jak to funguje](#-jak-to-funguje) · [Instalace](#-instalace) · [📚 Dokumentace](docs/index.md)**

</div>

---

<br/>

## Proč JARVIS?

Většina "AI asistentů" jsou jen chatboti. Napíšete otázku, dostanete odpověď. Tím to končí.

**JARVIS je jiný.** Je to agent, který přečte váš e-mail, všimne si změny v kódu, otevře prohlížeč, vyplní formulář a přijde za vámi — sám od sebe, bez vyzvání.

```
Vy:     "Najdi nejlevnější letenky do Říma na příští víkend a rezervuj."

JARVIS: Otevírám prohlížeč... ✓
        Vyhledávám letenky... ✓
        Nejlevnější: Wizz Air, pátek 18:40, 2 890 Kč
        Vyplňuji formulář... ✓
        Čeká na vaše potvrzení platby.
```

Žádné API klíče třetích stran. Žádná cloudová AI co čte vaše zprávy. Běží na vašem počítači.

<br/>

---

## ⚡ Začít za 60 sekund

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git
cd Jarvis
./install.sh
bash start_desktop.sh
```

> Potřebujete Python 3.11+ a [Ollama](https://ollama.com). Nic víc.

**Nebo s webovým dashboardem:**

```bash
python dashboard.py   # backend :8002
cd web && npm run dev # frontend :3000
```

<br/>

---

## 🎯 Co JARVIS dokáže

### Mluví s vámi — a skutečně vás slyší

Žádné stisknutí tlačítka, žádné čekání. Jen mluvte.

- **Whisper Live** — real-time transkripce s latencí ~200 ms (přes Groq nebo lokálně)
- **Barge-in** — přerušíte JARVIS uprostřed věty, on okamžitě naslouchá
- **WebRTC VAD** — automaticky rozezná řeč od ticha, neplýtvá výpočetním výkonem

```
"Hej JARVIS, jaký je stav mého projektu?"
→ JARVIS přečte git log, zkontroluje otevřené PR a odpoví hlasem za 0.8 s
```

---

### Vidí vaši obrazovku — a ovládá ji

JARVIS pořídí screenshot, pochopí co vidí, a pak klikne přesně tam, kde má.

- Klikání, vyplňování formulářů, scrollování — bez XPath, bez selektorů
- Popíšete prvek slovy: `"tlačítko Přihlásit"`, `"pole pro e-mail"` — najde ho
- Funguje v **jakékoliv aplikaci** — Chrome, Excel, Photoshop, terminál

```
"Otevři Gmail, najdi nepřečtený e-mail od klienta a přepošli mi shrnutí."
→ JARVIS otevře Gmail, přečte e-mail, přepíše klíčové body a oznámí vám je hlasem
```

---

### Pamatuje si vás — opravdu

Žádné "Jako AI nemám přístup k předchozím konverzacím."

- **GraphRAG** — znalostní graf vztahů (entity, projekty, lidé, preference)
- Z každé konverzace extrahuje trojice: `(Petr, pracuje na, projekt Alpha)`
- Při dalším dotazu automaticky doplní kontext z grafu

```
Minulý týden: "Pracuji s Petrem na redesignu webu, deadline je 20. června."

Dnes: "Jak jsme na tom s tím projektem?"
→ JARVIS ví: projekt = redesign webu, kolega = Petr, deadline = 20. června
```

---

### Hlídá za vás — bez vašeho vyzvání

JARVIS běží na pozadí a přijde za vámi, když se něco děje.

| Zdroj | Co monitoruje | Jak reaguje |
|---|---|---|
| 📧 **E-mail** | Klíčová slova, urgentní odesílatelé | Hlasové upozornění + shrnutí |
| 🐙 **Git** | Nové commity, PR, fixbranch | "Kolega pushnil změnu do hlavní větve" |
| 📅 **Kalendář** | Blížící se schůzky (< 30 min) | "Za 15 minut máš standup, chceš podklady?" |
| 💬 **Slack** | Přímé zmínky, klíčová slova | Přečte a navrhne odpověď |
| 🐱 **GitHub** | Review requests, mentions | "Žádají tě o code review" |

---

### Přemýšlí v krocích — a opravuje se sám

JARVIS není jen chatbot. Je to **ReAct agent** — plánuje, provádí, kontroluje výsledek.

```
Úkol: "Nainstaluj závislosti a spusť testy."

Krok 1: pip install -r requirements.txt  ✓
Krok 2: pytest tests/                    ✗  (3 testy selhaly)
Krok 3: Analyzuji chyby...               ✓
Krok 4: Opravuji import v test_memory.py ✓
Krok 5: pytest tests/                    ✓  531/531 passing
```

Při chybě JARVIS **neselže tiše** — vrátí se zpět, zkusí jinou cestu a informuje vás.

---

### Rychlý jako cloud — soukromý jako lokál

Hybridní router automaticky rozhoduje kde dotaz zpracovat:

| Dotaz | Kde se zpracuje | Latence |
|---|---|---|
| "Přelož tuhle větu" | Ollama lokálně | ~1 s |
| "Napiš mi REST API v Pythonu" | Groq LLaMA 3.3 | **~200 ms** |
| "Analyzuj tento dataset" | Groq / OpenRouter | **~300 ms** |
| "Otevři Spotify" | Lokální router (regex) | **< 50 ms** |

Bez Groq klíče — vše lokálně. S klíčem — automaticky nejrychlejší cesta.

<br/>

---

## 🏗️ Jak to funguje

```
  Váš hlas / text
        │
        ▼
  ┌─────────────┐     regex match?     ┌──────────────────┐
  │ Local Router│ ──────────────────► │ CommandExecutor  │
  └─────────────┘         ne          └──────────────────┘
        │                                      │
        ▼                               otevře app / soubor
  ┌─────────────────────────────────────────────────────┐
  │              Hybrid LLM Router                      │
  │  jednoduché → Ollama qwen2.5:3b  (lokálně, ~1 s)   │
  │  složité    → Groq LLaMA 3.3     (cloud, ~200 ms)  │
  │  vision     → LLaVA / Groq Vision                   │
  └─────────────────────────────────────────────────────┘
        │
        ├── Paměť: GraphRAG knowledge graph + SQLite embeddingy
        ├── Nástroje: 10 MCP serverů (filesystem, git, browser...)
        ├── Agenti: ReAct 2.0 (plán → akce → kontrola → oprava)
        └── Workers: email, git, calendar, slack, github (pozadí)
```

### Stack

| Vrstva | Technologie |
|---|---|
| **AI / LLM** | Ollama + Groq API + OpenRouter |
| **STT** | Whisper Live (Groq) · faster-whisper · Vosk offline |
| **TTS** | Edge-TTS streaming · piper-tts |
| **Vision** | LLaVA · Groq llama-3.2-90b-vision |
| **Paměť** | SQLite + embeddingy · GraphRAG knowledge graph |
| **Backend** | FastAPI · WebSocket streaming · asyncio |
| **Frontend** | Next.js · TypeScript · Tailwind CSS |
| **Desktop** | pywebview nativní okno |
| **Nástroje** | MCP (Model Context Protocol) |
| **Bezpečnost** | SecurityManager · shell blacklist/whitelist · audit log |

<br/>

---

## 🔧 Instalace

### Minimální (lokální, bez cloudu)

```bash
git clone https://github.com/simivilasek-ship-it/Jarvis.git
cd Jarvis
pip install -r requirements.txt
ollama pull qwen2.5:3b
python jarvis.py
```

### Plná instalace (doporučeno)

```bash
# Rychlejší STT
pip install faster-whisper sounddevice webrtcvad soundfile

# Vision-guided ovládání UI
pip install pyautogui pillow pyperclip

# Desktop aplikace
bash start_desktop.sh
```

### Cloud routing — volitelné, ale výrazně rychlejší

Přidejte do `.env`:

```env
GROQ_API_KEY=gsk_...          # zdarma na console.groq.com
OPENROUTER_API_KEY=sk-or-...  # zdarma na openrouter.ai
```

Bez těchto klíčů JARVIS funguje 100% lokálně. S nimi se složité dotazy zpracují za ~200 ms.

### Monitorování (volitelné)

```env
IMAP_HOST=imap.gmail.com
IMAP_USER=vas@gmail.com
IMAP_PASS=app-heslo           # Google App Password
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
CALENDAR_ICAL_URL=https://...
```

<br/>

---

## 🛡️ Bezpečnost

JARVIS nikdy neprovede destruktivní akci bez vašeho vědomí.

- **Shell blacklist** — `rm -rf /`, `dd`, `mkfs`, reverse shell, fork bomb → vždy blokováno
- **Shell whitelist** — pouze explicitně povolené příkazy (`git`, `pip`, `ls`, ...)
- **Headless mode** — v CI/serveru jsou ELEVATED akce automaticky zamítnuty
- **Audit log** — každá akce je zaznamenána do `~/.jarvis_audit.jsonl`

```bash
# Povolení ELEVATED akcí v CI (jen na důvěryhodných serverech)
export JARVIS_HEADLESS_APPROVE_ELEVATED=1
```

<br/>

---

## 📡 API

| Endpoint | Popis |
|---|---|
| `GET /health` | Status backendu |
| `GET /api/system` | CPU, RAM, GPU, disk — live |
| `POST /api/command` | Odešle příkaz, vrátí výsledek |
| `WS /ws/chat` | Streaming LLM odpovědi chunk po chunku |
| `WS /ws/agents` | Live stav ReAct agenta |
| `WS /ws/graph` | Vizualizace agent pipeline |
| `WS /ws/audio` | Duplex audio (WebRTC VAD) |

<br/>

---

## 🧪 Testy

```bash
pytest tests/ test_jarvis.py -v          # 531 testů
pytest tests/test_confirm_action_headless.py -q  # bezpečnostní testy
```

<br/>

---

## 🤝 Přispívání

```bash
just web-dev      # vývojový server frontendu
just web-build    # produkční build
just docker-build # Docker image
```

Podrobnosti v [CONTRIBUTING.md](CONTRIBUTING.md).

<br/>

---

<div align="center">

**JARVIS je open-source. Žádné předplatné. Žádné sledování. Váš počítač, váš asistent.**

MIT © 2026 — [simivilasek-ship-it](https://github.com/simivilasek-ship-it)

</div>
