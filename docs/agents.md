# Agentní systém JARVIS

JARVIS obsahuje tři typy agentů, každý vhodný pro jiný typ úkolů. Všichni sdílí stejné nástroje a paměťový systém.

---

## Přehled agentů

| Agent | Soubor | Kdy se použije | Max kroky |
|-------|--------|---------------|-----------|
| **ReAct** | `agent_react.py` | Lineární vícekvůlové úkoly | 8 |
| **Graf** | `agent_graph.py` | Složité úkoly s plánováním | 8 |
| **Hierarchical** | `agent_hierarchical.py` | Paralelní sub-tasky | 3×8 |

---

## ReAct Agent (`agent_react.py`)

Implementuje klasický ReAct (Reasoning + Acting) pattern.

### Smyčka

```
Thought → Action → Observation → Thought → ...
```

1. **Thought** — LLM přemýšlí co dělat dál
2. **Action** — volá nástroj (file read, web search, shell, ...)
3. **Observation** — vidí výsledek nástroje
4. Opakuje dokud nedosáhne výsledku nebo `max_steps`

### Použití

```python
from agent_react import ReactAgent
from config import CONFIG

agent = ReactAgent(
    ollama_url=CONFIG["ollama_url"],
    model=CONFIG["ollama_model"],
)

result = agent.run("Najdi v aktuálním adresáři všechny Python soubory s TODO komentáři")
print(result["answer"])
print(f"Kroků: {result['steps']}")
```

### Struktura výsledku

```python
{
    "answer": "Nalezl jsem 3 soubory s TODO: memory.py (řádek 42), llm.py (řádek 118)...",
    "steps": 4,
    "success": True,
    "history": [
        {"thought": "Musím prohledat .py soubory pomocí find a grep"},
        {"action": "shell", "params": {"command": "grep -rn 'TODO' *.py"}},
        {"observation": "memory.py:42: # TODO: optimalizovat recall\n..."},
        {"thought": "Mám výsledky, zformuluju odpověď"}
    ]
}
```

### Jak agentovi přidat nový nástroj

```python
from agent_tools import build_registry

# Nástroj je automaticky dostupný pokud je registrován v build_registry()
# Viz docs/plugin-development.md → Plugin jako nástroj pro agenty
```

---

## Graf Agent (`agent_graph.py`)

Složitější agent s explicitním plánováním a kritikou. Vhodný pro úkoly vyžadující více fází.

### Pipeline

```
PLANNER → ROUTER → EXECUTOR → CRITIC
                      ↑           │
                      └─────── (replán) ──→ DONE
```

| Uzel | Odpovědnost |
|------|-------------|
| **PLANNER** | Rozdělí úkol na seřazené kroky, odhadne potřebné nástroje |
| **ROUTER** | Vybere správný nástroj pro aktuální krok |
| **EXECUTOR** | Provede krok, zachytí výstup |
| **CRITIC** | Zhodnotí výsledek — OK / RETRY / REPLÁN / DONE |

### Kritéria pro přeplánování (CRITIC)

- Výstup obsahuje chybové patterny (`Error:`, `Traceback`, `not found`)
- Výstup je prázdný nebo podezřele krátký
- Akce měla nulový efekt (soubor stále neexistuje po `create_file`)

### Limity

```python
# config.json
{
  "agent_max_steps":   8,   # max Executor volání celkem
  "agent_max_retries": 2,   # max opakování jednoho kroku
  "agent_max_replans": 1,   # max přeplánování
  "agent_timeout":   120    # celkový timeout v sekundách
}
```

### Self-debugging

Graf agent integruje `SelfDebuggingAgent` z `agent_roles.py`. Pokud Executor vrátí odpověď obsahující chybový pattern, agent automaticky:
1. Rozpozná typ chyby (ImportError, SyntaxError, RuntimeError, ...)
2. Navrhne opravu
3. Zkusí krok znovu s opravou

### Graf events (WebSocket)

Každý přechod uzlu emituje event na `/ws/graph`:

```json
{ "type": "node_enter", "node": "planner" }
{ "type": "reasoning",  "text": "🤔 Analyzuji úkol..." }
{ "type": "node_exit" }
{ "type": "node_enter", "node": "executor" }
{ "type": "reasoning",  "text": "🔧 Spouštím: grep -rn 'TODO'" }
```

---

## Hierarchical Agent (`agent_hierarchical.py`)

Koordinátor který rozděluje komplexní úkoly na paralelní sub-tasky a deleguje je specializovaným agentům.

### Role sub-agentů

