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

_MONTH_ADJ = (
    "lednové", "únorové", "březnové", "dubnové",
    "květnové", "červnové", "červencové", "srpnové",
    "zářijové", "říjnové", "listopadové", "prosincové",
)

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
            greeting = f"## Odpolední aktualizace systémů E.V., {user_name}. 🌤️"
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


def _speech_hello(user_name: str, hour: int) -> str:
    if 5 <= hour < 12:
        return f"Čau {user_name}. Dobré ráno. Jsem tady."
    if 12 <= hour < 18:
        return f"Čau {user_name}. Jsem tady."
    if 18 <= hour < 22:
        return f"Čau {user_name}. Dobrý večer. Jsem tady."
    return f"Čau {user_name}. Pořád tady."


def _weather_line(weather: dict, now: datetime) -> str:
    desc = str(weather.get("desc") or "").lower()
    temp = weather.get("temp")
    if temp is None:
        return f"Venku je {desc}." if desc else "Počasí teď nemám."
    deg = int(round(float(temp)))
    advice = _weather_advice(float(temp), desc)
    if deg >= 26:
        month = _MONTH_ADJ[now.month - 1]
        line = f"Venku je {deg} stupňů, takže klasický {month} peklíčko."
    elif deg <= 3:
        line = f"Venku je {deg} stupňů. Zima."
    elif desc:
        line = f"Venku je {deg} stupňů, {desc}."
    else:
        line = f"Venku je {deg} stupňů."
    if advice:
        return f"{line} {advice}"
    return line


def _weather_advice(temp: float | None, desc: str) -> str:
    d = (desc or "").lower()
    if any(k in d for k in ("déšť", "dest", "přeháň", "mrhol", "bouř")):
        return "Vem deštník."
    if any(k in d for k in ("sníh", "snih")):
        return "Sněží, obuj se pořádně."
    if temp is not None and temp <= 3:
        return "Vrstvy se hodí."
    if temp is not None and temp >= 28:
        return "Vodu měj po ruce."
    return ""


def fetch_weather_facts(city: str = "Praha") -> dict | None:
    """Aktuální počasí pro mluvený briefing. Bez sítě vrátí None."""
    try:
        import requests
        from commands.utils import _normalize_city_name

        target = _normalize_city_name(city or "Praha")
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": target, "count": 3, "language": "cs", "format": "json"},
            timeout=3,
        ).json()
        results = geo.get("results") or []
        if not results:
            return None
        loc = next((r for r in results if r.get("country_code") == "CZ"), results[0])
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "current": "temperature_2m,apparent_temperature,weather_code",
                "timezone": "auto",
            },
            timeout=3,
        ).json()
        cur = weather.get("current") or {}
        wmo = {
            0: "jasno", 1: "převážně jasno", 2: "polojasno", 3: "zataženo",
            45: "mlha", 48: "mlha", 51: "mrholení", 61: "slabý déšť",
            63: "déšť", 65: "silný déšť", 71: "slabý sníh", 73: "sníh",
            80: "přeháňky", 95: "bouřka",
        }
        code = int(cur.get("weather_code") or 0)
        temp = cur.get("temperature_2m")
        return {
            "city": loc.get("name") or target,
            "desc": wmo.get(code, "proměnlivé počasí"),
            "temp": float(temp) if temp is not None else None,
        }
    except Exception as e:
        logger.debug("Počasí pro briefing nedostupné: %s", e)
        return None


def fetch_today_calendar(ical_url: str = "", now: datetime | None = None) -> list[dict]:
    """Dnešní nadcházející události z iCal URL."""
    url = (ical_url or "").strip()
    if not url:
        return []
    try:
        import re
        import requests

        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        now = now or datetime.now()
        today = now.date()
        out: list[dict] = []
        for ev_raw in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", resp.text, re.DOTALL):
            summary_m = re.search(r"SUMMARY:(.*?)(?:\r?\n)", ev_raw)
            dtstart_m = re.search(r"DTSTART(?:;[^:]+)?:(.*?)(?:\r?\n)", ev_raw)
            if not (summary_m and dtstart_m):
                continue
            summary = summary_m.group(1).strip()
            dt_str = dtstart_m.group(1).strip().replace("Z", "")
            try:
                if "T" in dt_str:
                    dt = datetime.strptime(dt_str[:15], "%Y%m%dT%H%M%S")
                    all_day = False
                else:
                    dt = datetime.strptime(dt_str[:8], "%Y%m%d")
                    all_day = True
            except ValueError:
                continue
            if dt.date() != today:
                continue
            if not all_day and dt < now - timedelta(minutes=20):
                continue
            out.append({
                "summary": summary,
                "time": "celý den" if all_day else dt.strftime("%H:%M"),
                "dt": dt,
            })
        out.sort(key=lambda e: e["dt"])
        return out[:5]
    except Exception as e:
        logger.debug("Kalendář pro briefing nedostupný: %s", e)
        return []


def spoken_hello(user_name: str = "Simone") -> str:
    """Krátký pozdrav při startu — bez sítě, hned k mluvení."""
    name = (user_name or "Simone").strip() or "Simone"
    return _speech_hello(name, datetime.now().hour)


def spoken_home_briefing(
    user_name: str = "Simone",
    *,
    now: datetime | None = None,
    weather: dict | None = ...,
    events: list[dict] | None = ...,
    calendar_configured: bool | None = None,
    include_hello: bool = True,
) -> str:
    """Lidský mluvený briefing na úvodní stránku: pozdrav, počasí, kalendář."""
    now = now or datetime.now()
    name = (user_name or "Simone").strip() or "Simone"

    if weather is ...:
        try:
            from config import CONFIG
            city = str(CONFIG.get("weather_city") or "Praha")
        except Exception:
            city = "Praha"
        weather = fetch_weather_facts(city)
    if events is ...:
        url = ""
        try:
            from config import CONFIG
            url = str(CONFIG.get("calendar_ical_url") or "")
        except Exception:
            url = ""
        import os
        url = url or os.environ.get("CALENDAR_ICAL_URL", "")
        events = fetch_today_calendar(url, now=now)
        if calendar_configured is None:
            calendar_configured = bool(url)
    elif calendar_configured is None:
        calendar_configured = True

    parts: list[str] = []
    if include_hello:
        parts.append(_speech_hello(name, now.hour))
    parts.append("Všechno běží, nic nehoří.")

    if weather and (weather.get("desc") or weather.get("temp") is not None):
        parts.append(_weather_line(weather, now))
    else:
        parts.append("Počasí teď nemám. Zkusím to znovu, když budeš chtít.")

    evs = list(events or [])
    if evs:
        if len(evs) == 1:
            e = evs[0]
            when = e.get("time") or ""
            title = e.get("summary") or "událost"
            if when == "celý den":
                parts.append(f"V kalendáři máš dnes {title}, celý den.")
            else:
                parts.append(f"V kalendáři máš {title} v {when}.")
        else:
            listed = "; ".join(
                f"{e.get('summary')} v {e.get('time')}" for e in evs[:3]
            )
            parts.append(f"V kalendáři na dnes: {listed}.")
    elif calendar_configured:
        parts.append("Kalendář je tichý. Volný zbytek dne.")
    else:
        parts.append("Kalendář ještě nemám. Schůzky nehlídám — hodíš mi odkaz, když budeš chtít.")

    parts.append("Co chceš dělat jako první?")
    return " ".join(p.strip() for p in parts if p and str(p).strip())


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
