# Paměťový systém E.V.

E.V. používá vícevrstvý paměťový systém kombinující SQLite embeddingy, knowledge graph a neural memory.

---

## Vrstvy paměti

```
┌─────────────────────────────────────────────────────────────┐
│                    E.V.Memory (memory.py)                   │
│                                                              │
│  ┌──────────────────┐    ┌────────────────────────────────┐  │
│  │  Epizodická      │    │  SQLite Memory Store           │  │
│  │  (EpisodicMemory)│    │  (_SQLiteMemoryStore)          │  │
│  │                  │    │  - content + importance        │  │
│  │  Krátkodobé      │    │  - embeddingy (sentence-       │  │
│  │  vzpomínky       │    │    transformers nebo TF-IDF)   │  │
│  │  v RAM           │    │  - TTL, priority, access score │  │
│  └──────────────────┘    └────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │               Knowledge Graph (GraphRAG)             │    │
│  │  SQLiteGraphStore + GraphRAGMemory                   │    │
│  │  Entity: "Petr"  ──[pracuje na]──►  "projekt Alpha" │    │
│  │  Automatická extrakce z každé konverzace             │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                Procedurální paměť                      │  │
│  │  ProceduralMemory — relace, fakta o uživateli         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## SQLite Memory Store

### Schéma databáze (`memory_data/memories.db`)

```sql
CREATE TABLE memories (
    id           TEXT PRIMARY KEY,      -- 8-znakový UUID
    content      TEXT NOT NULL,         -- text vzpomínky
    importance   REAL NOT NULL,         -- 0.0–1.0, vyšší = důležitější
    tags         TEXT NOT NULL,         -- JSON pole tagů
    metadata     TEXT NOT NULL,         -- JSON dict s kontextem
    created_at   REAL NOT NULL,         -- Unix timestamp
    last_access  REAL NOT NULL,         -- poslední přístup
    access_count INTEGER NOT NULL,      -- počet přístupů
    priority     INTEGER NOT NULL,      -- 0–10, vyšší = přednostní
    ttl_seconds  INTEGER NOT NULL,      -- 0 = bez expiry
    expires_at   REAL NOT NULL,         -- 0 = bez expiry
    access_score REAL NOT NULL          -- kombinovaný skóre pro recall
);

-- Indexy pro rychlý recall
CREATE INDEX idx_importance    ON memories(importance);
CREATE INDEX idx_created_at    ON memories(created_at);
CREATE INDEX idx_expires_at    ON memories(expires_at);
CREATE INDEX idx_priority      ON memories(priority);
CREATE INDEX idx_last_access   ON memories(last_access);
CREATE INDEX idx_access_score  ON memories(access_score);
```

### Skóre relevance při recall

```python
# Kombinuje 3 faktory:
score = (
    0.5 * semantic_similarity  # embeddingy nebo TF-IDF keyword overlap
  + 0.3 * importance           # importance z metadat
  + 0.2 * recency_score        # čím novější, tím vyšší
)
```

### Decay (zapomínání)

Paměti postupně ztrácejí důležitost:

```python
new_importance = old_importance * exp(-decay_rate * age_days)
# decay_rate = 0.01 (výchozí) → na 0.1 klesne za ~230 dní
```

Paměti pod `min_importance=0.05` jsou automaticky smazány při maintenance.

---

## Knowledge Graph (GraphRAG)

### Schéma (`memory_data/knowledge_graph.db`)

```sql
CREATE TABLE entities (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,         -- "Petr Novák", "projekt Alpha"
    embedding TEXT,                  -- JSON vektor pro sémantické hledání
    metadata  TEXT                   -- JSON dict
);

CREATE TABLE relations (
    id         INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL,     -- odkaz na entities.id
    predicate  TEXT NOT NULL,        -- "pracuje na", "preferuje", "je autorem"
    object_id  INTEGER NOT NULL,     -- odkaz na entities.id
    ts         REAL NOT NULL,        -- kdy byla relace zaznamenána
    source     TEXT,                 -- "conversation", "user_input"
    confidence REAL DEFAULT 1.0      -- 0.0–1.0
);
```

### Automatická extrakce entit

Z každé konverzace se automaticky extrahují trojice (subject, predicate, object):

**Regex extrakce (rychlá, bez LLM):**
```
"Pracuji na projektu Alpha s Petrem"
→ ("uživatel", "pracuje na projektu", "Alpha")
→ ("Petr", ???)  -- jen jméno bez kontextu → přeskočeno

