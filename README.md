<div align="center">

# 🤖 JARVIS

**Váš ultimátní, 100% offline a soukromý AI kopilot**

*Představte si asistenta, který má plnou kontrolu nad vaším počítačem, rozumí vašemu hlasu, vidí vaši obrazovku a pamatuje si vaše preference. A to vše bez odeslání jediného bajtu dat na internet.*

[![CI](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml/badge.svg)](https://github.com/simivilasek-ship-it/Jarvis/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/tests-531%20passing-22d3a5?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![Version](https://img.shields.io/badge/version-5.0.0-6366f1?style=flat-square)](https://github.com/simivilasek-ship-it/Jarvis)
[![License](https://img.shields.io/badge/license-MIT-0ea5e9?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b82f6?style=flat-square)](https://python.org)

---

**[Rychlý start](#rychlý-start) • [Co Jarvis umí](#co-jarvis-dokáže) • [Architektura](#architektura) • [Instalace](#instalace) • [Novinky v5.0](#novinky-v50)**

</div>

---

## Novinky v5.0

### ⚡ Hybridní Cloud Router (Groq + OpenRouter)
Komplexní dotazy (kód, analýza, agenti) automaticky letí na **Groq LLaMA 3.3** — odpověď do **200 ms** místo 5 sekund. Jednoduché dotazy zůstávají lokálně. Fallback Groq → OpenRouter → Ollama, vše transparentně.

### 👁️ Vision-Guided Computer Use
JARVIS nyní **vidí obrazovku** a ovládá UI jako člověk — kliká na tlačítka popsaná textem, vyplňuje formuláře, scrolluje. Powered by Groq llama-3.2-90b-vision nebo lokální LLaVA. `"Najdi nejlevnější letenky do Tokia a vyplň formulář"` → JARVIS to sám nakliká.

### 🧠 GraphRAG Paměť
Místo prosté SQLite paměti nyní **znalostní graf** (entity + vztahy). Z každé konverzace se automaticky extrahují trojice `(Petr, pracuje na, projekt Alpha)`. Při dalším dotazu JARVIS ví, co s čím souvisí — i po týdnech.

### 🤖 Autonomní Background Workers
JARVIS běží na pozadí a **sám vás přeruší** při důležité události: nový e-mail s klíčovým slovem, commit v git repozitáři, blížící se schůzka v kalendáři, zmínka na Slacku, GitHub notifikace. Konfigurovatelný interval, filtrování podle urgence.

### 🎙️ Whisper Live — Real-time Duplex Audio
Nahrazuje blocking Google STT kontinuálním streamingem: **WebRTC VAD** → **Groq Whisper API** (200 ms) nebo lokální faster-whisper. Plná podpora **barge-in** — přerušíte JARVIS uprostřed věty a on okamžitě naslouchá.

---

## Proč zvolit JARVIS?

### 🔒 100% Soukromí & Volitelný Cloud
Jarvis běží primárně lokálně přes Ollama. Pro rychlost lze zapnout hybridní cloud routing (Groq/OpenRouter) — volba je na vás. Žádné nucené předplatné, žádné sledování.

### 🎙️ Hlasové ovládání & Vision (Whisper Live / LLaVA)
Ovládejte systém hands-free s **real-time Whisper** transkripcí (latence ~200 ms). Díky integraci **LLaVA Vision** a **vision-guided Computer Use** JARVIS vidí obrazovku a ovládá jakoukoliv aplikaci.

### 🧠 Pokročilá agentní inteligence (ReAct 2.0 & Supervisor)
Jarvis není jen chatovací bot. Je to autonomní agent, který umí:
*   **Plánovat (Planning):** Rozložit složitý úkol na logické kroky ještě před spuštěním.
*   **Sebe-opravovat (Introspection & Rollback):** Pokud se nástroj setká s chybou, Jarvis vrátí stav zpět a zkusí jinou cestu.
*   **Delegovat (Hierarchical Supervisor):** Koordinátor rozděluje zadání specializovaným sub-agentům.

### 💻 Integrace s OS & MCP servery
Díky podpoře standardu MCP (Model Context Protocol) má Jarvis k dispozici bohatý ekosystém nástrojů:
*   Přímé ovládání souborového systému (čtení, zápis, mazání souborů)
*   Integraci s Gitem (commitování, tvorba větví, PR)
*   Plnohodnotný prohlížeč Puppeteer (web-scraping, automatizace klikání)
*   Spouštění lokálních příkazů a monitorování hardwaru

### ⚡ Bleskový výkon (Cloud Router + Caching)
*   **Hybrid Cloud Router:** Groq LLaMA 3.3 pro složité dotazy (~200 ms), Ollama lokálně pro jednoduché.
*   **LLM Router v2:** Směruje mezi lokálními modely podle náročnosti úkolu.
*   **Ollama Client Caching:** Opakované dotazy 2–4× rychlejší díky lokální mezipaměti.

---

## Rychlý start

Během několika minut máte svého osobního asistenta plně zprovozněného:

```bash
# 1. Naklonujte repozitář
git clone https://github.com/simivilasek-ship-it/Jarvis.git && cd Jarvis

# 2. Spusťte instalační skript (nastaví venv a závislosti)
./install.sh

# 3. Spusťte React HUD v nativním desktopovém okně
bash start_desktop.sh
```

### Spuštění Webového Rozhraní (Next.js Dashboard)
Pro plnohodnotný moderní dashboard s live metrikami a grafem agenta:
```bash
# Spusťte FastAPI backend (port 8002)
python dashboard.py

# V novém terminálu spusťte frontend (port 3000)
cd web
npm run dev
```

---

## Co Jarvis dokáže?

| Oblast | Příklad příkazu | Co Jarvis udělá |
| :--- | :--- | :--- |
| 💻 **Počítač & Systém** | *"Nainstaluj Git a uvolni místo na disku"* | Vyhledá chybějící balíčky, zkontroluje diskové kapacity a provede úklid. |
| 📁 **Soubory** | *"Smaž staré logy a vytvoř složku archiv"* | Prozkoumá strukturu, vybere soubory dle vzoru a přesune/smaže je. |
| 👁️ **Vision (Vize)** | *"Popiš, co je na mé obrazovce"* | Udělá screenshot, pošle ho LLaVA modelu a popíše otevřená okna či kód. |
| 🌐 **Prohlížení & Web** | *"Najdi nejlepší ceny grafických karet"* | Otevře Puppeteer, vyhledá weby, vyškrábe ceny a porovná je. |
| 💾 **Dlouhodobá paměť** | *"Zapamatuj si, že preferuji tmavý režim"* | Uloží informaci do SQLite databáze s embeddingy pro pozdější vyvolání. |
| ⚙️ **Automatizace** | *"Když CPU stoupne nad 90%, pošli notifikaci"* | Spustí běžící workflow engine, který hlídá systémové triggery a spouští akce. |

---

## Architektura systému

```
JARVIS
├── 🐍 Python backend          FastAPI :8002 · WebSocket streaming
│   ├── LLM Router v2       7 typů úkolů → správný model automaticky
│   ├── 15 Skills           Plugin sandbox · Health check · Marketplace
│   ├── 10 MCP serverů      Filesystem · Git · Puppeteer · Computer Control
│   ├── Memory              SQLite + embeddingy · TTL/priority · auto-pruning
│   ├── Agents              ReAct 2.0 (Rollback, Introspection) · Hierarchical (Supervisor)
│   ├── Workflow Engine     Trigger-based automation (CPU · time · app)
│   └── Notifications       Desktop alerts · CPU/RAM monitoring
│
├── ⚛️ Next.js frontend        TypeScript · Tailwind · React
│   ├── Chat                Streaming · markdown · copy button · history
│   ├── SystemPanel         Circular gauges · 60s sparklines · live metrics
│   ├── Agent Graph         SVG pipeline visualization
│   └── Spotlight           Alt+Space global hotkey · widgets
│
└── 🪟 Desktop wrapper         pywebview nativní okno
```

### LLM Router — Inteligentní rozdělování zátěže

| Typ úkolu | Doporučený lokální model | Rychlost / Náročnost |
| :--- | :--- | :--- |
| **Překlady, jednoduchá fakta** | `qwen2.5:1.5b` | Blesková rychlost, minimální RAM |
| **Běžný chat, obecné dotazy** | `qwen2.5:3b` *(výchozí)* | Skvělý poměr výkon/rychlost |
| **Kódování, matematika** | `deepseek-coder` nebo `qwen2.5:7b` | Pokročilé programovací schopnosti |
| **Autonomní agenti, uvažování**| `llama3.1:8b` | Vysoká úroveň logiky a plánování |
| **Vision (analýza obrazu)** | `llava:7b` | Vyžaduje GPU, automatické uvolnění VRAM |

---

## Instalace a požadavky

### Prerekvizity
*   **Python 3.11+**
*   **Node.js 18+**
*   [Ollama](https://ollama.com) (pro běh lokálních LLM)
*   **ffmpeg** (pro zpracování zvuku/hlasu)

### Nastavení prostředí
```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b
```

### Rozšířené offline možnosti (volitelně)
```bash
pip install pynput          # Aktivuje globální klávesovou zkratku Alt+Space
pip install faster-whisper  # Výkonný offline převod řeči na text (STT s podporou GPU)
pip install piper-tts       # Velmi rychlý a přirozený lokální syntetizátor řeči (TTS)
pip install sentence-transformers  # Pokročilé embeddingy pro sémantické vyhledávání v paměti
ollama pull llava:7b        # Podpora pro vizuální úkoly (čtení obrazovky, webkamera)
```

---

## Bezpečnost (Security & Headless režim)

Při spouštění Jarvise v headless (serverovém) prostředí nebo v CI je bezpečnost prioritou číslo jedna:

> [!IMPORTANT]
> **Omezení ELEVATED akcí v Headless režimu:**
> Ve výchozím nastavení Jarvis v headless režimu **automaticky zamítá** všechny nebezpečné (ELEVATED) akce, jako je např. odstraňování souborů (`delete_file`) nebo vypínání systému (`shutdown`).

### Jak povolit automatické schvalování na důvěryhodných serverech?
Pokud provozujete Jarvise v kontrolovaném testovacím/CI prostředí a potřebujete povolit automatické schvalování i pro ELEVATED akce, můžete toto chování povolit nastavením systémové proměnné prostředí:

```bash
export JARVIS_HEADLESS_APPROVE_ELEVATED=1
```
*Varování: Nikdy nepovolujte tuto proměnnou na veřejně dostupných serverech bez dodatečného zabezpečení.*

---

## API a vývojářské rozhraní

Backend nabízí kompletní sadu REST a WebSocket endpointů pro integraci do dalších systémů:

*   `GET  /health` – Rychlý status backendu a WebSocket serveru
*   `GET  /api/system` – Aktuální vytížení CPU, RAM, GPU, disku a sítě
*   `POST /api/command` – Odeslání textového příkazu asistentovi
*   `WS   /ws/chat` – Streamování odpovědí LLM v reálném čase
*   `WS   /ws/agents` – Live statistiky o běžících agentech a jejich krocích

### Spuštění testů
Před odesláním příspěvku do projektu vždy spusťte kompletní testovací sadu:
```bash
# Spuštění všech 500+ testů
python -m pytest tests/ test_jarvis.py -v

# Rychlý test pouze headless bezpečnostních potvrzení
pytest tests/test_confirm_action_headless.py -q
```

---

## Vývoj a přispívání

Pokud máte nainstalovaný nástroj [`just`](https://github.com/casey/just), můžete využít následující zkratky:
*   `just web-dev` – Spustí vývojový server frontendu
*   `just web-build` – Vytvoří produkční build frontendu
*   `just docker-build` – Sestaví Docker obraz pro izolovaný běh

Podrobnosti o zapojení do vývoje a standardech kódu naleznete v souboru [CONTRIBUTING.md](CONTRIBUTING.md).

---

MIT © 2026 — [simivilasek-ship-it](https://github.com/simivilasek-ship-it)
