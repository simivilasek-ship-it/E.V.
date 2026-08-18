# Vývoj pluginů pro E.V.

Plugin je Python balíček v adresáři `plugins/custom/<název>/` s manifestem a entry pointem. Pluginy mohou přidávat nové příkazy, nástroje pro agenty, API endpointy nebo background workery.

---

## Struktura pluginu

```
plugins/custom/muj-plugin/
├── manifest.json      ← popis pluginu (povinný)
├── plugin.py          ← hlavní kód (povinný)
├── README.md          ← dokumentace (doporučeno)
└── requirements.txt   ← extra závislosti (volitelné)
```

---

## manifest.json

```json
{
  "name": "muj-plugin",
  "version": "1.0.0",
  "description": "Stručný popis co plugin dělá",
  "author": "Vaše jméno",
  "min_jarvis_version": "5.0",
  "tags": ["productivity", "tools"],
  "permissions": ["SAFE"],
  "actions": ["muj_prikaz"],
  "entry": "plugin.py"
}
```

**Pole manifestu:**

| Pole | Povinné | Popis |
|------|---------|-------|
| `name` | ✅ | Unikátní název (lowercase, pomlčky) |
| `version` | ✅ | Sémantická verze (`X.Y.Z`) |
| `description` | ✅ | Max 100 znaků |
| `author` | ✅ | Jméno nebo GitHub username |
| `actions` | ✅ | Seznam akcí které plugin přidává |
| `permissions` | — | Úrovně oprávnění: `SAFE`, `STANDARD`, `ELEVATED` |
| `entry` | — | Vstupní soubor (výchozí: `plugin.py`) |
| `tags` | — | Tagy pro filtrování v Marketplace |

---

## plugin.py — základní šablona

```python
"""
muj-plugin — stručný popis
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MujPlugin:
    """
    Hlavní třída pluginu.
    E.V. automaticky zavolá register() po načtení.
    """

    name    = "muj-plugin"
    version = "1.0.0"

    def __init__(self, config: dict):
        self.config = config
        logger.info(f"MujPlugin inicializován")

    # ── Akce volaná z E.V. příkazů ─────────────────

    def muj_prikaz(self, arg: str = "", **kwargs) -> str:
        """
        Zpracuje příkaz a vrátí textový výsledek.

        Args:
            arg: Argument extrahovaný z příkazu uživatele
            **kwargs: Dodatečné parametry od CommandExecutor

        Returns:
            Textový výsledek zobrazený uživateli
        """
        logger.info(f"muj_prikaz volán s arg={arg!r}")
        return f"Výsledek pro: {arg}"

    # ── Registrace do E.V. ekosystému ──────────────

    def register(self, registry) -> None:
        """
        Registruje plugin do E.V..
        Voláno automaticky po načtení pluginu.

        Args:
            registry: PluginRegistry instance
        """
        # Registruj akci
        registry.register_action(
            name="muj_prikaz",
            fn=self.muj_prikaz,
            description="Provede mou akci s daným argumentem",
            permission="SAFE",
        )

        # Volitelně: přidej trigger do lokálního routeru
        registry.add_trigger(
            pattern=r"\b(udělej|proved)\s+(.+)",
            action="muj_prikaz",
            arg_group=2,
        )

        logger.info("MujPlugin registrován")


def create_plugin(config: dict) -> MujPlugin:
    """Factory funkce — E.V. ji volá pro vytvoření instance."""
    return MujPlugin(config)
```

---

## Typy pluginů

### 1. Plugin s novým příkazem

Nejjednodušší typ — přidá trigger v češtině a implementaci.

```python
# V register():
registry.register_action(
    name="pocasí",
    fn=lambda city="Praha", **_: get_weather(city),
    description="Zjistí počasí ve městě",
    permission="SAFE",
)
registry.add_trigger(
    pattern=r"\bpočasí\s+(?:v\s+)?(.+)",
    action="pocasí",
    arg_group=1,
)
```

### 2. Plugin s API endpointem

Plugin může přidat vlastní FastAPI endpoint.

```python
def register(self, registry) -> None:
    try:
        from dashboard import app as fastapi_app

        @fastapi_app.get("/api/muj-plugin/data")
        async def get_data():
            return {"data": self._get_data()}

    except Exception as e:
        logger.warning(f"Nepodařilo se zaregistrovat API endpoint: {e}")
```

### 3. Plugin jako nástroj pro agenty

Plugin může registrovat nástroj do `agent_tools.py` — agent ho pak může autonomně volat.

