"""
E.V. Multi-Agent Role System
4 specializované role: Planner, Researcher, Executor, Critic.
Každá role má vlastní system prompt a specializaci.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Rozloží úkol na konkrétní kroky."""

    SYSTEM = """Jsi Planner. Tvůj úkol: rozložit zadání na maximálně 5 konkrétních kroků.
Formát odpovědi: očíslovaný seznam kroků, stručně.
NIKDY neprovádíš kroky sám — jen plánuješ."""

    def __init__(self, ollama_url: str, model: str):
        self.url = ollama_url
        self.model = model

    def plan(self, task: str, context: str = "") -> list[str]:
        """Vrátí seznam kroků jako list stringů."""
        try:
            import requests
            prompt = f"Úkol: {task}"
            if context:
                prompt += f"\nKontext: {context}"
            resp = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            # Parsuj očíslovaný seznam
            steps = []
            for line in content.splitlines():
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Odstraň číslo/pomlčku ze začátku
                    cleaned = line.lstrip("0123456789.-) ").strip()
                    if cleaned:
                        steps.append(cleaned)
            return steps if steps else [content.strip()]
        except Exception as e:
            logger.warning(f"PlannerAgent chyba: {e}")
            return []


class ResearcherAgent:
    """Sbírá informace z webu, paměti, souborů."""

    SYSTEM = """Jsi Researcher. Tvůj úkol: najít relevantní informace pro zadaný dotaz.
Používej dostupné nástroje (web search, paměť, soubory).
Vrať stručné shrnutí nalezených informací."""

    def __init__(self, ollama_url: str, model: str):
        self.url = ollama_url
        self.model = model

    def research(self, query: str, tools: dict = None) -> str:
        """Vyhledá informace a vrátí shrnutí."""
        try:
            import requests
            resp = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM},
                        {"role": "user", "content": query},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"ResearcherAgent chyba: {e}")
            return ""


class ExecutorAgent:
    """Provádí konkrétní akce."""

    SYSTEM = """Jsi Executor. Tvůj úkol: provést konkrétní příkaz nebo akci.
Dostaneš jeden konkrétní krok z plánu a musíš ho provést."""

    def __init__(self, ollama_url: str, model: str):
        self.url = ollama_url
        self.model = model

    def execute(self, action: str, executor=None) -> str:
        """Provede akci a vrátí výsledek."""
        try:
            import requests
            resp = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM},
                        {"role": "user", "content": action},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"ExecutorAgent chyba: {e}")
            return ""


class CriticAgent:
    """Hodnotí výsledky a navrhuje vylepšení.

    Dvoufázová validace:
      1. Rychlá heuristická plausibility check (bez LLM) — chytí halucinované ceny/čísla
      2. LLM hodnocení SUCCESS/RETRY
    """

    SYSTEM = """Jsi Critic. Tvůj úkol: zhodnotit výsledek akce.
Rozhodni: SUCCESS (výsledek je dostatečný) nebo RETRY (s důvodem proč).
Formát: SUCCESS: [shrnutí] nebo RETRY: [co je špatně]."""

    # (popis, regex pro detekci tématu, min_hodnota, max_hodnota)
    _PLAUSIBILITY_RULES = [
        ("cena GPU v USD",   r"(rtx|gtx|radeon|gpu|grafick)",   100,   5_000),
        ("cena CPU v USD",   r"(ryzen|intel|core\s*i\d|cpu)",    50,   2_000),
        ("cena RAM v USD",   r"(ram|ddr\d|paměť)",                5,     500),
        ("teplota CPU °C",   r"(teplota|temp|°c|stupeň)",         0,     110),
        ("rok",              r"\b(rok|year|ročník)\b",          1970,   2_030),
        ("procento",         r"(procent|%|percent)",               0,     100),
        ("latence ms",       r"(latenc|ping|ms\b|milisekund)",    0,  60_000),
    ]

    def __init__(self, ollama_url: str, model: str):
        self.url = ollama_url
        self.model = model

    def _plausibility_check(self, action: str, result: str) -> tuple[bool, str]:
        """Heuristická kontrola čísel v výsledku — bez LLM, okamžitá."""
        import re
        ctx = (action + " " + result).lower()
        numbers = [float(n.replace(",", "."))
                   for n in re.findall(r"\b\d{1,9}(?:[.,]\d+)?\b", result)]
        if not numbers:
            return True, ""
        for desc, pattern, lo, hi in self._PLAUSIBILITY_RULES:
            if re.search(pattern, ctx, re.I):
                for n in numbers:
                    if not (lo <= n <= hi):
                        return False, (
                            f"Podezřelé číslo {n} pro '{desc}' "
                            f"(očekáváno {lo}–{hi}). Pravděpodobná halucinace."
                        )
        return True, ""

    def evaluate(self, action: str, result: str) -> tuple[bool, str]:
        """Vrátí (success: bool, feedback: str)."""
        # Fáze 1 — rychlá heuristika (bez LLM)
        ok, reason = self._plausibility_check(action, result)
        if not ok:
            logger.warning(f"CriticAgent plausibility: {reason}")
            return False, reason

        # Fáze 2 — LLM hodnocení
        try:
            import requests
            resp = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM},
                        {"role": "user",   "content": f"Akce: {action}\nVýsledek: {result}"},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"].strip()
            if content.upper().startswith("SUCCESS"):
                return True, content[len("SUCCESS"):].lstrip(": ").strip()
            elif content.upper().startswith("RETRY"):
                return False, content[len("RETRY"):].lstrip(": ").strip()
            return True, content
        except Exception as e:
            logger.warning(f"CriticAgent LLM chyba: {e}")
            return True, ""


