from __future__ import annotations
import logging
import json
import re
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from llm import OllamaClient
from agent_react import ReactAgent

if TYPE_CHECKING:
    from agent_tools import ToolRegistry

logger = logging.getLogger(__name__)

class HierarchicalAgent:
    """
    Hierarchical agent - Supervisor agent that decomposes tasks and delegates
    them to specialized sub-agents running constrained ReactAgents.
    """

    def __init__(self, registry: "ToolRegistry", ollama_url: str, model: str):
        self.registry = registry
        self.ollama_url = ollama_url
        self.model = model
        self._client = OllamaClient(ollama_url, model)

        # Define sub-agents tool mappings
        self.sub_agents_config = {
            "Researcher": {
                "tools": ["web_search", "fetch_url"],
                "system_prompt": (
                    "Jsi Researcher sub-agent. Tvou specializací je vyhledávání na internetu a stahování obsahu.\n"
                    "Zadání řeš přímočaře pomocí svých vyhledávacích nástrojů.\n"
                    "Odpovídej stručně a jasně v češtině."
                )
            },
            "MemorySpecialist": {
                "tools": ["note_add", "note_list", "memory_store", "memory_recall"],
                "system_prompt": (
                    "Jsi MemorySpecialist sub-agent. Tvou specializací je ukládání poznámek, dlouhodobá paměť a připomínky.\n"
                    "Ukládej a vyhledávej informace podle zadání.\n"
                    "Odpovídej stručně a jasně v češtině."
                )
            },
            "SystemSpecialist": {
                "tools": ["get_time", "get_weather", "calculate"],
                "system_prompt": (
                    "Jsi SystemSpecialist sub-agent. Tvou specializací jsou matematické výpočty, zjišťování času a počasí.\n"
                    "Zadání řeš pomocí svých systémových nástrojů.\n"
                    "Odpovídej stručně a jasně v češtině."
                )
            },
            "GenericAgent": {
                "tools": [],
                "system_prompt": (
                    "Jsi GenericAgent sub-agent. Tvou specializací je logická analýza, psaní kódu a obecné uvažování.\n"
                    "Nepoužíváš žádné speciální nástroje.\n"
                    "Odpovídej věcně a srozumitelně v češtině."
                )
            }
        }

    def _decompose_task(self, task: str) -> List[Dict[str, Any]]:
        """Rozloží úkol na pod-úkoly a určí vhodného sub-agenta."""
        prompt = (
            "Jsi Hlavní Koordinátor (Supervisor) v hierarchickém agentním systému. "
            "Tvým cílem je rozdělit úkol na pod-úkoly a delegovat je na specializované sub-agenty.\n\n"
            "Dostupní sub-agenti:\n"
            "1. Researcher: Specialista na vyhledávání na internetu a stahování webových stránek.\n"
            "2. MemorySpecialist: Specialista na ukládání poznámek, dlouhodobou paměť a vyhledávání v ní.\n"
            "3. SystemSpecialist: Specialista na matematické výpočty, počasí, čas a systémová data.\n"
            "4. GenericAgent: Obecný agent pro logické uvažování, analýzu, psaní textů a programování bez nutnosti nástrojů.\n\n"
            f"Rozděl úkol: '{task}' na 1 až 3 konkrétní pod-úkoly.\n"
            "Vrať pouze JSON seznam objektů ve formátu:\n"
            "[\n"
            "  {\"sub_agent\": \"NázevSubAgenta\", \"task\": \"Zadání pod-úkolu v češtině\"}\n"
            "]\n"
            "Nic jiného nevypisuj!"
        )
        try:
            raw = self._client.call([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=300)
            m = re.search(r"\[.*?\]", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"Chyba rozkladu úkolu supervisorom: {e}")
        
        # Fallback na GenericAgent s celým úkolem
        return [{"sub_agent": "GenericAgent", "task": task}]

    def _get_sub_registry(self, tool_names: List[str]) -> "ToolRegistry":
        from agent_tools import ToolRegistry
        sub = ToolRegistry()
        for name in tool_names:
            tool = self.registry.get(name)
            if tool:
                sub.register(tool)
        return sub

    def run(self, task: str, on_step: Optional[Callable] = None) -> str:
        """Spustí koordinaci sub-agentů a syntetizuje odpověď."""
        if on_step:
            on_step(f"[Supervisor] Plánuji a analyzuji úkol: '{task}'")
        
        sub_tasks = self._decompose_task(task)
        results = []

        for i, sub in enumerate(sub_tasks):
            sub_agent_name = sub.get("sub_agent", "GenericAgent")
            sub_task_desc = sub.get("task", task)
            
            if sub_agent_name not in self.sub_agents_config:
                sub_agent_name = "GenericAgent"
                
            config = self.sub_agents_config[sub_agent_name]
            
            # Vytvoř sub-registry
            sub_reg = self._get_sub_registry(config["tools"])
            
            if on_step:
                on_step(f"[Supervisor] Deleguji krok {i+1}: '{sub_task_desc}' na agenta {sub_agent_name}")
                
            # Spusť ReactAgent jako sub-agenta
            sub_agent = ReactAgent(sub_reg, self.ollama_url, self.model)
            # Uprav system prompt sub-agenta
            sub_agent.SYSTEM_PROMPT_V2 = config["system_prompt"] + "\n\nDostupné nástroje:\n{tools}"
            
            try:
                sub_result = sub_agent.run(sub_task_desc, on_step=None)
                results.append(f"Sub-agent {sub_agent_name} (úkol '{sub_task_desc}'): {sub_result}")
            except Exception as e:
                logger.error(f"Chyba sub-agenta {sub_agent_name}: {e}")
                results.append(f"Sub-agent {sub_agent_name} (úkol '{sub_task_desc}'): Selhal s chybou {e}")

        # Syntéza výsledků
        results_text = "\n\n".join(results)
        if on_step:
            on_step("[Supervisor] Syntetizuji výsledky sub-agentů do finální odpovědi...")
            
        synthesis_prompt = (
            "Jsi Hlavní Koordinátor (Supervisor) v hierarchickém agentním systému. "
            "Sestav z následujících výsledků sub-agentů finální, ucelenou odpověď pro uživatele v češtině.\n\n"
            f"Původní úkol: {task}\n\n"
            f"Výsledky sub-agentů:\n{results_text}\n\n"
            "Vytvoř přehlednou finální odpověď."
        )
        try:
            final_answer = self._client.call([{"role": "user", "content": synthesis_prompt}], temperature=0.2, max_tokens=500)
            return final_answer.strip()
        except Exception as e:
            logger.error(f"Syntéza selhala: {e}")
            return f"Úkol dokončen se sub-výsledky:\n\n{results_text}"

# Singleton factory
_hierarchical: Optional[HierarchicalAgent] = None
_hierarchical_lock = threading.Lock()

def get_hierarchical_agent(executor=None, mcp_bridge=None,
                           ollama_url: str = "http://localhost:11434/api/chat",
                           model: str = "qwen2.5:3b") -> Optional[HierarchicalAgent]:
    global _hierarchical
    with _hierarchical_lock:
        if _hierarchical is None:
            if executor is None:
                return None
            from agent_tools import build_registry
            registry = build_registry(executor, mcp_bridge)
            _hierarchical = HierarchicalAgent(registry, ollama_url, model)
            logger.info("HierarchicalAgent inicializován")
    return _hierarchical

def reset_hierarchical():
    global _hierarchical
    with _hierarchical_lock:
        _hierarchical = None

def should_handle(text: str) -> bool:
    """Určí, zda má být použit hierarchický agent."""
    keywords = ["hierarchic", "supervisor", "deleguj", "delegovat", "rozděl úkoly", "rozdel ukoly"]
    from commands.utils import normalize_text as _norm
    normalized = _norm(text)
    return any(kw in normalized for kw in keywords)
