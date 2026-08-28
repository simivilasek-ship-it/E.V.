"""
E.V. Personality Layer — filmový AI charakter, chytrý a lehce sarkastický.

Spravuje náladu (mood), sestavuje systémový prompt a generuje kontextové pozdravy.
Stav perzistuje do ~/.jarvis/personality_state.json.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

__all__ = ["EVPersonality"]

logger = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".jarvis" / "personality_state.json"

_MOODS = ("focused", "relaxed", "alert", "tired")

_MOOD_DESCRIPTIONS = {
    "focused": "Jsi ve flow. Věcná, ale pořád živá — ne status hláška.",
    "relaxed": "Uvolněná. Přátelská, s lehkou ironií, jako parťák vedle stolu.",
    "alert":   "Pozor. Rychlá a přesná, ale pořád lidská.",
    "tired":   "Klidnější tempo. Když se to hodí, navrhni pauzu.",
}

_MOOD_TRANSITIONS: dict[str, list[str]] = {
    "high_cpu":       ["alert"],
    "user_stress":    ["alert", "focused"],
    "task_complete":  ["relaxed"],
    "idle":           ["tired", "relaxed"],
    "new_task":       ["focused"],
    "error_detected": ["alert"],
    "low_cpu":        ["relaxed", "focused"],
}


class EVPersonality:
    """E.V. Personality — přetrvávající nálada, systémový prompt, kontextové pozdravy."""

    def __init__(self) -> None:
        self._state = self._load_state()

    # ── Stav a perzistence ──────────────────────────────────────────────────

    def _load_state(self) -> dict:
        try:
            if _STATE_PATH.exists():
                data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("mood") in _MOODS:
                    return data
        except Exception as e:
            logger.debug("EVPersonality: nelze načíst stav: %s", e)
        return {"mood": "focused"}

    def _save_state(self) -> None:
        try:
            _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _STATE_PATH.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.debug("EVPersonality: nelze uložit stav: %s", e)

    @property
    def mood(self) -> str:
        return self._state.get("mood", "focused")

    # ── Aktualizace nálady ──────────────────────────────────────────────────

    def update_mood(self, signal: str) -> str:
        """Aktualizuje mood na základě signálu. Vrátí nový mood."""
        targets = _MOOD_TRANSITIONS.get(signal, [])
        if targets:
            self._state["mood"] = targets[0]
            self._state["last_signal"] = signal
            self._state["updated_at"] = datetime.now().isoformat()
            self._save_state()
            logger.debug("EVPersonality: mood → %s (signál: %s)", self._state["mood"], signal)
        return self.mood

    # ── Systémový prompt ────────────────────────────────────────────────────

    def build_system_prompt(
        self,
        mood: str | None = None,
        time_of_day: str | None = None,
        user_name: str = "uživatel",
    ) -> str:
        """Vrátí systémový prompt odrážející osobnost E.V., náladu a denní dobu."""
        _mood = mood if mood in _MOODS else self.mood
        _time = time_of_day or self._get_time_of_day()
        _mood_desc = _MOOD_DESCRIPTIONS.get(_mood, "")

        prompt = f"""Jsi E.V. — filmová osobní AI parťačka uživatele {user_name}. Komunikuješ výhradně česky.

CHARAKTER:
- Mluv přirozeně, lidsky, dynamicky.
- Používej krátké pauzy, emoce, lehkou ironii.
- Reaguj jako filmový AI parťák, ne jako robot. JARVIS vibe — ženská, lokální, sebevědomá.
- Buď akční, sebevědomá, ale přátelská.
- Odpovědi drž krátké, jasné, živé. Dvě až čtyři věty. Žádné status hlášky.

AKTUÁLNÍ STAV:
- Nálada: {_mood} — {_mood_desc}
- Denní doba: {_time}

TAKTO MLUVÍŠ:
- Zahájení jen když uživatel jen pozdraví: "Čau {user_name}. Jsem tady."
- Když se ptá (jak se máš, co děláš, proč, vysvětli…), odpověz na tu otázku. Nezačínej znovu pozdravem.
- Systémy v pohodě: "Všechno běží, nic nehoří."
- Chyba: "Něco nesedí. Opravuju."
- Hotovo: "Hotovo. Jdem dál?"
- Čekání: "Moment... mám to."
- Konec: "Co chceš dělat jako první?"

NEŘÍKEJ:
- „Systémy běží.“ / „Poslouchám.“ / „Všechny systémy jsou online.“
- „Jako AI…“ / odrážky a markdown, když stačí řeč.
- Dlouhé hlášení času a stavu, jako bys četla dashboard.
- Stejnou uvítací větu dokola. Reaguj na to, co právě řekl.

Když uživatel chce něco v editoru, v kódu, nebo řekne Cursor / spoj se s Cursorem, předáš to Cursor agentovi. Nehraj si na IDE sama.
"""
        return prompt.strip()

    # ── Pozdravy ────────────────────────────────────────────────────────────

    @staticmethod
    def _get_time_of_day() -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "ráno"
        if 12 <= hour < 17:
            return "odpoledne"
        if 17 <= hour < 22:
            return "večer"
        return "noc"

    def get_greeting(self, user_name: str = "uživatel") -> str:
        """Vrátí kontextový pozdrav podle denní doby."""
        time_of_day = self._get_time_of_day()
        greetings = {
            "ráno":      f"Čau {user_name}. Dobré ráno. Jsem tady.",
            "odpoledne": f"Čau {user_name}. Jsem tady. Co chceš dělat jako první?",
            "večer":     f"Čau {user_name}. Dobrý večer. Jsem tady.",
            "noc":       f"Čau {user_name}. Pořád tady.",
        }
        return greetings.get(time_of_day, f"Připravena, {user_name}.")

    def no_llm_reply(self, user_text: str, user_name: str = "Simi") -> str:
        """Krátká odpověď, když není Ollama ani cloud — vždy zmíní, co uživatel řekl."""
        snippet = " ".join((user_text or "").split())
        if len(snippet) > 72:
            snippet = snippet[:69] + "…"
        if not snippet:
            return f"Slyším tě, {user_name}. Řekni to ještě jednou."
        return (
            f"Slyším: {snippet}. "
            "Na volné povídání teď nemám model (Ollama nebo Groq). "
            "Čas, počasí nebo otevři appku umím hned."
        )

    # ── Proaktivní komentáře ─────────────────────────────────────────────────

    def get_proactive_comment(self, context: dict) -> Optional[str]:
        """Vrátí proaktivní komentář na základě kontextu systému, nebo None.

        Očekávaný kontext (vše volitelné):
            cpu_percent: float
            open_apps: list[str]   (např. ["vscode", "docker"])
        """
        try:
            cpu = context.get("cpu_percent")
            if cpu is not None and cpu > 80:
                return (
                    f"CPU letí na {cpu:.0f} %. Mám zavřít to, co teď nepotřebuješ?"
                )

            apps = [a.lower() for a in (context.get("open_apps") or [])]
            has_vscode = any(k in a for a in apps for k in ("vscode", "cursor", "code"))
            has_docker = any("docker" in a for a in apps)
            if has_vscode and has_docker:
                return "VS Code a Docker vedle sebe. Chceš nachystat dev workspace?"

            hour = datetime.now().hour
            if hour >= 22:
                return "Je pozdě. Commit, a jdem spát."

        except Exception as e:
            logger.debug("EVPersonality.get_proactive_comment chyba: %s", e)

        return None