```python
def register(self, registry) -> None:
    try:
        from agent_tools import ToolRegistry, Tool, ToolParam

        tool = Tool(
            name="muj_nastroj",
            description="Detailní popis co nástroj dělá a kdy ho agent má použít",
            params=[
                ToolParam("query", "Co hledat nebo zpracovat"),
                ToolParam("limit", "Max počet výsledků", required=False),
            ],
            fn=lambda query, limit=10, **_: self.search(query, int(limit)),
            examples=[
                'muj_nastroj(query="Python async patterns", limit=5)',
            ],
        )
        # Přidej do globálního registru nástrojů
        registry.register_agent_tool(tool)

    except Exception as e:
        logger.debug(f"Agent tool registrace selhala: {e}")
```

### 4. Plugin s background workerem

Plugin může spustit vlastní background thread.

```python
import threading
import time

class MonitorPlugin:

    def __init__(self, config):
        self.config  = config
        self._running = False
        self._thread: threading.Thread | None = None

    def start_monitoring(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="MonitorPlugin")
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                self._check()
            except Exception as e:
                logger.warning(f"Monitor chyba: {e}")
            time.sleep(60)

    def _check(self):
        # Vaše logika monitorování
        pass

    def register(self, registry):
        registry.register_action("start_monitor", lambda **_: self._start_and_reply())

    def _start_and_reply(self) -> str:
        self.start_monitoring()
        return "Monitor spuštěn na pozadí."
```

---

## Zabezpečení pluginů

### Úrovně oprávnění

Každá akce pluginu musí deklarovat úroveň oprávnění:

| Úroveň | Použití | Příklady |
|--------|---------|---------|
| `SAFE` | Akce bez vedlejších efektů | Kalkulace, výpis informací, vyhledávání |
| `STANDARD` | Akce s malými vedlejšími efekty | Zápis souboru, otevření aplikace |
| `ELEVATED` | Potenciálně nebezpečné akce | Smazání souboru, síťové volání, spuštění příkazu |
| `FORBIDDEN` | Vždy zakázáno | — |

```python
# ELEVATED akce vyžaduje potvrzení uživatele v interaktivním režimu
registry.register_action(
    name="smazat_soubory",
    fn=self.delete_files,
    description="Smaže soubory dle vzoru",
    permission="ELEVATED",  # Uživatel musí potvrdit!
)
```

### Sandbox spuštění

Pluginy ze Marketplace jsou spouštěny v izolovaném sandboxu:

```python
from plugin_marketplace import PluginMarketplace

mp = PluginMarketplace()
result = mp.run_sandboxed(
    "muj-plugin",
    entry="plugin.py",
    timeout=30,      # max 30 sekund
    memory_mb=256,   # max 256 MB RAM
)
print(result["stdout"])
```

Sandbox nastavuje env proměnnou `JARVIS_SANDBOX=1` — plugin ji může detekovat:

```python
import os
if os.environ.get("JARVIS_SANDBOX"):
    # Omezený režim — nevolat destruktivní operace
    pass
```

---

## Testování pluginu

```python
# tests/test_muj_plugin.py
import pytest
from plugins.custom.muj_plugin.plugin import MujPlugin


@pytest.fixture
def plugin():
    return MujPlugin(config={})


def test_muj_prikaz_basic(plugin):
    result = plugin.muj_prikaz("test vstup")
    assert "test vstup" in result


def test_muj_prikaz_empty(plugin):
    result = plugin.muj_prikaz("")
    assert isinstance(result, str)
    assert len(result) > 0


def test_plugin_metadata(plugin):
    assert plugin.name == "muj-plugin"
    assert plugin.version.count(".") == 2  # sémantická verze
```

Spuštění testů:
```bash
pytest tests/test_muj_plugin.py -v
```

---

## Publikování do Marketplace

### 1. Přidej do REGISTRY v `plugin_marketplace.py`

```python
REGISTRY = {
    # ... existující pluginy ...
    "muj-plugin": {
        "repo":        "vaše-github-username/jarvis-plugin-muj",
        "description": "Stručný popis do 80 znaků",
        "author":      "Vaše jméno",
        "version":     "1.0.0",
        "rating":      0.0,
        "downloads":   0,
        "tags":        ["productivity"],
        "builtin":     False,
    },
}
```

### 2. Publikuj na GitHub

Repozitář musí mít strukturu:
```
jarvis-plugin-muj/
├── manifest.json
├── plugin.py
├── README.md
└── tests/
    └── test_plugin.py
```

### 3. Instalace uživateli

```
"Nainstaluj plugin muj-plugin"
# nebo přes Marketplace UI v dashboardu
```

---

## Příklady existujících pluginů

### `plugins/builtin/calculator/`
Jednoduchý příklad SAFE pluginu s math evaluací.

### `plugins/builtin/timer/`
Příklad pluginu s background workerem (countdown) a TTS notifikací.

### `plugins/builtin/clipboard/`
Příklad STANDARD pluginu pracujícího se systémem (clipboard).
