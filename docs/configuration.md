# Konfigurace JARVIS v5.0

Konfigurace se načítá v pořadí: `DEFAULT_CONFIG` → `config.json` → `.env` (nejvyšší priorita).

---

## Základní nastavení

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `ollama_url` | `http://localhost:11434/api/chat` | URL Ollama API |
| `ollama_model` | `qwen2.5:3b` | Výchozí lokální model |
| `history_size` | `20` | Počet zpráv v konverzační historii |
| `log_level` | `INFO` | Úroveň logování (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `log_file` | `jarvis.log` | Cesta k log souboru |
| `log_json_format` | `true` | Strukturované JSON logy |

---

## TTS (Text-to-Speech)

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `tts_enabled` | `true` | Zapnout/vypnout hlasový výstup |
| `tts_voice` | `cs-CZ-AntoninNeural` | Hlas pro Edge-TTS (Azure Neural) |
| `tts_rate` | `170` | Rychlost řeči (50–400 slov/min) |

**Dostupné české hlasy:** `cs-CZ-AntoninNeural` (muž), `cs-CZ-VlastaNeural` (žena)

---

## STT (Speech-to-Text)

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `stt_language` | `cs-CZ` | Jazyk rozpoznávání |
| `stt_timeout` | `10` | Max sekundy čekání na řeč |
| `stt_phrase_limit` | `15` | Max délka jedné fráze v sekundách |
| `stt_energy_threshold` | `300` | Prahová hodnota pro detekci hlasu (100–4000) |

---

## Vision Sandbox (dry-run)

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `vision_sandbox_enabled` | `true` | Agent nejdřív ukáže náhled kliknutí, neprovede hned |
| `vision_sandbox_auto_execute` | `false` | Pokud `true`, náhled se hned provede (jen pro dev) |

UI: panel **Vision** (Alt+V) · API: `POST /api/vision/sandbox/preview`, `POST /api/vision/sandbox/execute`

---

## Multi-agent mise

| Pole API | Hodnoty | Popis |
|----------|---------|-------|
| `agent_mode` | `single`, `multi`, `parallel` | Režim executoru pro kroky mise |

- `single` — ReAct agent (výchozí)
- `multi` — MultiAgentOrchestrator (Planner→Critic)
- `parallel` — paralelní vlny sub-agentů

UI: panel **Mise** (Alt+M)

---

## Web UI & bezpečnost

| Klíč / Env | Výchozí | Popis |
|------------|---------|-------|
| `audio_ws_enabled` | `true` | WebSocket `/ws/audio` pro VAD/duplex |
| `JARVIS_HEADLESS_APPROVE_ELEVATED` | *(unset)* | Opt-in auto-schválení ELEVATED v headless bez web UI |

Pokud je otevřený web dashboard, nebezpečné akce čekají na modal v prohlížeči (`/ws/confirm`).

---

## Whisper Live (real-time STT)

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `whisper_live_enabled` | `true` | Použít Whisper Live místo blocking STT |
| `whisper_model_size` | `base` | Velikost modelu: `tiny`, `base`, `small`, `medium`, `large` |
| `duplex_barge_in` | `true` | Povolit přerušení TTS mluvením |

---

## Hybridní Cloud Routing

| Klíč | Výchozí | Env proměnná | Popis |
|------|---------|-------------|-------|
| `cloud_routing_enabled` | `true` | `CLOUD_ROUTING_ENABLED` | Zapnout hybridní routing |
| `cloud_routing_threshold` | `complex` | `CLOUD_ROUTING_THRESHOLD` | Kdy použít cloud: `complex`, `always`, `simple` |
| `groq_api_key` | `""` | `GROQ_API_KEY` | API klíč pro Groq (console.groq.com) |
| `openrouter_api_key` | `""` | `OPENROUTER_API_KEY` | API klíč pro OpenRouter |

**Hodnoty `cloud_routing_threshold`:**
- `complex` — cloud pro kód, reasoning, math, agenty (doporučeno)
- `always` — vždy cloud, Ollama jako fallback
- `simple` — cloud jen pro rychlé dotazy (překlady, krátké fráze)

---

## Paměť

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `memory_dir` | `memory_data` | Adresář pro SQLite databáze paměti |
| `graph_extraction_enabled` | `true` | Automatická extrakce entit do knowledge grafu |
| `graph_backend` | `sqlite_mvp` | Backend grafu (`sqlite_mvp` nebo `neo4j`) |
| `memory_graph_auto_merge` | `false` | Automatické slučování podobných entit |
| `memory_graph_merge_threshold` | `0.88` | Práh podobnosti pro auto-merge (0.0–1.0) |

---

## Agenti

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `agent_max_steps` | `8` | Max počet kroků ReAct/Graf agenta |
| `agent_max_retries` | `2` | Max opakování jednoho kroku při chybě |
| `agent_max_replans` | `1` | Max přeplánování při záseku |
| `agent_timeout` | `120` | Celkový timeout agenta v sekundách |
| `agent_llm_tokens` | `500` | Max tokenů na jeden LLM call v agentovi |

---

## Mise (Mission Manager)

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `missions_enabled` | `true` | Zapnout autonomní mise |

---

## Autonomous Workers (monitoring na pozadí)

| Klíč | Výchozí | Env proměnná | Popis |
|------|---------|-------------|-------|
| `autonomous_workers_enabled` | `true` | — | Zapnout background workery |
| `auto_workers_interval` | `900` | `AUTO_WORKERS_INTERVAL` | Interval kontrol v sekundách (15 min) |
| `imap_host` | `""` | `IMAP_HOST` | IMAP server (např. `imap.gmail.com`) |
| `imap_user` | `""` | `IMAP_USER` | E-mailová adresa |
| `imap_pass` | `""` | `IMAP_PASS` | Heslo nebo App Password |
| `calendar_ical_url` | `""` | `CALENDAR_ICAL_URL` | URL iCal kalendáře |
| `slack_bot_token` | `""` | `SLACK_BOT_TOKEN` | Slack Bot Token (`xoxb-...`) |
| `github_token` | `""` | `GITHUB_TOKEN` | GitHub Personal Access Token |

---

## Vision a Computer Use

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `computer_use_enabled` | `false` | Zapnout accessibility backend (AT-SPI) |
| `computer_use_backend` | `auto` | Backend: `auto`, `linux_atspi`, `windows_uia`, `macos_ax` |
| `vision_gpu_enabled` | `false` | Použít GPU pro vision modely |
| `vision_cache_enabled` | `true` | Cache OCR výsledků na disk |
| `vision_cache_dir` | `~/.jarvis/vision_cache` | Adresář pro OCR cache |
| `vision_low_end_mode` | `false` | Redukovaná kvalita pro slabý hardware |

---

## MCP Servery

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `mcp_filesystem_enabled` | `true` | Čtení/zápis souborů |
| `mcp_git_enabled` | `true` | Git operace |
| `mcp_memory_enabled` | `true` | Sdílená paměť přes MCP |
| `mcp_brave_enabled` | `false` | Brave Search (vyžaduje `BRAVE_API_KEY`) |
| `mcp_fetch_enabled` | `true` | HTTP fetch webových stránek |
| `mcp_playwright_enabled` | `false` | Headless prohlížeč (vyžaduje playwright) |
| `mcp_github_enabled` | `true` | GitHub API (vyžaduje `GITHUB_TOKEN`) |
| `mcp_slack_enabled` | `true` | Slack API (vyžaduje `SLACK_BOT_TOKEN`) |
| `mcp_google_maps_enabled` | `true` | Google Maps (vyžaduje `GOOGLE_MAPS_API_KEY`) |
| `mcp_result_limit` | `32000` | Max znaků z MCP výsledku před zkrácením |

---

## Pluginy

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `plugins_enabled` | `true` | Zapnout plugin systém |
| `plugins_dir` | `plugins` | Kořenový adresář pluginů |
| `disabled_plugins` | `[]` | Seznam deaktivovaných pluginů (jména) |
| `marketplace_enable_ratings` | `true` | Zobrazit hodnocení v marketplace |

---

## Proactive Engine

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `proactive_enabled` | `true` | Zapnout context-aware triggery |
| `proactive_daily_time` | `18:00` | Čas denního reportu (`HH:MM`) |
| `proactive_poll_interval` | `2.0` | Interval polling aktivního okna (sekundy) |
| `proactive_max_notify_interval` | `3600` | Min. interval mezi notifikacemi pro stejný soubor |
| `proactive_report_retention_days` | `30` | Počet dní uchování denních reportů |
| `proactive_workspace_roots` | `[]` | Adresáře pro skenování (prázdné = auto-detekce) |
| `proactive_max_files_scan` | `2000` | Max souborů při skenu workspace |

---

## Bezpečnost

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `audit_enabled` | `true` | Zapnout audit log |
| `audit_log_file` | `audit.log` | Cesta k audit logu |
| `rate_limit_window` | `60.0` | Okno rate limiteru v sekundách |
| `rate_limit_max` | `10` | Max požadavků za okno |

**Headless bezpečnost:**
```bash
# Ve výchozím nastavení jsou ELEVATED akce v headless režimu ZAMÍTNUTY.
# Pro povolení (jen na důvěryhodných serverech):
export JARVIS_HEADLESS_APPROVE_ELEVATED=1
```

---

## Ukázkový `.env` soubor

```env
# Povinné pro cloud routing (doporučeno)
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...

# MCP integrace
BRAVE_API_KEY=BSA...
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
GOOGLE_MAPS_API_KEY=AIza...

# E-mail monitoring
IMAP_HOST=imap.gmail.com
IMAP_USER=vas@gmail.com
IMAP_PASS=app-heslo-16-znaku

# Kalendář
CALENDAR_ICAL_URL=https://calendar.google.com/.../basic.ics

# Volitelné overrides
OLLAMA_MODEL=llama3.1:8b
CLOUD_ROUTING_THRESHOLD=complex
LOG_LEVEL=DEBUG
```

---

## Ukázkový `config.json`

```json
{
  "ollama_url": "http://localhost:11434/api/chat",
  "ollama_model": "qwen2.5:3b",
  "tts_voice": "cs-CZ-AntoninNeural",
  "tts_rate": 170,
  "history_size": 20,
  "cloud_routing_enabled": true,
  "cloud_routing_threshold": "complex",
  "whisper_model_size": "base",
  "agent_max_steps": 8,
  "missions_enabled": true,
  "autonomous_workers_enabled": true,
  "auto_workers_interval": 900,
  "proactive_enabled": true,
  "proactive_daily_time": "18:00",
  "memory_dir": "memory_data",
  "graph_extraction_enabled": true,
  "plugins_enabled": true,
  "mcp_filesystem_enabled": true,
  "mcp_git_enabled": true,
  "mcp_brave_enabled": true,
  "audit_enabled": true
}
```
