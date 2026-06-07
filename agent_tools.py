"""
JARVIS — Agent Tools Registry
Definuje nástroje dostupné ReAct agentovi. Každý nástroj je wrapper
nad existujícím CommandExecutor nebo MCPBridge — žádná duplicita logiky.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolParam:
    name:        str
    description: str
    required:    bool = True
    type:        str  = "string"


@dataclass
class Tool:
    name:        str
    description: str
    params:      List[ToolParam]
    fn:          Callable[..., str]
    examples:    List[str] = field(default_factory=list)

    def call(self, **kwargs) -> str:
        try:
            return self.fn(**kwargs)
        except Exception as e:
            logger.error(f"Tool '{self.name}' chyba: {e}")
            return f"Chyba nástroje {self.name}: {e}"

    def schema(self) -> str:
        params = ", ".join(
            f"{p.name}: {p.type}{'?' if not p.required else ''}"
            for p in self.params
        )
        return f"{self.name}({params}) — {self.description}"


class ToolRegistry:
    """Registr všech nástrojů dostupných agentovi."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def schema_block(self) -> str:
        """Vrátí text pro systémový prompt — seznam nástrojů."""
        lines = ["Dostupné nástroje:"]
        for t in self._tools.values():
            lines.append(f"  - {t.schema()}")
            for ex in t.examples[:1]:
                lines.append(f"    Příklad: {ex}")
        return "\n".join(lines)

    def ollama_tools_schema(self) -> list:
        """Vrátí Ollama-kompatibilní tool schema pro nativní tool-calling.

        Formát dle Ollama /api/chat docs:
        https://ollama.com/blog/tool-support
        """
        tools = []
        for t in self._tools.values():
            properties = {}
            required = []
            for p in t.params:
                prop: dict = {"type": p.type if p.type in ("string", "number", "boolean", "integer") else "string"}
                if hasattr(p, "description") and p.description:
                    prop["description"] = p.description
                properties[p.name] = prop
                if p.required:
                    required.append(p.name)
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return tools


COPILOT_TOOL_NAMES = (
    "open_app", "screenshot", "pc_overview", "get_time",
    "weather", "search_web", "system_info",
)


def build_copilot_registry(executor, mcp_bridge=None) -> ToolRegistry:
    """Malá sada nástrojů pro Copilot LLM path (Ollama tool-calling)."""
    reg = ToolRegistry()
    ex = executor

    reg.register(Tool(
        name="open_app",
        description="Spustí aplikaci (chromium, spotify, vscode…)",
        params=[ToolParam("app", "Název aplikace")],
        fn=lambda app: ex.execute("open_app", {"app": app}),
        examples=['open_app(app="chromium")'],
    ))

    reg.register(Tool(
        name="screenshot",
        description="Pořídí screenshot a uloží na plochu",
        params=[],
        fn=lambda: ex.execute("screenshot", {}),
        examples=["screenshot()"],
    ))

    reg.register(Tool(
        name="pc_overview",
        description="Kompletní přehled PC — CPU, RAM, disk, okna, procesy",
        params=[],
        fn=lambda: ex.execute("pc_overview", {}),
        examples=["pc_overview()"],
    ))

    reg.register(Tool(
        name="get_time",
        description="Vrátí aktuální čas",
        params=[],
        fn=lambda: ex.execute("get_time", {}),
        examples=["get_time()"],
    ))

    reg.register(Tool(
        name="weather",
        description="Vrátí aktuální počasí pro město",
        params=[ToolParam("city", "Název města", required=False)],
        fn=lambda city="": ex.execute("weather", {"city": city}),
        examples=['weather(city="Praha")'],
    ))

    if mcp_bridge and mcp_bridge.is_available("brave-search"):
        reg.register(Tool(
            name="search_web",
            description="Vyhledá na webu a vrátí výsledky",
            params=[ToolParam("query", "Co hledat")],
            fn=lambda query: mcp_bridge.call_tool(
                "brave-search", "brave_web_search", {"query": query, "count": 5}),
            examples=['search_web(query="cena RTX 4090")'],
        ))
    else:
        reg.register(Tool(
            name="search_web",
            description="Otevře Google vyhledávání v prohlížeči",
            params=[ToolParam("query", "Co hledat")],
            fn=lambda query: ex.execute("search_web", {"query": query}),
            examples=['search_web(query="cena RTX 4090")'],
        ))

    reg.register(Tool(
        name="system_info",
        description="Základní systémové informace — OS, hostname, CPU, RAM",
        params=[],
        fn=lambda: ex.execute("system_info", {}),
        examples=["system_info()"],
    ))

    return reg


