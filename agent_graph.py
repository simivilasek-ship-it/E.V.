"""
JARVIS — Graf agenta (LangGraph styl)
Stavový graf se 4 uzly: Planner → Router → Executor → Critic.

Výhody oproti lineárnímu ReAct:
- Planner nejdřív rozdělí úkol na pojmenované kroky
- Critic kontroluje každý výsledek a může přeplánovat
- Transparentní stav (co bylo hotovo, co zbývá)
- Lepší recovery při selhání nástroje

Tok:
  START → Planner → Router ─→ Executor → Critic ─→ Router (opakuj)
                       └─→ DONE
"""
from __future__ import annotations

import json
import logging
import re
import requests
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional

if TYPE_CHECKING:
    from agent_tools import ToolRegistry

logger = logging.getLogger(__name__)

MAX_STEPS    = 8     # max Executor volání celkem
MAX_RETRIES  = 2     # max opakování jednoho kroku při chybě
MAX_REPLANS  = 1     # max přeplánování při záseknutí
LLM_TOKENS   = 500


# ── Stav grafu ────────────────────────────────────────────────────

class NodeStatus(str, Enum):
    PLANNING   = "planning"
    ROUTING    = "routing"
    EXECUTING  = "executing"
    CRITICIZING = "criticizing"
    DONE       = "done"
    FAILED     = "failed"


@dataclass
class AgentState:
    task:            str
    plan:            List[str]        = field(default_factory=list)
    step_idx:        int              = 0
    observations:    List[str]        = field(default_factory=list)
    retry_count:     int              = 0
    replan_count:    int              = 0
    exec_count:      int              = 0
    last_tool:       str              = ""
    last_result:     str              = ""
    final_answer:    str              = ""
    status:          NodeStatus       = NodeStatus.PLANNING
    on_step:         Optional[Callable] = field(default=None, repr=False)

    def current_step(self) -> str:
        if self.step_idx < len(self.plan):
            return self.plan[self.step_idx]
        return ""

    def steps_summary(self) -> str:
        lines = []
        for i, s in enumerate(self.plan):
            if i < self.step_idx:
                obs = self.observations[i] if i < len(self.observations) else "hotovo"
                lines.append(f"  ✓ {s} → {obs[:60]}")
            elif i == self.step_idx:
                lines.append(f"  ▶ {s}")
            else:
                lines.append(f"  ○ {s}")
        return "\n".join(lines) if lines else "(prázdný plán)"

    def notify(self, msg: str):
        logger.debug(f"[Graf] {msg}")
        if self.on_step:
            self.on_step(msg)


# ── Systémové prompty uzlů ────────────────────────────────────────

_PLANNER_PROMPT = """\
Jsi JARVIS plánovač. Rozděl úkol na 2–5 konkrétních kroků.

Vrať POUZE JSON pole kroků, nic jiného:
["krok 1", "krok 2", "krok 3"]

Každý krok musí být konkrétní akce (vyhledej X, ulož Y, otevři Z).
Maximálně 5 kroků. Žádné vysvětlování.
"""

_ROUTER_PROMPT = """\
Jsi JARVIS router. Rozhodneš co udělat s aktuálním krokem.

Dostupné nástroje:
{tools}

Aktuální krok: {step}
Hotové kroky a výsledky:
{history}

Vrať POUZE JSON na jednom řádku:
{{"tool": "nazev_nastroje", "args": {{"param": "hodnota"}}}}

NEBO pokud jsou všechny kroky hotovy:
{{"tool": "DONE", "args": {{"answer": "finální odpověď česky"}}}}

Nic jiného nevypisuj.
"""

_CRITIC_PROMPT = """\
Jsi JARVIS kritik. Zhodnoť výsledek nástroje.

Krok: {step}
Výsledek: {result}

Vrať POUZE jedno z:
OK — výsledek je uspokojivý, pokračuj dalším krokem
RETRY — výsledek je chybný nebo prázdný, zkus znovu
REPLAN — úkol nelze splnit tímto způsobem, přeplánuj

Nic jiného nevypisuj.
"""


