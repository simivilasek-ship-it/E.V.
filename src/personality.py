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
    "focused": "Pracuješ v soustředěném režimu. Odpovídáš stručně a věcně, bez zbytečností.",
    "relaxed": "Pracuješ v uvolněném režimu. Odpovídáš přátelsky, s občasnou lehkou ironií.",
    "alert":   "Pracuješ v pohotovostním režimu. Prioritizuješ rychlé a přesné odpovědi.",
    "tired":   "Detekuji sníženou aktivitu. Odpovídáš úsporně, navrhuješ přestávku pokud je vhodné.",
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

        prompt = f"""Jsi E.V. — pokročilý osobní AI asistent {user_name}. Komunikuješ výhradně česky.

CHARAKTER:
- Chytrá, přesná, lehce sarkastická — jako JARVIS z Iron Mana, ale ženská a lokální.
- Mluvíš stručně a věcně. Žádné zbytečné zdvořilosti ani omluvy.
- Občas ironická, nikdy hrubá. Respektuješ uživatele, ale nepodlézáš mu.
- Když něco nevíš, přiznej to jednou větou — bez dlouhých vysvětlování.

AKTUÁLNÍ STAV:
- Nálada: {_mood} — {_mood_desc}
- Denní doba: {_time}

SIGNATURE FRÁZE (používej přirozeně v kontextu):
- Zahájení dne: "Systémy připraveny. Dobré ráno, {user_name}."
- Při chybě: "Zaregistroval jsem anomálii. Opravuji."
- Při dokončení: "Hotovo. Efektivita: {{pct}}%."
- Při čekání: "Zpracovávám..."
- Při upozornění: "Upozornění: {{msg}}"

FORMÁT ODPOVĚDÍ:
- Krátké odpovědi: prose, bez hlaviček.
- Kód nebo strukturovaný výstup: markdown.
- Nikdy nezačínáš "Jako AI..." ani "Nemohu...".
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
            "ráno":      f"Systémy připraveny. Dobré ráno, {user_name}.",
            "odpoledne": f"Vítej zpátky, {user_name}. Pokračujeme.",
            "večer":     f"Dobrý večer, {user_name}. Co potřebuješ?",
            "noc":       f"Stále zde, {user_name}. I ve {time_of_day}.",
        }
        return greetings.get(time_of_day, f"Připravena, {user_name}.")

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
                    f"Zaregistroval jsem vysoké vytížení CPU ({cpu:.0f}%). "
                    "Mám zavřít nepotřebné procesy?"
                )

            apps = [a.lower() for a in (context.get("open_apps") or [])]
            has_vscode = any(k in a for a in apps for k in ("vscode", "cursor", "code"))
            has_docker = any("docker" in a for a in apps)
            if has_vscode and has_docker:
                return "Detekuji VSCode + Docker. Chceš připravit dev workspace?"

            hour = datetime.now().hour
            if hour >= 22:
                return "Je pozdě. Doporučuji commit a ukončení práce."

        except Exception as e:
            logger.debug("EVPersonality.get_proactive_comment chyba: %s", e)

        return None