class MultiAgentOrchestrator:
    """Orchestruje 4 role pro komplexní úkoly."""

    def __init__(self, ollama_url: str, model: str, executor=None, mcp_bridge=None):
        self.planner = PlannerAgent(ollama_url, model)
        self.researcher = ResearcherAgent(ollama_url, model)
        self.executor_agent = ExecutorAgent(ollama_url, model)
        self.critic = CriticAgent(ollama_url, model)
        self._cmd_executor = executor   # CommandExecutor instance
        self._mcp = mcp_bridge

    def run(self, task: str, max_steps: int = 5) -> str:
        """Spustí celý pipeline: Plan → Research → Execute × N → Critic."""
        steps = self.planner.plan(task)
        if not steps:
            return "Nepodařilo se sestavit plán."

        results = []
        for i, step in enumerate(steps[:max_steps]):
            result = self._execute_step(step)
            ok, feedback = self.critic.evaluate(step, result)
            results.append(f"Krok {i+1}: {step}\n→ {result}")
            if not ok and i < max_steps - 1:
                # Retry krok jednou
                result2 = self._execute_step(f"{step} (oprava: {feedback})")
                results[-1] += f"\n→ Oprava: {result2}"

        return "\n\n".join(results)

    def run_parallel(self, task: str, max_steps: int = 5,
                     on_step=None) -> str:
        """Paralelní pipeline — nezávislé kroky běží souběžně.

        Kroky jsou rozděleny do vln (waves):
          - Vlna 1: kroky bez závislostí (odd-indexed nebo výslovně nezávislé)
          - Vlna 2: kroky závislé na výsledcích vlny 1

        on_step(step_idx, step, result) — volitelný callback pro streaming UI.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time as _t

        steps = self.planner.plan(task)
        if not steps:
            return "Nepodařilo se sestavit plán."

        steps = steps[:max_steps]
        results: list[str] = [""] * len(steps)
        timings: list[float] = [0.0] * len(steps)

        # Rozdělení do vln: sudé indexy = vlna 0, liché = vlna 1
        # (jednoduché heuristické schéma — bez explicitního dependency grafu)
        wave0 = [i for i in range(len(steps)) if i % 2 == 0]
        wave1 = [i for i in range(len(steps)) if i % 2 != 0]

        def _run(idx: int) -> tuple[int, str, float]:
            t0  = _t.monotonic()
            res = self._execute_step(steps[idx])
            ok, feedback = self.critic.evaluate(steps[idx], res)
            if not ok:
                res2 = self._execute_step(f"{steps[idx]} (oprava: {feedback})")
                res  = res2
            elapsed = _t.monotonic() - t0
            if on_step:
                try:
                    on_step(idx, steps[idx], res)
                except Exception:
                    pass
            return idx, res, elapsed

        def _run_wave(indices: list[int], workers: int = 4):
            with ThreadPoolExecutor(max_workers=min(workers, len(indices))) as pool:
                futures = {pool.submit(_run, i): i for i in indices}
                for fut in as_completed(futures):
                    idx, res, elapsed = fut.result()
                    results[idx]  = res
                    timings[idx]  = elapsed
                    logger.info(f"ParallelAgent: krok {idx+1} hotov ({elapsed:.1f}s)")

        # Vlna 0 — paralelně
        if wave0:
            _run_wave(wave0)

        # Vlna 1 — paralelně (po dokončení vlny 0)
        if wave1:
            _run_wave(wave1)

        # Sestavení výstupu
        lines = []
        for i, (step, res, t) in enumerate(zip(steps, results, timings)):
            lines.append(f"**Krok {i+1}** ({t:.1f}s): {step}\n{res}")

        total = sum(timings)
        sequential = total
        actual = max(
            sum(timings[i] for i in wave0) if wave0 else 0,
            sum(timings[i] for i in wave1) if wave1 else 0,
        ) + min(
            sum(timings[i] for i in wave0) if wave0 else 0,
            sum(timings[i] for i in wave1) if wave1 else 0,
        )
        lines.append(
            f"\n*Paralelní: {actual:.1f}s vs sekvenční ~{sequential:.1f}s "
            f"({int((1 - actual/sequential)*100) if sequential else 0}% rychleji)*"
        )
        return "\n\n".join(lines)

    def _execute_step(self, step: str) -> str:
        """Provede jeden krok — přes CommandExecutor nebo LLM."""
        if self._cmd_executor:
            try:
                from local_router import LocalRouter
                _, action = LocalRouter().route(step)
                if action:
                    return self._cmd_executor.execute(action["action"], action.get("params", {}))
            except Exception:
                pass
        return self.executor_agent.execute(step)


# ── SupervisorAgent ───────────────────────────────────────────────

class SupervisorAgent:
    """Hlavní agent který plánuje a deleguje sub-agentům."""

    def __init__(self, ollama_url: str, model: str):
        self.planner    = PlannerAgent(ollama_url, model)
        self.researcher = ResearcherAgent(ollama_url, model)
        self.executor   = ExecutorAgent(ollama_url, model)
        self.critic     = CriticAgent(ollama_url, model)
        self._log: list[str] = []

    def run_with_delegation(self, task: str, max_rounds: int = 3) -> str:
        """Spustí úkol s hierarchickou delegací.

        1. Planner vytvoří plán
        2. Pro každý krok: Supervisor rozhodne který sub-agent ho vykoná
        3. Critic hodnotí výsledek
        4. Pokud RETRY: Supervisor přeplánuje
        """
        plan = self.planner.plan(task)
        results = []

        for step in plan[:5]:  # max 5 kroků
            # Supervisor rozhodne kdo vykoná krok
            agent_type = self._route_step(step)

            if agent_type == "research":
                result = self.researcher.research(step)
            elif agent_type == "execute":
                result = self.executor.execute(step)
            else:
                result = self.executor.execute(step)

            ok, feedback = self.critic.evaluate(step, result)
            self._log.append(f"{agent_type}: {step[:40]} → {'✓' if ok else '✗'}")

            if ok:
                results.append(result)
            elif max_rounds > 0:
                # Retry s feedbackem
                retry_result = self.executor.execute(f"{step} (oprav: {feedback})")
                results.append(retry_result)

        return "\n".join(results) if results else "Úkol nedokončen."

    def _route_step(self, step: str) -> str:
        """Rozhodne který typ agenta má krok vykonat."""
        step_l = step.lower()
        if any(w in step_l for w in ["vyhledej", "najdi", "zjisti", "info"]):
            return "research"
        return "execute"

    def get_log(self) -> str:
        return "\n".join(self._log) if self._log else "Žádný log."


class SelfDebuggingAgent:
    """Agent který detekuje chyby ve vlastních odpovědích a opravuje je."""

    ERROR_PATTERNS = [
        r"traceback", r"exception", r"error:", r"syntax error",
        r"nameerror", r"typeerror", r"attributeerror",
        r"chyba:", r"selhalo", r"nelze",
    ]

    def __init__(self, ollama_url: str, model: str):
        self.url   = ollama_url
        self.model = model
        self._re   = __import__('re').compile(
            "|".join(self.ERROR_PATTERNS), __import__('re').IGNORECASE
        )

    def has_error(self, text: str) -> bool:
        """True pokud text obsahuje chybové patterny."""
        return bool(self._re.search(text))

    def debug_and_fix(self, original_task: str, broken_response: str,
                      max_attempts: int = 2) -> str:
        """Pokusí se opravit chybnou odpověď."""
        import requests

        for attempt in range(max_attempts):
            try:
                prompt = (
                    f"Tato odpověď obsahuje chybu:\n{broken_response}\n\n"
                    f"Původní úkol: {original_task}\n\n"
                    f"Oprav chybu a vrať správnou odpověď:"
                )
                r = requests.post(self.url, json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 500},
                }, timeout=30)
                if r.ok:
                    fixed = r.json().get("message", {}).get("content", "").strip()
                    if fixed and not self.has_error(fixed):
                        return fixed
            except Exception as e:
                logger.debug(f"SelfDebugging attempt {attempt+1} selhal: {e}")

        return broken_response  # Vrátí originál pokud se nepodaří opravit
