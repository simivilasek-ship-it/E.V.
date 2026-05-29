"""
JARVIS — ReAct Agent
Implementuje Reasoning + Acting smyčku pro vícesvůlové úkoly.

Formát:
  Thought: [co si agent myslí]
  Action: tool_name(param="hodnota")
  Observation: [výsledek nástroje]
  ... opakuj max MAX_STEPS krát ...
  Answer: [finální odpověď uživateli]

Napojení:
  ReactAgent.run(text) → str  (finální odpověď)
  ReactAgent.should_handle(text) → bool  (je to vícesvůlový úkol?)
"""
from __future__ import annotations

import json
import logging
import re
import requests
import threading
from typing import TYPE_CHECKING, List, Optional

from commands.utils import normalize_text as _norm
from llm import OllamaClient

if TYPE_CHECKING:
    from agent_tools import ToolRegistry

logger = logging.getLogger(__name__)

MAX_STEPS   = 6      # max kol Thought→Action→Observation
MAX_TOKENS  = 600    # max tokenů na jeden LLM call


# ── Detekce vícesvůlových úkolů ──────────────────────────────────

_MULTI_STEP = re.compile(
    r"\b("
    r"(najdi|vyhledej|zjisti).{0,40}(uloz|zapis|poznamen|rekni|otevre|posli)"
    r"|(uloz|zapis).{0,40}(co|ktery|jaky|nalezl|vysledek)"
    r"|(porovnej|srovnej).{1,60}(cen|model|verz)"
    r"|(zkontroluj|over).{1,50}(a\s+pak|potom|nasledne)"
    r"|(udel|proved).{1,30}(a\s+potom|a\s+taky|a\s+take)"
    r"|(kolik\s+stoji|cena).{1,50}(uloz|zapamatuj|poznamen)"
    r")",
    re.IGNORECASE | re.UNICODE,
)


def should_handle(text: str) -> bool:
    """True pokud text vypadá jako vícesvůlový úkol pro agenta."""
    return bool(_MULTI_STEP.search(_norm(text)))


# ── Parsování Action řádku ────────────────────────────────────────

_ACTION_RE = re.compile(
    r"Action:\s*(\w+)\(([^)]*)\)",
    re.IGNORECASE,
)

