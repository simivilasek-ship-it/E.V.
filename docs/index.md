# JARVIS v5.0 — Dokumentace

Vítejte v kompletní dokumentaci JARVIS — autonomního AI asistenta který ovládá váš počítač.

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
| Ovládat počítač přes vision | [Vision & Computer Use](vision-computer-use.md) |

---

## Co je JARVIS?

JARVIS (v5.0) je lokální AI asistent s těmito schopnostmi:

### Mluví a slyší v reálném čase
Whisper Live: WebRTC VAD → Groq Whisper API (200 ms) nebo faster-whisper lokálně. Plná barge-in podpora — přerušíte JARVISe uprostřed věty.

### Vidí obrazovku a ovládá UI
Screenshot → OCR (pytesseract, ~50 ms) → kliknutí přesně na popsaný element. Fallback na LLaVA vision (~2 s). Funguje v jakékoliv aplikaci.

### Pamatuje si přes týdny
GraphRAG knowledge graph automaticky extrahuje entity a vztahy z každé konverzace. JARVIS ví že "ten projekt z úterý" = "projekt Alpha" = "Petr".

### Plánuje a provádí dlouhodobé mise
Mission Manager rozdělí vícedenní úkol na kroky s daty, provádí je autonomně přes ReAct agenta a vyhodnotí výsledek.

### Hlídá za vás na pozadí
Autonomous Workers každých 15 minut kontrolují e-mail, git repozitáře, kalendář, Slack a GitHub. Přijde sám pokud se něco důležitého stane.

### Rychlý jako cloud, soukromý jako lokál
Hybridní router automaticky směruje složité dotazy na Groq (~200 ms) a jednoduché ponechá lokálně v Ollama. Bez API klíče = 100% lokální.

---

## Architektura v kostce

```
Hlas/Text → Local Router (regex, < 1ms)
                │ komplex
                ▼
         Hybrid LLM Router
          ├── Groq (200ms)     ← kód, analýza, agenti
          └── Ollama (1-2s)    ← chat, překlad, příkazy
                │
                ▼
     GraphRAG kontext + SQLite paměť
                │
                ▼
        LLM odpověď / Agent akce
```

Viz [Architektura](architecture.md) pro kompletní datové toky.

---

## Stack

| Vrstva | Technologie |
|--------|-------------|
| AI | Ollama, Groq API, OpenRouter |
| STT | Whisper Live, faster-whisper, Vosk |
| TTS | Edge-TTS streaming |
| Vision | LLaVA, pytesseract, OpenCV |
| Backend | FastAPI, WebSocket, asyncio |
| Frontend | Next.js, TypeScript, Tailwind |
| Desktop | pywebview |
| Paměť | SQLite, sentence-transformers, GraphRAG |
| Nástroje | MCP (Model Context Protocol) |

---

## Verze

Aktuální: **v5.0** — viz [CHANGELOG](../CHANGELOG.md) pro kompletní historii změn.