| Role | Nástroje | Typické úkoly |
|------|----------|---------------|
| **Researcher** | web_search, wiki, fetch | Vyhledávání informací, průzkum |
| **MemorySpecialist** | memory_recall, memory_store | Práce s historií a znalostmi |
| **SystemSpecialist** | shell, file_read, screenshot | OS operace, soubory |
| **Coder** | shell (python3), file_write | Psaní a spouštění kódu |

### Příklad běhu

```
Úkol: "Prozkoumej nejnovější AI frameworky, porovnej je a ulož shrnutí"

Supervisor rozdělí:
  → Researcher: "Najdi nejnovější AI frameworky (2025-2026)"
  → Researcher: "Porovnej LangChain, LlamaIndex a Haystack"
  → MemorySpecialist: "Ulož výsledky do paměti pod tagem 'ai-frameworks'"

Výsledky se sloučí → finální odpověď uživateli
```

---

## Mission Manager (`mission_manager.py`)

Dlouhodobé autonomní mise — agentní úkoly plánované přes více dní.

### Životní cyklus mise

```
create_mission() → MissionPlanner (LLM decompose)
                         ↓
                   SQLite: missions + steps uloženy
                         ↓
            (každých 15 minut — Scheduler)
                         ↓
            MissionExecutor.tick()
              └── najde due steps
              └── volá ReactAgent.run(step)
              └── uloží výsledek
                         ↓
            (po dokončení všech steps)
                         ↓
            MissionEvaluator.evaluate()
              └── LLM: success / partial / failed
              └── uloží závěrečný report
```

### Stavy mise

| Stav | Popis |
|------|-------|
| `active` | Executor provádí kroky dle plánu |
| `paused` | Dočasně pozastaveno (manuálně nebo po 3 selháních) |
| `done` | Všechny kroky dokončeny, evaluace hotová |
| `failed` | Mise selhala po max pokusech |

### Příklad vytvoření mise

```python
from mission_manager import get_mission_manager

mgr = get_mission_manager()
mission = mgr.create_mission(
    title="Týdenní audit kódu",
    description="Každý den zkontroluj jeden modul: pokryti testy, linting, docstringy",
    deadline="2026-06-10"
)

# LLM automaticky vygeneruje steps:
# Step 1 (dnes): Audit memory.py
# Step 2 (zítra): Audit llm.py
# Step 3: Audit agent_react.py
# ...
```

### Notifikace

Mise posílá notifikace při:
- Dokončení kroku
- Selhání kroku (3× retry → pauza mise)
- Dokončení celé mise s výsledkem

---

## Dostupné nástroje pro agenty

Kompletní seznam nástrojů z `agent_tools.py`:

### Systémové

| Nástroj | Popis | Příklad |
|---------|-------|---------|
| `open_app` | Spustí aplikaci | `open_app(app="chromium")` |
| `open_url` | Otevře URL | `open_url(url="https://...")` |
| `screenshot` | Pořídí screenshot | `screenshot()` |
| `system_info` | CPU, RAM, disk info | `system_info()` |

### Vision & UI

| Nástroj | Popis | Příklad |
|---------|-------|---------|
| `ui_click` | Klikne na element popsaný textem | `ui_click(element="Přihlásit")` |
| `ui_type` | Napíše text | `ui_type(text="hello@example.com")` |
| `ui_fill` | Najde pole a vyplní | `ui_fill(field="E-mail", value="...")` |
| `ui_task` | Autonomní UI úkol | `ui_task(task="Rezervuj letenku...")` |

### Vyhledávání

| Nástroj | Popis | Příklad |
|---------|-------|---------|
| `search_web` | Webové vyhledávání | `search_web(query="...")` |
| `wiki_search` | Wikipedia | `wiki_search(query="...")` |

### Soubory (MCP)

| Nástroj | Popis | Příklad |
|---------|-------|---------|
| `read_file` | Přečte soubor | `read_file(path="~/notes.txt")` |
| `list_files` | Zobrazí adresář | `list_files(path="~/Dokumenty")` |

---

## Ladění agentů

### Zapnutí verbose loggingu

```bash
LOG_LEVEL=DEBUG python jarvis.py
```

### Agent timeline v dashboardu

Každý agent run je zaznamenán v SQLite (`memory_data/agent_runs.db`) a zobrazen v dashboardu na cestě `/api/agent/timeline`.

### Debug WebSocket

Připoj se na `ws://localhost:8002/ws/graph` pro real-time sledování kroků:

```javascript
const ws = new WebSocket("ws://localhost:8002/ws/graph")
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

### Replay zaznamenaných kroků

V `AgentGraphV2` komponentě klikni na **Debug** → **Replay** pro přehrání posledního agentatního běhu.
