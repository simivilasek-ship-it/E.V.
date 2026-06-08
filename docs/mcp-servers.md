# MCP servery — co reálně funguje (Linux)

JARVIS registruje až 18 MCP serverů v `mcp_bridge.py`. Pro denní použití stačí **5 spolehlivých** bez placených API klíčů.

## Předpoklady

```bash
pip install mcp          # Python SDK — povinné
node --version           # npx pro npm servery
uvx --version            # Python MCP servery (git, fetch, time)
python3 dashboard.py --restart
```

Status v UI: **Nastavení** nebo `GET /api/mcp/status`.

## Doporučená sada (Linux, bez API klíčů)

| Server | Příkaz | K čemu |
|--------|--------|--------|
| **filesystem** | `npx` | Čtení/zápis v `~`, Dokumenty, Plocha, Stažené |
| **git** | `uvx` | `git status`, diff, log v repozitářích |
| **fetch** | `uvx` | Stáhnout text z URL |
| **mcp-memory** | `npx` | Knowledge graph MCP (`~/.jarvis_mcp_memory/`) |
| **time** | `uvx` | Čas a timezone (Europe/Prague) |

Volitelně: **youtube-transcript**, **sequential-thinking** (agent reasoning).

## Vyžadují API klíč v `.env`

| Server | Proměnná |
|--------|----------|
| brave-search | `BRAVE_API_KEY` (+ `mcp_brave_enabled=true`) |
| github | `GITHUB_TOKEN` |
| google-maps | `GOOGLE_MAPS_API_KEY` |
| slack | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |
| discord | `DISCORD_TOKEN` |

Bez klíče jsou automaticky **vypnuté** — UI může ukazovat `enabled: true` z configu, ale bridge je nespustí.

## Opt-in / nestabilní

| Server | Poznámka |
|--------|----------|
| **playwright** | `mcp_playwright_enabled=false` — těžký headless browser |
| **puppeteer** | Deprecated npm balíček, často timeout |
| **computer-control** | Pomaleý start (OCR deps), potřebuje `DISPLAY` |
| **sqlite** | Vypnuto — JARVIS má vlastní memory API |
| **everything-search** | Primárně Windows |

## Kdy se MCP používá

- **Agent / Copilot tool-calling** (`agent_tools.py`)
- **Plugin skills** (`plugins/custom/mcp_*`)
- Běžný chat (*„kolik je hodin"*, *„otevři chrome"*) jde přes **local_router** — bez MCP

## Řešení problémů

| Symptom | Fix |
|---------|-----|
| „MCP není nainstalován" | `pip install mcp` + restart dashboardu |
| UI 15/15, ale volání selhá | Stejné — chybí Python balíček `mcp` |
| Timeout 30 s | První `npx` běh stahuje balíček — zkus znovu |
| `command not found: uvx` | `pip install uv` nebo `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
