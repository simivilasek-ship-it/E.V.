"""
JARVIS — User Profile
Permanentní úložiště faktů o uživateli (nikdy nedecays).
Fakta se extrahují automaticky z konverzací + lze ukládat ručně.

Příklady faktů:
  - jméno: "Petr"
  - jazyk: "čeština"
  - město: "Brno"
  - práce: "programátor"
  - zájmy: ["gaming", "python"]
"""

from __future__ import annotations
import json
import logging
import threading
import time
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


def _norm(text: str) -> str:
    """Odstraní diakritiku — stejná funkce jako v llm.py."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )

logger = logging.getLogger(__name__)

_PROFILE_PATH = Path.home() / ".jarvis_user_profile.json"

# Regex patterny pro automatickou extrakci faktů — BEZ diakritiky (STT text je normalizovaný)
# Všechny patterny jsou bez diakritiky — aplikují se na _norm(text)
_FACT_PATTERNS = [
    # Jméno
    (r"jmenuji?\s+se\s+(\w+)", "jméno"),
    (r"jmenuju\s+se\s+(\w+)", "jméno"),
    # Město / lokace
    (r"bydlim?\s+v\s+([\w\s]+?)(?:\.|,|$)", "město"),
    (r"jsem\s+z\s+([\w\s]+?)(?:\.|,|$)", "město"),
    # Profese (bez diakritiky)
    (r"jsem\s+(programator|developer|ucitel|doktor|inzenyr|student|designer|manazer|freelancer)", "profese"),
    (r"pracuji\s+jako\s+([\w\s]+?)(?:\.|,|$)", "profese"),
    (r"delam\s+jako\s+([\w\s]+?)(?:\.|,|$)", "profese"),
    # Preference
    (r"nerad\s+mam\s+([\w\s]+?)(?:\.|,|$)", "nelíbí"),
    (r"mam\s+rad\s+([\w\s]+?)(?:\.|,|$)", "zájmy"),
    (r"bavi\s+me\s+([\w\s]+?)(?:\.|,|$)", "zájmy"),
    (r"zajima\s+me\s+([\w\s]+?)(?:\.|,|$)", "zájmy"),
]


@dataclass
class UserFact:
    key: str            # kategorie faktu (jméno, město, zájmy…)
    value: Any          # hodnota
    confidence: float   # 0.0–1.0
    source: str         # "manual" | "extracted" | "inferred"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "UserFact":
        return cls(**d)


class UserProfile:
    """
    Permanentní profil uživatele.
    Fakta mají confidence score — vysoká jistota přepíše nízkou.
    Ukládá se do ~/.jarvis_user_profile.json
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _PROFILE_PATH
        self._facts: Dict[str, UserFact] = {}
        self._lock = threading.Lock()
        self._load()

    # ── CRUD ──────────────────────────────────────────

    def set(self, key: str, value: Any, confidence: float = 0.8,
            source: str = "manual") -> None:
        """Uloží nebo aktualizuje fakt (přepíše jen pokud nová confidence >= stará)."""
        with self._lock:
            existing = self._facts.get(key)
            if existing and existing.confidence > confidence:
                logger.debug(f"Profil: '{key}' zachován (confidence {existing.confidence} > {confidence})")
                return
            self._facts[key] = UserFact(key=key, value=value,
                                        confidence=confidence, source=source)
        self._save()
        logger.info(f"Profil: {key} = {value!r} [{source}, conf={confidence}]")

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            fact = self._facts.get(key)
            return fact.value if fact else default

    def get_fact(self, key: str) -> Optional[UserFact]:
        with self._lock:
            return self._facts.get(key)

    def all_facts(self) -> Dict[str, Any]:
        with self._lock:
            return {k: f.value for k, f in self._facts.items()}

    def remove(self, key: str) -> bool:
        with self._lock:
            if key in self._facts:
                del self._facts[key]
                self._save()
                return True
        return False

    def summary(self) -> str:
        """Vrátí textový souhrn profilu pro LLM kontext."""
        facts = self.all_facts()
        if not facts:
            return ""
        lines = ["Fakta o uživateli:"]
        for k, v in facts.items():
            if isinstance(v, list):
                lines.append(f"  {k}: {', '.join(str(x) for x in v)}")
            else:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    # ── Auto-extrakce z textu ─────────────────────────

    def extract_from_text(self, text: str) -> List[str]:
        """Zkusí extrahovat fakta z textu uživatele. Vrátí seznam nalezených klíčů."""
        import re
        normalized = _norm(text)   # odstraň diakritiku — STT text může být bez ní
        found = []
        for pattern, key in _FACT_PATTERNS:
            m = re.search(pattern, normalized, re.IGNORECASE)
            if m:
                value = m.group(1).strip().rstrip(".,!")
                if len(value) > 1:
                    # Zájmy ukládáme jako seznam
                    if key in ("zájmy", "nelíbí"):
                        existing = self.get(key) or []
                        if isinstance(existing, list) and value not in existing:
                            existing.append(value)
                            value = existing
                    self.set(key, value, confidence=0.6, source="extracted")
                    found.append(key)
        return found

    # ── Persistence ───────────────────────────────────

    def _save(self) -> None:
        try:
            data = {k: f.to_dict() for k, f in self._facts.items()}
            self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        except Exception as e:
            logger.warning(f"Profil: chyba uložení: {e}")

    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._facts = {k: UserFact.from_dict(v) for k, v in data.items()}
                logger.info(f"Profil načten: {len(self._facts)} faktů")
        except Exception as e:
            logger.warning(f"Profil: chyba načtení: {e}")


# ── Singleton ─────────────────────────────────────────

_profile: Optional[UserProfile] = None


def get_user_profile() -> UserProfile:
    global _profile
    if _profile is None:
        _profile = UserProfile()
    return _profile