# ── Graf ─────────────────────────────────────────────────────────

class AgentGraph:
    """Stavový graf agenta se 4 uzly."""

    def __init__(self, registry: "ToolRegistry", ollama_url: str, model: str):
        self.registry   = registry
        self.ollama_url = ollama_url
        self.model      = model

    # ── Veřejné API ──────────────────────────────────────────────

    def run(self, task: str, on_step: Optional[Callable] = None) -> str:
        state = AgentState(task=task, on_step=on_step)
        state.notify(f"Plánuji: {task[:60]}")

        while state.status not in (NodeStatus.DONE, NodeStatus.FAILED):
            if state.exec_count >= MAX_STEPS:
                state.final_answer = (
                    "Dosažen limit kroků. Částečný výsledek:\n" +
                    state.steps_summary()
                )
                state.status = NodeStatus.DONE
                break

            if state.status == NodeStatus.PLANNING:
                self._node_planner(state)
            elif state.status == NodeStatus.ROUTING:
                self._node_router(state)
            elif state.status == NodeStatus.EXECUTING:
                self._node_executor(state)
            elif state.status == NodeStatus.CRITICIZING:
                self._node_critic(state)

        return state.final_answer or "Úkol dokončen."

    # ── Uzel: Planner ────────────────────────────────────────────

    def _node_planner(self, state: AgentState):
        raw = self._llm([
            {"role": "system", "content": _PLANNER_PROMPT},
            {"role": "user",   "content": state.task},
        ])

        plan = self._parse_json_list(raw)
        if not plan:
            # Fallback — jeden krok = celý úkol
            plan = [state.task]

        state.plan      = plan
        state.step_idx  = 0
        state.status    = NodeStatus.ROUTING
        state.notify(f"Plán ({len(plan)} kroků): " + " → ".join(plan[:3]))

    # ── Uzel: Router ─────────────────────────────────────────────

    def _node_router(self, state: AgentState):
        if state.step_idx >= len(state.plan):
            # Všechny kroky hotovy — generuj finální odpověď
            state.final_answer = self._synthesize(state)
            state.status       = NodeStatus.DONE
            return

        tools_schema = self.registry.schema_block()
        history      = state.steps_summary()

        raw = self._llm([
            {"role": "system", "content": _ROUTER_PROMPT.format(
                tools=tools_schema,
                step=state.current_step(),
                history=history,
            )},
            {"role": "user", "content": f"Úkol: {state.task}"},
        ])

        parsed = self._parse_json_obj(raw)
        if not parsed:
            # LLM vrátil nečitelný výstup — přeskoč krok
            logger.warning(f"Router: nečitelný výstup: {raw[:80]}")
            state.observations.append("(router selhal — přeskočeno)")
            state.step_idx += 1
            return

        tool = parsed.get("tool", "")
        args = parsed.get("args", {})

        if tool == "DONE":
            state.final_answer = args.get("answer", state.steps_summary())
            state.status       = NodeStatus.DONE
            return

        state.last_tool  = tool
        state.last_args  = args
        state.status     = NodeStatus.EXECUTING

    # ── Uzel: Executor ───────────────────────────────────────────

    def _node_executor(self, state: AgentState):
        tool = self.registry.get(state.last_tool)
        if tool is None:
            result = f"Nástroj '{state.last_tool}' neexistuje."
        else:
            state.notify(f"[{state.last_tool}] spouštím…")
            result = tool.call(**state.last_args)
            if len(result) > 1000:
                result = result[:997] + "…"

        state.last_result = result
        state.exec_count += 1
        state.notify(f"[{state.last_tool}] → {result[:70]}{'…' if len(result) > 70 else ''}")
        state.status = NodeStatus.CRITICIZING

    # ── Uzel: Critic ─────────────────────────────────────────────

    def _node_critic(self, state: AgentState):
        raw = self._llm([
            {"role": "system", "content": _CRITIC_PROMPT.format(
                step=state.current_step(),
                result=state.last_result,
            )},
            {"role": "user", "content": "Zhodnoť výsledek."},
        ])

        verdict = raw.strip().upper().split()[0] if raw.strip() else "OK"

        if verdict == "RETRY" and state.retry_count < MAX_RETRIES:
            state.retry_count += 1
            state.notify(f"Critic: RETRY ({state.retry_count}/{MAX_RETRIES})")
            state.status = NodeStatus.EXECUTING

        elif verdict == "REPLAN" and state.replan_count < MAX_REPLANS:
            state.replan_count += 1
            state.retry_count  = 0
            state.notify("Critic: REPLAN — přeplánuji")
            state.observations.append(f"Selhalo: {state.last_result[:60]}")
            state.status = NodeStatus.PLANNING

        else:
            # OK nebo vyčerpány pokusy — zapiš výsledek, přejdi na další krok
            state.observations.append(state.last_result)
            state.step_idx    += 1
            state.retry_count  = 0
            state.status       = NodeStatus.ROUTING

    # ── Syntéza finální odpovědi ──────────────────────────────────

    def _synthesize(self, state: AgentState) -> str:
        """Pokud router nevrátil DONE s answer, syntetizuj ze stavu."""
        if not state.observations:
            return "Úkol dokončen."

        obs_text = "\n".join(
            f"- {s}: {o[:100]}"
            for s, o in zip(state.plan, state.observations)
        )
        raw = self._llm([
            {"role": "system", "content":
                "Jsi JARVIS. Shrň výsledky provedených kroků do jedné stručné české věty."},
            {"role": "user", "content":
                f"Úkol: {state.task}\n\nVýsledky kroků:\n{obs_text}"},
        ])
        return raw.strip() if raw.strip() else "Všechny kroky dokončeny."

    # ── LLM helper ───────────────────────────────────────────────

    def _llm(self, messages: list) -> str:
        payload = {
            "model":    self.model,
            "messages": messages,
            "stream":   False,
            "options":  {"temperature": 0.1, "num_predict": LLM_TOKENS},
        }
        try:
            r = requests.post(self.ollama_url, json=payload, timeout=60)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"GraphAgent LLM chyba: {e}")
            return ""

    # ── JSON parsery ─────────────────────────────────────────────

    @staticmethod
    def _parse_json_list(raw: str) -> List[str]:
        try:
            m = re.search(r"\[.*?\]", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                if isinstance(data, list):
                    return [str(x).strip() for x in data if x]
        except Exception:
            pass
        return []

    @staticmethod
    def _parse_json_obj(raw: str) -> Optional[dict]:
        """Najde první JSON objekt v textu — správně zpracuje vnořené {}."""
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except Exception:
                        return None
        return None


# ── Detekce složitých úkolů ───────────────────────────────────────

_COMPLEX = re.compile(
    r"\b("
    r"(najdi|vyhledej|zjisti).{0,50}(uloz|zapis|otevre|posli|rekni|porovnej)"
    r"|(udel|proved|zkontroluj|over).{0,40}(a\s*(pak|potom|take|taky)|nasledne)"
    r"|(porovnej|srovnej).{1,60}(cen|model|verz|produkt)"
    r"|(kolik\s+stoji|cena\s+).{1,50}(uloz|zapamatuj|poznamen)"
    r"|sestav|vytvor\s+report|shromazdi|analyzuj"
    r")",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    )


def should_handle(text: str) -> bool:
    """True pokud text vyžaduje grafového agenta (složitější než ReAct)."""
    return bool(_COMPLEX.search(_norm(text)))


# ── Singleton ─────────────────────────────────────────────────────

_graph: Optional[AgentGraph] = None


def get_graph_agent(executor=None, mcp_bridge=None,
                    ollama_url: str = "http://localhost:11434/api/chat",
                    model: str = "qwen2.5:3b") -> Optional[AgentGraph]:
    global _graph
    if _graph is None:
        if executor is None:
            return None
        from agent_tools import build_registry
        registry = build_registry(executor, mcp_bridge)
        _graph   = AgentGraph(registry, ollama_url, model)
        logger.info(f"GraphAgent inicializován ({len(registry.all())} nástrojů)")
    return _graph


def reset_graph():
    global _graph
    _graph = None