def build_registry(executor, mcp_bridge=None) -> ToolRegistry:
    """
    Sestaví ToolRegistry z existujícího CommandExecutoru a MCPBridge.
    Volá se jednou při inicializaci agenta.
    """
    reg = ToolRegistry()
    ex  = executor

    # ── Vyhledávání ──────────────────────────────────────────────

    if mcp_bridge and mcp_bridge.is_available("brave-search"):
        reg.register(Tool(
            name="web_search",
            description="Vyhledá na webu přes Brave Search a vrátí výsledky",
            params=[ToolParam("query", "Co hledat")],
            fn=lambda query: mcp_bridge.call_tool(
                "brave-search", "brave_web_search", {"query": query, "count": 5}),
            examples=['web_search(query="cena RTX 4090 2025")'],
        ))
    else:
        reg.register(Tool(
            name="web_search",
            description="Otevře Google vyhledávání v prohlížeči",
            params=[ToolParam("query", "Co hledat")],
            fn=lambda query: ex.execute("search_web", {"query": query}),
            examples=['web_search(query="cena RTX 4090")'],
        ))

    if mcp_bridge and mcp_bridge.is_available("fetch"):
        reg.register(Tool(
            name="fetch_url",
            description="Stáhne obsah webové stránky a vrátí text",
            params=[ToolParam("url", "URL stránky")],
            fn=lambda url: mcp_bridge.call_tool(
                "fetch", "fetch", {"url": url}),
            examples=['fetch_url(url="https://example.com/cenik")'],
        ))

    # ── Soubory a paměť ──────────────────────────────────────────

    reg.register(Tool(
        name="note_add",
        description="Uloží poznámku do souboru ~/jarvis_notes.txt",
        params=[ToolParam("note", "Text poznámky")],
        fn=lambda note: ex.execute("note_add", {"note": note}),
        examples=['note_add(note="RTX 4090 stojí 35 000 Kč")'],
    ))

    reg.register(Tool(
        name="note_list",
        description="Zobrazí uložené poznámky",
        params=[],
        fn=lambda: ex.execute("note_list", {}),
        examples=["note_list()"],
    ))

    reg.register(Tool(
        name="memory_store",
        description="Uloží informaci do dlouhodobé paměti",
        params=[ToolParam("content", "Co uložit"),
                ToolParam("importance", "Důležitost 0.0–1.0", required=False)],
        fn=lambda content, importance=0.7: ex.execute(
            "memory_store", {"content": content, "importance": importance}),
        examples=['memory_store(content="Uživatel má rád Python")'],
    ))

    reg.register(Tool(
        name="memory_recall",
        description="Vyhledá v dlouhodobé paměti",
        params=[ToolParam("query", "Co hledat")],
        fn=lambda query: ex.execute("memory_recall", {"query": query, "top_k": 5}),
        examples=['memory_recall(query="oblíbené programovací jazyky")'],
    ))

    # ── Systém ───────────────────────────────────────────────────

    reg.register(Tool(
        name="get_time",
        description="Vrátí aktuální čas",
        params=[],
        fn=lambda: ex.execute("get_time", {}),
        examples=["get_time()"],
    ))

    reg.register(Tool(
        name="get_pc_overview",
        description="Kompletní přehled PC — CPU, RAM, disk, okna, procesy",
        params=[],
        fn=lambda: ex.execute("pc_overview", {}),
        examples=["get_pc_overview()"],
    ))

    reg.register(Tool(
        name="get_weather",
        description="Vrátí aktuální počasí pro město",
        params=[ToolParam("city", "Název města", required=False)],
        fn=lambda city="": ex.execute("weather", {"city": city}),
        examples=['get_weather(city="Praha")'],
    ))

    reg.register(Tool(
        name="calculate",
        description="Vypočítá matematický výraz v sandboxu",
        params=[ToolParam("expression", "Matematický výraz")],
        fn=lambda expression: ex.execute("calculate", {"expression": expression}),
        examples=['calculate(expression="15% z 25000")'],
    ))

    reg.register(Tool(
        name="open_url",
        description="Otevře URL v prohlížeči",
        params=[ToolParam("url", "Webová adresa")],
        fn=lambda url: ex.execute("open_url", {"url": url}),
        examples=['open_url(url="https://moodle.sspu-opava.cz")'],
    ))

    reg.register(Tool(
        name="open_app",
        description="Spustí aplikaci (chromium, spotify, vscode…)",
        params=[ToolParam("app", "Název aplikace")],
        fn=lambda app: ex.execute("open_app", {"app": app}),
        examples=['open_app(app="chromium")'],
    ))

    reg.register(Tool(
        name="screenshot",
        description="Pořídí screenshot a uloží na plochu",
        params=[],
        fn=lambda: ex.execute("screenshot", {}),
        examples=["screenshot()"],
    ))

    # ── Vision Computer Use ───────────────────────────────────────
    reg.register(Tool(
        name="ui_click",
        description="Najde UI element popsaný textem na obrazovce a klikne na něj (vision-guided)",
        params=[ToolParam("element", "Popis elementu, např. 'tlačítko Přihlásit' nebo 'vyhledávací pole'")],
        fn=lambda element: _vision_click(element),
        examples=['ui_click(element="tlačítko Odeslat")'],
    ))

    reg.register(Tool(
        name="ui_type",
        description="Napíše text do aktivního pole (po ui_click nebo find_and_fill)",
        params=[ToolParam("text", "Text k napsání")],
        fn=lambda text: _vision_type(text),
        examples=['ui_type(text="hello@example.com")'],
    ))

    reg.register(Tool(
        name="ui_fill",
        description="Najde formulářové pole a vyplní ho hodnotou (vision-guided)",
        params=[
            ToolParam("field", "Popis pole, např. 'pole pro e-mail'"),
            ToolParam("value", "Hodnota k vyplnění"),
        ],
        fn=lambda field, value: _vision_fill(field, value),
        examples=['ui_fill(field="pole pro e-mail", value="user@example.com")'],
    ))

    reg.register(Tool(
        name="ui_task",
        description="Autonomně splní UI úkol: otevře prohlížeč, kliká, vyplňuje formuláře",
        params=[ToolParam("task", "Popis úkolu, např. 'Najdi nejlevnější letenky do Paříže'")],
        fn=lambda task: _vision_task(task),
        examples=['ui_task(task="Otevři gmail.com a přečti první nepřečtený e-mail")'],
    ))


    reg.register(Tool(
        name="wiki_search",
        description="Vyhledá na Wikipedii a vrátí shrnutí",
        params=[ToolParam("query", "Co hledat")],
        fn=lambda query: ex.execute("wiki_search", {"query": query}),
        examples=['wiki_search(query="Python programovací jazyk")'],
    ))

    # ── Filesystem MCP (pokud dostupné) ──────────────────────────

    if mcp_bridge and mcp_bridge.is_available("filesystem"):
        reg.register(Tool(
            name="read_file",
            description="Přečte obsah souboru",
            params=[ToolParam("path", "Cesta k souboru")],
            fn=lambda path: mcp_bridge.call_tool(
                "filesystem", "read_file", {"path": path}),
            examples=['read_file(path="~/notes.txt")'],
        ))

        reg.register(Tool(
            name="list_files",
            description="Zobrazí obsah složky",
            params=[ToolParam("path", "Cesta ke složce")],
            fn=lambda path: mcp_bridge.call_tool(
                "filesystem", "list_directory", {"path": path}),
            examples=['list_files(path="~/Dokumenty")'],
        ))

    return reg


