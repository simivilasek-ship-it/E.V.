"""
JARVIS Multi-Agent Role System
4 specializované role: Planner, Researcher, Executor, Critic.
Každá role má vlastní system prompt a specializaci.
"""
from __future__ import annotations
import logging
from typing import Optional

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
    """Hodnotí výsledky a navrhuje vylepšení."""

    SYSTEM = """Jsi Critic. Tvůj úkol: zhodnotit výsledek akce.
Rozhodni: SUCCESS (výsledek je dostatečný) nebo RETRY (s důvodem proč).
Formát: SUCCESS: [shrnutí] nebo RETRY: [co je špatně]."""

    def __init__(self, ollama_url: str, model: str):
        self.url = ollama_url
        self.model = model

    def evaluate(self, action: str, result: str) -> tuple[bool, str]:
        """Vrátí (success: bool, feedback: str)."""
        try:
            import requests
            prompt = f"Akce: {action}\nVýsledek: {result}"
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
            content = resp.json()["message"]["content"].strip()
            if content.upper().startswith("SUCCESS"):
                feedback = content[len("SUCCESS"):].lstrip(": ").strip()
                return True, feedback
            elif content.upper().startswith("RETRY"):
                feedback = content[len("RETRY"):].lstrip(": ").strip()
                return False, feedback
            else:
                # Pokud odpověď neodpovídá formátu, považujeme za SUCCESS
                return True, content
        except Exception as e:
            logger.warning(f"CriticAgent chyba: {e}")
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

    def _execute_step(self, step: str) -> str:
        """Provede jeden krok — přes CommandExecutor nebo LLM."""
        # Pokud krok vypadá jako příkaz (vyhledej, otevři, spočítej)
        if self._cmd_executor:
            try:
                from local_router import LocalRouter
                _, action = LocalRouter().route(step)
                if action:
                    return self._cmd_executor.execute(action["action"], action.get("params", {}))
            except Exception:
                pass
        return self.executor_agent.execute(step)