"Preferuji tmavé téma v editoru"
→ ("uživatel", "preferuje", "tmavé téma v editoru")
```

**LLM extrakce (přesnější, pro delší texty):**
```
Prompt: "Extrahuj entity a vztahy → JSON [{s, p, o}]"
Input: celý text konverzace (max 800 znaků)
Output: [{"s": "Petr", "p": "pracuje na", "o": "projekt Alpha"}]
```

### Dotaz na graph kontext

Při každém LLM volání se graph dotáže na relevantní entity:

```python
# Dotaz: "Jak jsme na tom s projektem?"
graph_ctx = graph_rag.recall_graph_context("projekt")
# Vrátí:
# "Znalostní kontext:
#  • Petr pracuje na projekt Alpha
#  • projekt Alpha má deadline 20.6.2026
#  • uživatel preferuje Python pro projekt Alpha"
```

Tento kontext se automaticky přidá do systémového promptu.

---

## Embeddingy

### Primární: sentence-transformers

Model: `paraphrase-multilingual-MiniLM-L12-v2` (podpora češtiny)

```bash
pip install sentence-transformers
# Model se stáhne automaticky (~120 MB)
```

### Fallback: TF-IDF keyword overlap

Pokud sentence-transformers není nainstalováno, E.V. použije keyword overlap:

```python
similarity = len(words_a & words_b) / len(words_a | words_b)
```

Tento fallback má nižší recall pro sémanticky podobné, ale jinak formulované dotazy.

---

## Maintenance (čištění paměti)

### Ruční spuštění

```python
from memory import E.V.Memory
from config import CONFIG

memory = E.V.Memory(CONFIG)
result = memory.run_maintenance()
print(result)
# {"removed": 23, "decayed": 145, "avg_importance": 0.61, "total": 824}
```

### Automatické spuštění

Maintenance běží automaticky každou hodinu přes Scheduler:
- Poprvé 5 minut po startu E.V.
- Pak každou hodinu (3600 sekund)
- **Nikdy neblokuje** uživatelský dotaz — běží v background threadu

### Co maintenance dělá

1. Aplikuje decay na všechny paměti (`importance *= exp(-decay * age)`)
2. Smaže paměti pod prahem (`importance < 0.05`)
3. Smaže paměti s vypršeným TTL (`expires_at < now`)
4. Vrátí statistiky

---

## UserProfile

Persistentní profil uživatele uložený v `memory_data/user_profile.json`.

### Co se ukládá automaticky

- Jméno (z frází jako "Jmenuji se...", "Jsem...")
- Technologie (z "Pracuji s Pythonem", "Programuji v Rustu")
- Lokalita (z "Bydlím v Praze")
- Preference (z "Mám rád...", "Preferuji...")

### Ruční uložení

```
"Zapamatuj si, že jsem vývojář v Pythonu a pracuji na E.V. projektu"
```

### Injekce do LLM

Souhrn profilu se přidá do systémového promptu při každém dotazu:

```
Profil uživatele:
- Jméno: Šimon
- Technologie: Python, FastAPI, React
- Projekt: E.V. AI asistent
- Preference: tmavé téma, stručné odpovědi
```

---

## API pro práci s pamětí

### Uložení

```python
from memory import E.V.Memory
from config import CONFIG

memory = E.V.Memory(CONFIG)

# Uloží konverzaci
memory.store_conversation(
    user_text="Jak se jmenuješ?",
    response="Jmenuji se E.V..",
    importance=0.6  # 0.0–1.0
)

# Uloží fakt přímo
memory.store_fact(
    "Uživatel pracuje jako Python developer",
    importance=0.9,
    tags=["profil", "technologie"]
)
```

### Vybavení

```python
# Sémantické vyhledávání
context = memory.recall_context("python projekt", top_k=5)
print(context)
# "Uživatel pracuje jako Python developer (důležitost: 0.9)
#  Pracuji na E.V. projektu (0.8)
#  ..."

# Přímý SQL dotaz (pokročilé)
store = memory._store  # _SQLiteMemoryStore instance
rows = store.recall(query="python", top_k=10, min_importance=0.5)
```

---

## Work Timeline

Kromě konverzační paměti E.V. sleduje **pracovní aktivitu** na počítači.

### Úložiště

- Soubor: `~/.jarvis/activity.db` (SQLite)
- Modul: `activity_store.py`
- Kolektor: `activity_collector.py` (background thread, interval 20s)

### Sledované události

| Typ | Příklad |
|-----|---------|
| `app.open` / `app.focus` | VS Code, Chrome, Cursor |
| `git.commit` / `git.push` | Automaticky z git log |
| `docker.start` / `docker.stop` | Docker events |
| `build.fail` / `build.success` | Detekce z terminálu |
| `command.run` / `command.done` | Uživatelské příkazy |
| `proactive.suggestion` | CPU alert, Docker RAM |

### Dotazy

```
"Co jsem dělal dnes?"
"Na čem jsem skončil?"
"Kolik času jsem strávil na projektu E.V.?"
"Jaké bugy jsem řešil?"
```

API: `GET /api/activity/query?q=...`

### DailySummarizer integrace

Večerní shrnutí (`DailySummarizer` v `memory.py`) zahrnuje i pracovní aktivitu — nejen chat konverzace.
