"""
JARVIS router — neural memory routing.
Handles remember/forget/recall commands.
"""
import re


def route_memory(text: str, t: str) -> tuple:
    """Handles memory recall, store, stats and maintenance commands."""

    if re.search(r"\b(vyhledej\s+v\s+paměti|recall\s+memory|co\s+si\s+pamatuješ)\b", t):
        query = re.sub(
            r"\b(vyhledej\s+v\s+paměti|recall\s+memory|co\s+si\s+pamatuješ)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        return f"Hledám v paměti: {query}", {
            "action": "memory_recall", "params": {"query": query}}

    if re.search(r"\b(zapamatuj\s+si|ulož\s+do\s+paměti|store\s+memory)\b", t):
        content = re.sub(
            r"\b(zapamatuj\s+si|ulož\s+do\s+paměti|store\s+memory)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if content:
            return f"Ukládám do paměti: {content}", {
                "action": "memory_store", "params": {"content": content}}

    if re.search(r"\b(statistiky\s+paměti|memory\s+stats)\b", t):
        return "Statistiky paměti:", {"action": "memory_stats", "params": {}}

    if re.search(r"\b(údržba\s+paměti|memory\s+maintenance)\b", t):
        return "Spouštím údržbu paměti.", {"action": "memory_maintenance", "params": {}}

    return None, None