# ── Vision Computer Use helpers (module-level) ────────────────────────────────

def _vision_click(element: str) -> str:
    try:
        from vision_computer_use import get_vision_agent
        r = get_vision_agent().click(element)
        return "ok" if r.success else f"Selhalo: {r.error}"
    except ImportError:
        return "vision_computer_use: pyautogui není nainstalováno (pip install pyautogui pillow)"
    except Exception as e:
        return f"Chyba: {e}"


def _vision_type(text: str) -> str:
    try:
        from vision_computer_use import get_vision_agent
        r = get_vision_agent().type_text(text)
        return "ok" if r.success else f"Selhalo: {r.error}"
    except Exception as e:
        return f"Chyba: {e}"


def _vision_fill(field: str, value: str) -> str:
    try:
        from vision_computer_use import get_vision_agent
        r = get_vision_agent().find_and_fill(field, value)
        return "ok" if r.success else f"Selhalo: {r.error}"
    except Exception as e:
        return f"Chyba: {e}"


def _vision_task(task: str) -> str:
    try:
        from vision_computer_use import get_vision_agent
        return get_vision_agent().run_task(task)
    except ImportError:
        return "vision_computer_use: pyautogui není nainstalováno (pip install pyautogui pillow)"
    except Exception as e:
        return f"Chyba: {e}"
