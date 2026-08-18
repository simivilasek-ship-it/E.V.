"""
E.V. Morning Briefing
Proactive daily briefing sent via notify-send + injected into chat on first open.
"""
from __future__ import annotations

import json
import logging
import subprocess
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_JARVIS_DIR = Path.home() / ".jarvis"
_BRIEFING_LOG = _JARVIS_DIR / "briefing.log"
_BRIEFING_STATE = _JARVIS_DIR / "briefing_state.json"

_DAYS_CS = [
    "pondělí", "úterý", "středa", "čtvrtek",
    "pátek", "sobota", "neděle",
]

_GIT_SEARCH_DIRS = [
    Path.home() / "projects",
    Path.home() / "dev",
    Path.home() / "code",
    Path.home() / "src",
    Path.cwd(),
]


def _find_dirty_repos() -> list[str]:
    """Return list of directory names with uncommitted git changes."""
    dirty: list[str] = []
    checked: set[str] = set()

    candidates: list[Path] = []
    for base in _GIT_SEARCH_DIRS:
        if not base.is_dir():
            continue
        if (base / ".git").is_dir():
            candidates.append(base)
        else:
            try:
                for sub in base.iterdir():
                    if sub.is_dir() and (sub / ".git").is_dir():
                        candidates.append(sub)
            except PermissionError:
                pass

    for repo in candidates:
        key = str(repo.resolve())
        if key in checked:
            continue
        checked.add(key)
        try:
            r = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                dirty.append(repo.name)
        except Exception:
            pass

    return dirty


def _get_yesterday_summary() -> str:
    """Retrieve yesterday's activity summary from activity_store."""
    yesterday = date.today() - timedelta(days=1)
    try:
        from activity_store import get_activity_store
        data = get_activity_store().daily_summary(yesterday)
        text = data.get("summary_text", "")
        if text:
            return text[:200]
    except Exception:
        pass
    return "žádná zaznamenaná aktivita"


class MorningBriefing:
    """Generates a Czech-language morning briefing string."""

    def generate(self, user_name: str = "Simone") -> str:
        now = datetime.now()
        day_name = _DAYS_CS[now.weekday()]
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M")

        yesterday_summary = _get_yesterday_summary()
        dirty_repos = _find_dirty_repos()

        hour = now.hour
        if hour < 12:
            greeting = f"## Dobré ráno, {user_name}. Systémy E.V. jsou online. ☀️"
        elif hour < 18:
            greeting = f"## Odpolední aktualizace systémů, {user_name}. 🌤️"
        else:
            greeting = f"## Večerní přehled, {user_name}. Systémy E.V. v nočním módu. 🌙"

        narrative_parts = [
            greeting,
            "",
            f"**Datum:** {day_name} **{date_str}** · **Čas:** {time_str}",
            "",
        ]

        if dirty_repos:
            narrative_parts += [
                "**📂 Otevřené projekty s necommitovanými změnami:**",
            ]
            for repo in dirty_repos[:3]:
                narrative_parts.append(f"- `{repo}`")
            narrative_parts.append("")
        else:
            narrative_parts += ["**📂 Git:** Všechny projekty jsou čisté. ✓", ""]

        narrative_parts += [
            f"**📊 Včerejší aktivita:** {yesterday_summary}",
            "",
            "> 💡 Napiš **\"co mám dělat dnes\"** nebo **\"připrav workspace\"** pro zahájení práce.",
        ]

        return "\n".join(narrative_parts)


def send_briefing() -> str:
    """Generate, display via notify-send, log, and return the briefing text."""
    briefing = MorningBriefing().generate()

    # Send desktop notification
    try:
        subprocess.run(
            ["notify-send", "E.V.", briefing, "--icon=dialog-information"],
            timeout=5,
            capture_output=True,
        )
    except FileNotFoundError:
        logger.debug("notify-send není dostupný — přeskakuji notifikaci.")
    except Exception as e:
        logger.warning("notify-send selhal: %s", e)

    # Log to file
    _JARVIS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _BRIEFING_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}]\n{briefing}\n\n")
    except Exception as e:
        logger.warning("Nelze zapsat briefing.log: %s", e)

    logger.info("Morning briefing odeslán.")
    return briefing


def schedule_briefing(hour: int = 8, minute: int = 0) -> None:
    """Schedule send_briefing() to fire today (or tomorrow if already past)."""
    _JARVIS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)

    delay = (target - now).total_seconds()

    def _fire() -> None:
        try:
            send_briefing()
        except Exception as e:
            logger.error("Briefing selhal: %s", e)
        # Reschedule for next day after firing
        schedule_briefing(hour=hour, minute=minute)

    t = threading.Timer(delay, _fire)
    t.daemon = True
    t.start()

    # Persist schedule state
    try:
        state = {
            "scheduled_hour": hour,
            "scheduled_minute": minute,
            "next_fire": target.isoformat(),
        }
        _BRIEFING_STATE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning("Nelze uložit briefing_state.json: %s", e)

    logger.info(
        "Briefing naplánován na %02d:%02d (za %.0f s).",
        hour,
        minute,
        delay,
    )


if __name__ == "__main__":
    print(send_briefing())
