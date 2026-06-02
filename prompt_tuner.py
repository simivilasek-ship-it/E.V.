"""
JARVIS Prompt Tuner
Sleduje úspěšnost odpovědí a učí se jaké systémové prompty fungují nejlépe.
"""
from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

TUNER_FILE = Path.home() / ".jarvis" / "prompt_scores.json"


@dataclass
class PromptVariant:
    """Jedna varianta system promptu s metrikami."""
    variant_id: str
    system_prompt: str
    uses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    avg_response_length: float = 0.0

    @property
    def score(self) -> float:
        if self.uses == 0:
            return 0.5  # neutral
        return (self.positive_feedback + 0.5) / (self.uses + 1)


class PromptTuner:
    """Automaticky optimalizuje systémové prompty na základě zpětné vazby."""

    VARIANTS = {
        "stručný": "Odpovídej stručně a přímo. Vyhni se zbytečným vysvětlením.",
        "podrobný": "Odpovídej detailně s příklady. Vysvětli každý krok.",
        "technický": "Odpovídej technicky přesně. Používej správnou terminologii.",
        "conversational": "Odpovídej přátelsky a přirozeně jako v rozhovoru.",
    }

    def __init__(self):
        self._scores: dict[str, PromptVariant] = {}
        self._load()
        # Inicializuj varianty pokud chybí
        for vid, prompt in self.VARIANTS.items():
            if vid not in self._scores:
                self._scores[vid] = PromptVariant(variant_id=vid, system_prompt=prompt)

    def get_best_variant(self) -> str:
        """Vrátí system prompt s nejvyšším skóre (UCB1 exploration)."""
        if not self._scores:
            return ""
        total_uses = sum(v.uses for v in self._scores.values())
        import math
        best, best_ucb = None, -1
        for v in self._scores.values():
            if v.uses == 0:
                return v.system_prompt  # Explore unused
            ucb = v.score + math.sqrt(2 * math.log(total_uses + 1) / v.uses)
            if ucb > best_ucb:
                best, best_ucb = v, ucb
        return best.system_prompt if best else ""

    def get_best_variant_id(self) -> str:
        """Vrátí ID varianty s nejvyšším skóre (UCB1 exploration)."""
        if not self._scores:
            return ""
        total_uses = sum(v.uses for v in self._scores.values())
        import math
        best, best_ucb = None, -1
        for v in self._scores.values():
            if v.uses == 0:
                return v.variant_id  # Explore unused
            ucb = v.score + math.sqrt(2 * math.log(total_uses + 1) / v.uses)
            if ucb > best_ucb:
                best, best_ucb = v, ucb
        return best.variant_id if best else ""

    def record_use(self, variant_id: str, response_length: int) -> None:
        """Zaznamená použití varianty."""
        if variant_id in self._scores:
            v = self._scores[variant_id]
            v.uses += 1
            v.avg_response_length = (v.avg_response_length * (v.uses - 1) + response_length) / v.uses
            self._save()

    def record_feedback(self, variant_id: str, positive: bool) -> None:
        """Zaznamená uživatelskou zpětnou vazbu (palec nahoru/dolů)."""
        if variant_id in self._scores:
            if positive:
                self._scores[variant_id].positive_feedback += 1
            else:
                self._scores[variant_id].negative_feedback += 1
            self._save()

    def stats(self) -> str:
        lines = ["Prompt Tuner Statistics:"]
        for v in sorted(self._scores.values(), key=lambda x: -x.score):
            lines.append(
                f"  [{v.variant_id}] score={v.score:.2f} uses={v.uses} "
                f"+{v.positive_feedback}/-{v.negative_feedback}"
            )
        return "\n".join(lines)

    def _save(self) -> None:
        try:
            TUNER_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: asdict(v) for k, v in self._scores.items()}
            TUNER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"PromptTuner save chyba: {e}")

    def _load(self) -> None:
        try:
            if TUNER_FILE.exists():
                data = json.loads(TUNER_FILE.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._scores[k] = PromptVariant(**v)
        except Exception as e:
            logger.debug(f"PromptTuner load chyba: {e}")


_tuner: Optional[PromptTuner] = None


def get_prompt_tuner() -> PromptTuner:
    global _tuner
    if _tuner is None:
        _tuner = PromptTuner()
    return _tuner
