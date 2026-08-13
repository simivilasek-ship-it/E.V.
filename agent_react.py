"""
E.V. — ReAct Agent
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

import logging
import re
import threading
from typing import Callable,  TYPE_CHECKING, List, Optional

import requests

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
    r"(najdi|vyhledej|zjisti|search|find).{0,40}(uloz|zapis|poznamen|rekni|otevre|posli|open|save)"
    r"|(uloz|zapis|save).{0,40}(co|ktery|jaky|nalezl|vysledek|result)"
    r"|(porovnej|srovnej|compare).{1,60}(cen|model|verz|price)"
    r"|(zkontroluj|over|check).{1,50}(a\s+pak|potom|nasledne|then|and)"
    r"|(udel|proved|do|execute|run).{1,30}(a\s+potom|a\s+taky|a\s+take|then)"
    r"|(kolik\s+stoji|cena).{1,50}(uloz|zapamatuj|poznamen)"
    r"|(analyzuj|analyz|analyze|oprav|fix|navrhni|suggest).{1,60}"
    r"|(otevri|open).{1,30}(a\s+|and\s+)(najdi|search|precti|read)"
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
    ReAct 2.0 agent — Thought → Action → Observation loop with planning,
    introspection, step check, and checkpoint rollback capabilities.
    """

    SYSTEM_PROMPT_V2 = """\
Jsi E.V., inteligentní AI asistent. Pro splnění úkolu používáš nástroje.
Před každou akcí nejprve proveď introspekci ohledně dosavadního postupu vzhledem k plánu.

Plán, který máš následovat:
{plan}

Formát odpovědi (opakuj dokud úkol není hotov):
  Introspection: [tvá krátká introspekce a zhodnocení dosavadního pokroku - co bylo splněno, co zbývá]
  Thought: [co si myslíš o dalším kroku a proč volíš tento nástroj]
  Action: název_nástroje(parametr="hodnota")
  Observation: [výsledek — doplní systém]
  ...
  Answer: [finální odpověď uživateli česky]

Pravidla:
- Vždy začni s Introspection: následovaným Thought: a Action:
- Každý Action: musí být na samostatném řádku v přesném formátu tool(param="hodnota")
- Po Observation: pokračuj dalším Introspection:
- Když máš vše potřebné, ukonči Answer:
- Nikdy nevymýšlej výsledky — použij nástroj
- Maximálně {max_steps} kroků

Dostupné nástroje:
{tools}
"""

    def __init__(self, registry: "ToolRegistry", ollama_url: str, model: str):
        self.registry    = registry
        self.ollama_url  = ollama_url
        self.model       = model
        self._client     = OllamaClient(ollama_url, model)

    def _generate_plan(self, user_text: str) -> List[str]:
        """Vygeneruje plán kroků pro zadaný úkol."""
        prompt = (
            f"Jsi E.V. Plánovač. Rozděl úkol: '{user_text}' na 2 až 4 konkrétní kroky pro nástroje.\n"
            "Vrať pouze JSON pole řetězců, např. [\"krok 1\", \"krok 2\"]. Nic jiného nevypisuj."
        )
        try:
            raw = self._client.call([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=200)
            import json as _json
            m = re.search(r"\[.*?\]", raw, re.DOTALL)
            if m:
                data = _json.loads(m.group(0))
                if isinstance(data, list):
                    return [str(x).strip() for x in data if x]
        except Exception as e:
            logger.warning(f"Chyba při plánování ReAct 2.0: {e}")
        return [f"Vyřeš úkol: {user_text}"]

    def _check_step(self, tool_name: str, args: dict, observation: str) -> tuple[bool, str]:
        """Kontrola kroku (Step check / Critic). Vrátí (ok, důvod)."""
        obs_lower = observation.lower()
        if "chyba:" in obs_lower or "error:" in obs_lower or "nástroj neexistuje" in obs_lower:
            return False, "Nástroj vrátil chybu"
        if not observation.strip() or observation.strip() == "…[zkráceno]":
            return False, "Nástroj vrátil prázdný výsledek"
        
        # Heuristická kontrola plausibility čísel
        import re
        ctx = (tool_name + " " + str(args) + " " + observation).lower()
        numbers = [float(n.replace(",", "."))
                   for n in re.findall(r"\b\d{1,9}(?:[.,]\d+)?\b", observation)]
        if numbers:
            rules = [
                ("cena GPU",   r"(rtx|gtx|radeon|gpu|grafick)",   100,   5_000),
                ("cena CPU",   r"(ryzen|intel|core\s*i\d|cpu)",    50,   2_000),
                ("teplota CPU",   r"(teplota|temp|°c|stupeň)",         0,     110),
                ("procento",         r"(procent|%|percent)",               0,     100),
            ]
            for desc, pattern, lo, hi in rules:
                if re.search(pattern, ctx):
                    for n in numbers:
                        if not (lo <= n <= hi):
                            return False, f"Podezřelá hodnota {n} pro {desc} (očekáváno {lo}-{hi})"
        return True, "OK"

    def run(self, user_text: str, on_step: Optional[Callable] = None) -> str:
        """
        Spustí ReAct 2.0 smyčku a vrátí finální odpověď.
        """
        plan = self._generate_plan(user_text)
        plan_text = "\n".join(f"- {step}" for step in plan)
        if on_step:
            on_step(f"[Plan] Plán: " + " → ".join(plan))

        system_prompt = self.SYSTEM_PROMPT_V2.format(
            plan=plan_text,
            max_steps=MAX_STEPS,
            tools=self.registry.schema_block(),
        )

        messages = [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_text},
        ]
        trace: List[str] = []
        rollback_count = 0
        MAX_ROLLBACKS = 2
        step = 0

        while step < MAX_STEPS:
            checkpoint = {
                "messages": list(messages),
                "trace_len": len(trace),
                "step": step
            }

            raw = self._llm(messages)
            if not raw:
                break

            logger.debug(f"ReAct step {step}: {raw[:120]}")

            # Zpracuj introspekci pokud existuje
            intro_match = re.search(r"Introspection:\s*(.+)", raw, re.IGNORECASE)
            if intro_match:
                intro_text = intro_match.group(1).strip()
                if on_step:
                    on_step(f"[Introspekce] {intro_text[:100]}…")

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
            check_ok  = True
            check_reason = "OK"
            kwargs = {}

            if not parsed:
                observation = f"Chyba: nepodařilo se parsovat Action: {action_m.group(0)}"
                check_ok = False
                check_reason = "Parsovací chyba"
            else:
                _, kwargs  = parsed
                tool       = self.registry.get(tool_name)
                if tool is None:
                    observation = f"Chyba: nástroj '{tool_name}' neexistuje. Dostupné: {[t.name for t in self.registry.all()]}"
                    check_ok = False
                    check_reason = "Neexistující nástroj"
                else:
                    try:
                        observation = tool.call(**kwargs)
                        if len(observation) > 1200:
                            observation = observation[:1200] + "…[zkráceno]"
                        # Kontrola kroku (Step check)
                        check_ok, check_reason = self._check_step(tool_name, kwargs, observation)
                    except Exception as e:
                        observation = f"Chyba při volání nástroje: {e}"
                        check_ok = False
                        check_reason = str(e)

            if not check_ok:
                if rollback_count < MAX_ROLLBACKS:
                    rollback_count += 1
                    logger.warning(f"ReAct 2.0: Krok {step} selhal ({check_reason}). Provádím rollback ({rollback_count}/{MAX_ROLLBACKS}).")
                    if on_step:
                        on_step(f"[Rollback] Selhání ({check_reason}). Návrat k předchozímu stavu.")

                    messages = list(checkpoint["messages"])
                    trace = trace[:checkpoint["trace_len"]]

                    guidance = (
                        f"Upozornění systému: Spuštění nástroje '{tool_name}' s parametry {kwargs} "
                        f"selhalo nebo vrátilo neplatný výsledek ({check_reason}). "
                        f"Zvol prosím jinou akci nebo uprav parametry a pokračuj v plnění plánu."
                    )
                    messages.append({"role": "user", "content": guidance})
                    # Zkusíme znovu ze stejného stavu, nezvyšujeme krok
                    continue
                else:
                    logger.warning("ReAct 2.0: Překročen limit rollbacků. Pokračuji i přes selhání.")
                    if on_step:
                        on_step("[Warning] Limit rollbacků vyčerpán. Pokračuji.")

            step_text = f"[{tool_name}] → {observation[:80]}…" if len(observation) > 80 else f"[{tool_name}] → {observation}"
            trace.append(step_text)
            if on_step:
                on_step(step_text)

            # Přidej do kontextu
            messages.append({"role": "assistant",  "content": raw})
            messages.append({"role": "user",       "content": f"Observation: {observation}"})
            step += 1

        logger.warning(f"ReAct: dosažen limit {MAX_STEPS} kroků nebo žádná Answer")
        return "Nepodařilo se dokončit úkol v časovém limitu. " + (
            "Kroky: " + " → ".join(trace) if trace else ""
        )

    def _llm(self, messages: list) -> str:
        return self._client.call(messages, temperature=0.2, max_tokens=MAX_TOKENS)

    def run_with_tool_calling(self, user_text: str,
                              on_step: Optional[Callable] = None) -> str:
        """Ollama nativní tool-calling — JSON místo regex parsování.
        S ReAct 2.0 plánováním, introspekcí, step checky a rollbacky.
        """
        import json as _json

        tools_schema = self.registry.ollama_tools_schema()
        if not tools_schema:
            return self.run(user_text, on_step)

        plan = self._generate_plan(user_text)
        plan_text = "\n".join(f"- {step}" for step in plan)
        if on_step:
            on_step(f"[Plan] Plán: " + " → ".join(plan))

        system_msg = (
            "Jsi E.V., AI asistent. Používáš nástroje k splnění úkolů. "
            "Komunikuješ česky. Když máš výsledek, odpověz přímo.\n"
            f"Plán, který máš následovat:\n{plan_text}\n"
            "Před každým voláním nástroje (tool call) nejprve napiš do textového obsahu (content) zprávu ve formátu:\n"
            "Introspection: [tvá krátká introspekce a zhodnocení dosavadního pokroku - co bylo splněno, co zbývá]\n"
            "Thought: [tvá úvaha a zdůvodnění dalšího kroku]\n"
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text},
        ]
        trace: List[str] = []
        rollback_count = 0
        MAX_ROLLBACKS = 2
        step = 0

        while step < MAX_STEPS:
            checkpoint = {
                "messages": list(messages),
                "trace_len": len(trace),
                "step": step
            }

            payload = {
                "model":    self.model,
                "messages": messages,
                "tools":    tools_schema,
                "stream":   False,
                "options":  {"temperature": 0.1, "num_predict": MAX_TOKENS},
            }
            try:
                resp = requests.post(self.ollama_url, json=payload, timeout=60)
                resp.raise_for_status()
                msg = resp.json().get("message", {})
            except Exception as e:
                logger.warning(f"Tool-calling LLM chyba ({e}) — fallback na ReAct")
                return self.run(user_text, on_step)

            tool_calls = msg.get("tool_calls", [])
            content    = (msg.get("content") or "").strip()

            # Zpracuj introspekci pokud existuje
            if content:
                intro_match = re.search(r"Introspection:\s*(.+)", content, re.IGNORECASE)
                if intro_match and on_step:
                    on_step(f"[Introspekce] {intro_match.group(1).strip()[:100]}…")

            # Model odpověděl textem bez tool call — to je finální odpověď
            if not tool_calls:
                return content or "Hotovo."

            step_check_ok = True
            step_check_reason = "OK"
            temp_results = []

            for tc in tool_calls:
                fn   = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = _json.loads(args)
                    except Exception:
                        args = {}

                tool = self.registry.get(name)
                if tool is None:
                    observation = f"Nástroj '{name}' neexistuje"
                    step_check_ok = False
                    step_check_reason = "Neexistující nástroj"
                else:
                    try:
                        observation = tool.call(**args)
                        if len(observation) > 1200:
                            observation = observation[:1200] + "…[zkráceno]"
                        # Kontrola kroku (Step check)
                        check_ok, check_reason = self._check_step(name, args, observation)
                        if not check_ok:
                            step_check_ok = False
                            step_check_reason = check_reason
                    except Exception as e:
                        observation = f"Chyba nástroje {name}: {e}"
                        step_check_ok = False
                        step_check_reason = str(e)

                temp_results.append((name, args, observation))

            if not step_check_ok:
                if rollback_count < MAX_ROLLBACKS:
                    rollback_count += 1
                    logger.warning(f"ReAct 2.0 (Tool Calling): Krok {step} selhal ({step_check_reason}). Provádím rollback ({rollback_count}/{MAX_ROLLBACKS}).")
                    if on_step:
                        on_step(f"[Rollback] Selhání ({step_check_reason}). Návrat k předchozímu stavu.")

                    messages = list(checkpoint["messages"])
                    trace = trace[:checkpoint["trace_len"]]

                    failed_calls_desc = ", ".join(f"{n}({a})" for n, a, _ in temp_results)
                    guidance = (
                        f"Upozornění systému: Spuštění nástroje/nástrojů '{failed_calls_desc}' "
                        f"selhalo nebo vrátilo neplatný výsledek ({step_check_reason}). "
                        f"Zvol prosím jinou akci nebo uprav parametry a pokračuj v plnění plánu."
                    )
                    messages.append({"role": "user", "content": guidance})
                    continue
                else:
                    logger.warning("ReAct 2.0: Překročen limit rollbacků v tool calling. Pokračuji.")
                    if on_step:
                        on_step("[Warning] Limit rollbacků vyčerpán. Pokračuji.")

            # Úspěšně zpracované tool cally zapíšeme do zpráv
            messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
            for name, args, observation in temp_results:
                step_text = f"[{name}] → {observation[:80]}"
                trace.append(step_text)
                if on_step:
                    on_step(step_text)

                messages.append({
                    "role": "tool",
                    "content": observation,
                })
            step += 1

        logger.warning("Tool-calling: dosažen limit kroků")
        return "Nepodařilo se dokončit úkol. Kroky: " + " → ".join(trace)


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