_ANSWER_RE = re.compile(
    r"Answer:\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_action(line: str):
    """Vrátí (tool_name, kwargs) nebo None."""
    m = _ACTION_RE.search(line)
    if not m:
        return None
    tool_name = m.group(1).strip()
    raw_args  = m.group(2).strip()

    kwargs: dict = {}
    if raw_args:
        # Parsuj: key="value" nebo key='value' nebo key=value
        for kv in re.finditer(r'(\w+)\s*=\s*"([^"]*?)"|(\w+)\s*=\s*\'([^\']*?)\'|(\w+)\s*=\s*([^\s,)]+)', raw_args):
            k = kv.group(1) or kv.group(3) or kv.group(5)
            v = kv.group(2) or kv.group(4) or kv.group(6)
            if v is not None:
                # Pokus o konverzi čísel
                try:
                    v = float(v) if "." in v else int(v)
                except ValueError:
                    pass
                kwargs[k] = v
    return tool_name, kwargs


# ── ReAct Agent ──────────────────────────────────────────────────

class ReactAgent:
    """
    ReAct agent — Thought → Action → Observation smyčka.
    Volá Ollama LLM pro Thought, pak spustí příslušný nástroj.
    """

    SYSTEM_PROMPT = """\
Jsi JARVIS, inteligentní AI asistent. Pro splnění úkolu používáš nástroje.

Formát odpovědi (opakuj dokud úkol není hotov):
  Thought: [co si myslíš o dalším kroku]
  Action: název_nástroje(parametr="hodnota")
  Observation: [výsledek — doplní systém]
  Thought: [co dál]
  ...
  Answer: [finální odpověď uživateli česky]

Pravidla:
- Vždy začni Thought:
- Každý Action: musí být na samostatném řádku v přesném formátu tool(param="hodnota")
- Po Observation: pokračuj dalším Thought:
- Když máš vše potřebné, ukonči Answer:
- Nikdy nevymýšlej výsledky — použij nástroj
- Maximálně {max_steps} kroků

{tools}
"""

    def __init__(self, registry: "ToolRegistry", ollama_url: str, model: str):
        self.registry    = registry
        self.ollama_url  = ollama_url
        self.model       = model
        self._client     = OllamaClient(ollama_url, model)
        self._system     = self.SYSTEM_PROMPT.format(
            max_steps=MAX_STEPS,
            tools=registry.schema_block(),
        )

    def run(self, user_text: str, on_step: Optional[callable] = None) -> str:
        """
        Spustí ReAct smyčku a vrátí finální odpověď.
        on_step(step_text) je voláno po každém Observation pro live feedback.
        """
        messages = [
            {"role": "system",  "content": self._system},
            {"role": "user",    "content": user_text},
        ]
        trace: List[str] = []

        for step in range(MAX_STEPS):
            raw = self._llm(messages)
            if not raw:
                break

            logger.debug(f"ReAct step {step}: {raw[:120]}")

            # Zkontroluj Answer: — hotovo
            ans_m = _ANSWER_RE.search(raw)
            if ans_m and "Action:" not in raw[raw.find("Answer:"):]:
                return ans_m.group(1).strip()

            # Najdi Action:
            action_m = _ACTION_RE.search(raw)
            if not action_m:
                # LLM neposkytl akci ani odpověď — pokud je tam text, vrátíme ho
                if raw.strip():
                    return raw.strip()
                break

            tool_name = action_m.group(1).strip()
            parsed    = _parse_action(raw)
            if not parsed:
                observation = f"Chyba: nepodařilo se parsovat Action: {action_m.group(0)}"
            else:
                _, kwargs  = parsed
                tool       = self.registry.get(tool_name)
                if tool is None:
                    observation = f"Chyba: nástroj '{tool_name}' neexistuje. Dostupné: {[t.name for t in self.registry.all()]}"
                else:
                    observation = tool.call(**kwargs)
                    # Zkrať dlouhé výsledky
                    if len(observation) > 1200:
                        observation = observation[:1200] + "…[zkráceno]"

            step_text = f"[{tool_name}] → {observation[:80]}…" if len(observation) > 80 else f"[{tool_name}] → {observation}"
            trace.append(step_text)
            if on_step:
                on_step(step_text)

            # Přidej do kontextu
            messages.append({"role": "assistant",  "content": raw})
            messages.append({"role": "user",       "content": f"Observation: {observation}"})

        logger.warning(f"ReAct: dosažen limit {MAX_STEPS} kroků nebo žádná Answer")
        return "Nepodařilo se dokončit úkol v časovém limitu. " + (
            "Kroky: " + " → ".join(trace) if trace else ""
        )

    def _llm(self, messages: list) -> str:
        return self._client.call(messages, temperature=0.2, max_tokens=MAX_TOKENS)


# ── Singleton factory ─────────────────────────────────────────────

_agent: Optional[ReactAgent] = None
_agent_lock = threading.Lock()


def get_react_agent(executor=None, mcp_bridge=None,
                    ollama_url: str = "http://localhost:11434/api/chat",
                    model: str = "qwen2.5:3b") -> Optional[ReactAgent]:
    """Vrátí singleton ReactAgent. Thread-safe, vytvoří ho při prvním volání."""
    global _agent
    with _agent_lock:
        if _agent is None:
            if executor is None:
                return None
            from agent_tools import build_registry
            registry = build_registry(executor, mcp_bridge)
            _agent   = ReactAgent(registry, ollama_url, model)
            logger.info(f"ReactAgent inicializován s {len(registry.all())} nástroji")
    return _agent


def reset_agent():
    """Zruší singleton — použij při reinicializaci (testy, změna konfigurace)."""
    global _agent
    with _agent_lock:
        _agent = None