# ── ReAct 2.0 rozšíření ───────────────────────────────────────────

from dataclasses import dataclass, field


@dataclass
class StepResult:
    """Výsledek jednoho kroku agenta."""
    action: str
    result: str
    success: bool
    error: Optional[str] = None
    rollback_fn: Optional[Callable] = field(default=None, repr=False)


class ReactAgentV2(ReactAgent):
    """ReAct 2.0 — s plánováním, kontrolou kroků a rollbackem."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_history: List[StepResult] = []
        self._plan: List[str] = []

    def plan(self, task: str) -> List[str]:
        """Vytvoří plán kroků před spuštěním. Vrátí seznam akcí."""
        prompt = (
            f"Vytvoř stručný plán (max 5 kroků) pro úkol: {task}\n"
            "Každý krok na nový řádek jako: KROK X: popis\n"
            "Jen kroky, žádné vysvětlení."
        )
        try:
            raw = self._client.call(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            steps = []
            for line in raw.splitlines():
                line = line.strip()
                m = re.match(r"KROK\s*\d+\s*:\s*(.+)", line, re.IGNORECASE)
                if m:
                    steps.append(m.group(1).strip())
            self._plan = steps if steps else [task]
        except Exception as e:
            logger.warning(f"ReactAgentV2.plan chyba: {e}")
            self._plan = [task]
        return self._plan

    def validate_step(self, step: StepResult) -> bool:
        """Zkontroluje výsledek kroku — detekuje chyby."""
        if not step.success:
            return False
        error_keywords = ["error", "chyba", "selhal", "failed", "exception"]
        if any(kw in step.result.lower() for kw in error_keywords):
            return False
        return True

    def rollback_last(self) -> str:
        """Odvolá poslední krok pokud má rollback funkci."""
        if self._step_history and self._step_history[-1].rollback_fn:
            self._step_history[-1].rollback_fn()
            self._step_history.pop()
            return "Krok odvolán."
        return "Žádný krok k odvolání."

    def introspect(self) -> str:
        """Vrátí souhrn co agent dělal — pro debugging."""
        if not self._step_history:
            return "Žádná historie kroků."
        lines = [f"Celkem kroků: {len(self._step_history)}"]
        for i, s in enumerate(self._step_history, 1):
            status = "✓" if s.success else "✗"
            lines.append(f"  {i}. [{status}] {s.action}: {s.result[:50]}")
        return "\n".join(lines)
