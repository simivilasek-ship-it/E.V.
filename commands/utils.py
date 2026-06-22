"""Utility příkazy: kalkulačka, překlad, poznámky, počasí, Wikipedia, měna."""

from __future__ import annotations

import logging
import math
import os
import subprocess
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


# ── Bezpečný subprocess helper ────────────────────────


def safe_run(
    cmd: List[str],
    timeout: float = 30.0,
    cwd: Optional[str] = None,
    bg: bool = False,
) -> Dict[str, Any]:
    """Spustí příkaz bezpečně — vždy bez shell=True.

    Args:
        cmd:     příkaz jako list (nikdy string se shell=True)
        timeout: maximální doba čekání v sekundách (ignorováno pokud bg=True)
        cwd:     pracovní adresář (None = aktuální)
        bg:      True = spusť na pozadí a ihned vrať (Popen, timeout se neaplikuje)

    Returns:
        {"rc": int, "stdout": str, "stderr": str, "timeout": bool}
    """
    if not isinstance(cmd, list) or not cmd:
        raise ValueError(f"safe_run: cmd musí být neprázdný list, dostal: {cmd!r}")

    if bg:
        try:
            subprocess.Popen(cmd, cwd=cwd,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            logger.warning(f"safe_run bg: příkaz nenalezen: {cmd[0]}")
            return {"rc": -1, "stdout": "", "stderr": f"nenalezen: {cmd[0]}", "timeout": False}
        return {"rc": 0, "stdout": "", "stderr": "", "timeout": False}

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr, "timeout": False}
    except subprocess.TimeoutExpired:
        logger.warning(f"safe_run timeout ({timeout}s): {cmd}")
        return {"rc": -1, "stdout": "", "stderr": "timeout", "timeout": True}
    except FileNotFoundError:
        return {"rc": -1, "stdout": "", "stderr": f"nenalezen: {cmd[0]}", "timeout": False}
    except Exception as e:
        logger.error(f"safe_run chyba {cmd}: {e}")
        return {"rc": -1, "stdout": "", "stderr": str(e), "timeout": False}

_HOME = str(Path.home())


# ── Vstupní validace ─────────────────────────────────

_PKG_RE = __import__("re").compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\_\.+]*$")


def validate_package_name(name: str) -> str:
    """Ověří název apt balíčku — povoleny jen bezpečné znaky.

    Returns:
        Oříznutý název pokud je validní.
    Raises:
        ValueError: pokud název obsahuje nebezpečné znaky.
    """
    name = name.strip()
    if not name:
        raise ValueError("Název balíčku nesmí být prázdný")
    if len(name) > 128:
        raise ValueError("Název balíčku je příliš dlouhý")
    if not _PKG_RE.match(name):
        raise ValueError(f"Neplatný název balíčku: {name!r} "
                         "(povoleno: a-z A-Z 0-9 - _ . +)")
    return name


def validate_path(path: str, must_exist: bool = False) -> Path:
    """Canonicalizuje cestu a zabrání path traversal útokům.

    Pravidla:
    - Expanduje ~ a proměnné prostředí
    - Zabrání ../../../etc/passwd stylu přes resolve()
    - Odmítne prázdné cesty

    Returns:
        Absolutní Path objekt.
    Raises:
        ValueError: pokud je cesta prázdná nebo nebezpečná.
    """
    if not path or not path.strip():
        raise ValueError("Cesta nesmí být prázdná")
    p = Path(path.strip()).expanduser()
    try:
        resolved = p.resolve()
    except Exception as e:
        raise ValueError(f"Nelze zpracovat cestu: {e}") from e
    if must_exist and not resolved.exists():
        raise ValueError(f"Cesta neexistuje: {resolved}")
    return resolved


def normalize_text(text: str) -> str:
    """Odstraní diakritiku pro robustní matching (otevři == otevri)."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    )


def cmd_calculate(expr: str) -> str:
    import ast as _ast
    import operator as _op

    if len(expr) > 500:
        return "Chyba: výraz je příliš dlouhý (max 500 znaků)"

    ALLOWED_NAMES = {
        "sqrt": math.sqrt, "pow": math.pow, "abs": abs,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10,
        "ceil": math.ceil, "floor": math.floor,
        "round": round, "pi": math.pi, "e": math.e,
    }
    OPERATORS = {
        _ast.Add: _op.add, _ast.Sub: _op.sub, _ast.Mult: _op.mul,
        _ast.Div: _op.truediv, _ast.Pow: _op.pow, _ast.Mod: _op.mod,
        _ast.FloorDiv: _op.floordiv,
    }

    def _eval(node, depth=0):
        if depth > 50:
            raise ValueError("Příliš hluboký výraz")
        if isinstance(node, _ast.Expression):
            return _eval(node.body, depth + 1)
        if isinstance(node, _ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Pouze čísla jsou povolena")
        if isinstance(node, _ast.BinOp):
            op = type(node.op)
            if op in OPERATORS:
                left  = _eval(node.left,  depth + 1)
                right = _eval(node.right, depth + 1)
                if op is _ast.Pow and isinstance(right, (int, float)) and abs(right) > 300:
                    raise ValueError("Exponent je příliš velký (max 300)")
                return OPERATORS[op](left, right)
            raise ValueError("Nepodporovaný operátor")
        if isinstance(node, _ast.UnaryOp):
            val = _eval(node.operand, depth + 1)
            return -val if isinstance(node.op, _ast.USub) else val
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Name) and node.func.id in ALLOWED_NAMES:
                return ALLOWED_NAMES[node.func.id](
                    *[_eval(a, depth + 1) for a in node.args])
            raise ValueError("Neznámá funkce")
        if isinstance(node, _ast.Name):
            if node.id in ALLOWED_NAMES:
                return ALLOWED_NAMES[node.id]
            raise ValueError("Neznámé jméno")
        raise ValueError(f"Nepodporovaný uzel: {type(node).__name__}")

    try:
        expr_clean = expr.strip().replace(",", ".").replace("^", "**")
        tree = _ast.parse(expr_clean, mode="eval")
        for n in _ast.walk(tree):
            if not isinstance(n, (
                _ast.Expression, _ast.BinOp, _ast.UnaryOp, _ast.Constant,
                _ast.Add, _ast.Sub, _ast.Mult, _ast.Div, _ast.Pow,
                _ast.Mod, _ast.FloorDiv, _ast.USub, _ast.UAdd,
                _ast.Call, _ast.Name, _ast.Load,
            )):
                return f"Chyba: zakázaný výraz ({type(n).__name__})"
        result = _eval(tree)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return f"{result:.10g}" if isinstance(result, float) else str(result)
    except Exception as e:
        return f"Chyba výpočtu: {e}"


def cmd_translate(text: str, from_lang: str = "auto", to_lang: str = "cs",
                  ollama_model: str = "qwen2.5:3b",
                  ollama_url: str = "http://localhost:11434/api/chat") -> str:
    import requests as _req
    lang_map = {
        "cs": "češtiny", "en": "angličtiny", "de": "němčiny",
        "fr": "francouzštiny", "es": "španělštiny", "sk": "slovenštiny",
    }
    to_name = lang_map.get(to_lang, to_lang)
    prompt  = f"Přelož přesně do {to_name}, vrať pouze překlad bez vysvětlení:\n{text}"
    payload = {
        "model": ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 500},
    }
    try:
        r = _req.post(ollama_url, json=payload, timeout=30)
        r.raise_for_status()
        translated = r.json().get("message", {}).get("content", "").strip()
        return f"Překlad: {translated}"
    except Exception as e:
        return f"Chyba překladu: {e}"


def cmd_note_add(note: str) -> str:
    notes_file = os.path.join(_HOME, "jarvis_notes.txt")
    with open(notes_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {note}\n")
    return "Poznámka uložena."


def cmd_note_list() -> str:
    notes_file = os.path.join(_HOME, "jarvis_notes.txt")
    if os.path.exists(notes_file):
        notes = open(notes_file, "r", encoding="utf-8").read().strip()
        return notes if notes else "Žádné poznámky."
    return "Žádné poznámky."


def cmd_reminder_set(text: str, time_str: str = "1 minuta") -> str:
    def remind():
        time.sleep(60)
        logger.info(f"Připomínka: {text}")

    threading.Thread(target=remind, daemon=True).start()
    return f"Připomínka nastavena: {text}"


def _normalize_city_name(city: str) -> str:
    """Převod českých sklonění / překlepů na správný název města."""
    key = (city or "").strip().lower().rstrip("?.,!")
    aliases = {
        "praha": "Praha", "praze": "Praha", "prague": "Praha",
        "ostrava": "Ostrava", "ostrave": "Ostrava",
        "brno": "Brno", "brne": "Brno",
        "opava": "Opava", "opave": "Opava",
        "plzen": "Plzeň", "plzni": "Plzeň", "plzeň": "Plzeň",
        "bratislava": "Bratislava", "bratislave": "Bratislava",
        "olomouc": "Olomouc", "olomouci": "Olomouc",
        "liberec": "Liberec", "liberci": "Liberec",
    }
    return aliases.get(key, city.strip().title() if city else "Praha")


def cmd_weather(city: str = "") -> str:
    """Počasí přes Open-Meteo (free, bez API klíče) + wttr.in fallback."""
    import requests

    # WMO weather kódy → emoji + popis
    _WMO = {
        0: ("☀️",  "Jasno"),
        1: ("🌤️", "Převážně jasno"), 2: ("⛅", "Polojasno"), 3: ("☁️", "Zataženo"),
        45: ("🌫️","Mlha"), 48: ("🌫️","Námrazová mlha"),
        51: ("🌦️","Slabé mrholení"), 53: ("🌦️","Mrholení"), 55: ("🌧️","Silné mrholení"),
        61: ("🌧️","Slabý déšť"), 63: ("🌧️","Déšť"), 65: ("🌧️","Silný déšť"),
        71: ("🌨️","Slabý sníh"), 73: ("❄️","Sníh"), 75: ("❄️","Silný sníh"),
        77: ("🌨️","Sněhové vločky"),
        80: ("🌦️","Přeháňky"), 81: ("🌧️","Silné přeháňky"), 82: ("⛈️","Průtrž"),
        85: ("🌨️","Sněhové přeháňky"), 86: ("❄️","Silné sněhové přeháňky"),
        95: ("⛈️","Bouřka"), 96: ("⛈️","Bouřka s krupobitím"), 99: ("⛈️","Silná bouřka"),
    }

    target = _normalize_city_name(city)

    try:
        # 1. Geokódování — preferuj ČR u známých českých měst
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": target, "count": 5, "language": "cs", "format": "json"},
            timeout=3,
        ).json()
        results = geo.get("results") or []
        if not results:
            return f"Město '{target}' nenalezeno."
        loc = next(
            (r for r in results if r.get("country_code") == "CZ"),
            results[0],
        )
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc.get("name", target)
        country = loc.get("country", "")

        # 2. Aktuální počasí
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "current":   "temperature_2m,apparent_temperature,relative_humidity_2m,"
                             "wind_speed_10m,precipitation,weather_code",
                "timezone":  "auto",
                "wind_speed_unit": "kmh",
            },
            timeout=3,
        ).json()
        cur   = weather.get("current", {})
        code  = cur.get("weather_code", 0)
        emoji, desc = _WMO.get(code, ("🌡️", f"kód {code}"))
        temp  = cur.get("temperature_2m", "?")
        feels = cur.get("apparent_temperature", "?")
        humid = cur.get("relative_humidity_2m", "?")
        wind  = cur.get("wind_speed_10m", "?")
        precip = cur.get("precipitation", 0)

        result = (
            f"{emoji} {name}{', ' + country if country else ''}: {desc}\n"
            f"   🌡️ {temp}°C (pocitová {feels}°C)  💧 {humid}%  💨 {wind} km/h"
        )
        if precip and float(precip) > 0:
            result += f"  🌧️ {precip} mm"
        return result

    except Exception:
        # Rychlý fallback na wttr.in (3s timeout)
        try:
            r = requests.get(
                f"https://wttr.in/{quote(target or 'Prague')}?format=3",
                timeout=3, headers={"User-Agent": "curl/7.0"})
            text = r.text.strip()
            if text and "render failed" not in text.lower() and len(text) < 200:
                return text
        except Exception:
            pass
        return "⚠️ Počasí dočasně nedostupné (zkus znovu za chvíli)"


def cmd_wiki_search(query: str) -> str:
    import requests
    url = f"https://cs.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("extract", "Nenalezeno.").split(".")[0] + "."
        return "Nenalezeno na Wikipedii."
    except Exception as e:
        return f"Chyba: {e}"


def cmd_currency_convert(amount: float = 1.0, from_curr: str = "USD",
                         to_curr: str = "CZK") -> str:
    rates = {"USD": 1.0, "EUR": 0.85, "CZK": 25.0, "GBP": 0.73,
             "CHF": 0.9, "PLN": 4.0, "HUF": 370.0}
    fc, tc = from_curr.upper(), to_curr.upper()
    if fc in rates and tc in rates:
        result = amount * rates[tc] / rates[fc]
        return f"{amount} {fc} = {result:.2f} {tc}"
    return "Nepodporované měny."


def cmd_write_email(to: str = "", subject: str = "", body: str = "") -> str:
    import webbrowser
    mailto = f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
    webbrowser.open(mailto)
    return "ok"


def cmd_memory_recall(config: Dict[str, Any], query: str = "", top_k: int = 5) -> str:
    try:
        from memory import JarvisMemory
        mem     = JarvisMemory(config)
        results = mem.recall(query, top_k=top_k)
        if not results:
            return "Nic nenalezeno v paměti."
        resp = f"Nalezeno {len(results)} vzpomínek:\n"
        for i, r in enumerate(results, 1):
            resp += f"{i}. [{r['score']:.2f}] {r['content'][:100]}...\n"
        return resp
    except Exception as e:
        return f"Chyba paměti: {e}"


def cmd_memory_store(config: Dict[str, Any], content: str = "",
                     importance: float = 0.5) -> str:
    try:
        from memory import JarvisMemory
        mem_id = JarvisMemory(config).store(content, importance=importance)
        return f"Uloženo do paměti (ID: {mem_id})."
    except Exception as e:
        return f"Chyba: {e}"


def cmd_memory_stats(config: Dict[str, Any]) -> str:
    try:
        from memory import JarvisMemory
        stats = JarvisMemory(config).stats()
        return (f"Paměť: {stats.get('total_memories', 0)} položek, "
                f"průměrná důležitost: {stats.get('avg_importance', 0):.2f}")
    except Exception as e:
        return f"Chyba: {e}"


def cmd_memory_maintenance(config: Dict[str, Any]) -> str:
    try:
        from memory import JarvisMemory
        result = JarvisMemory(config).run_maintenance()
        return f"Údržba dokončena: {result}"
    except Exception as e:
        return f"Chyba: {e}"


# ══════════════════════════════════════════════════════
#  SPORTS — ESPN API (bez API klíče)
# ══════════════════════════════════════════════════════

# Mapování sport/liga → ESPN endpoint path
_SPORT_LEAGUES = {
    # Fotbal
    "premier league": "soccer/eng.1",
    "pl":             "soccer/eng.1",
    "champions league": "soccer/UEFA.CHAMPIONS",
    "ucl":            "soccer/UEFA.CHAMPIONS",
    "europa league":  "soccer/UEFA.EUROPA",
    "la liga":        "soccer/esp.1",
    "serie a":        "soccer/ita.1",
    "bundesliga":     "soccer/ger.1",
    "ligue 1":        "soccer/fra.1",
    "česká liga":     "soccer/CZE.1",
    "fortuna liga":   "soccer/CZE.1",
    "mls":            "soccer/usa.1",
    # Hokej
    "nhl":            "hockey/nhl",
    "hokej":          "hockey/nhl",
    # Basketball
    "nba":            "basketball/nba",
    "basket":         "basketball/nba",
    "basketball":     "basketball/nba",
    # Americký fotbal
    "nfl":            "football/nfl",
    # Baseball
    "mlb":            "baseball/mlb",
}

# Výchozí ligy pokud není specifikováno (nejpopulárnější)
_DEFAULT_LEAGUES = [
    ("⚽ Premier League",   "soccer/eng.1"),
    ("⚽ Champions League", "soccer/UEFA.CHAMPIONS"),
    ("⚽ La Liga",          "soccer/esp.1"),
    ("🏒 NHL",             "hockey/nhl"),
    ("🏀 NBA",             "basketball/nba"),
]

_STATUS_MAP = {
    "Scheduled":  "🕐 Naplánováno",
    "In Progress": "🔴 ŽIVĚ",
    "Halftime":   "⏸ Poločas",
    "Final":      "✅ Konec",
    "Full Time":  "✅ Konec",
    "Postponed":  "📅 Odloženo",
    "Canceled":   "❌ Zrušeno",
    "Suspended":  "⏸ Přerušeno",
}


def _fetch_espn_scores(league_path: str) -> list[dict]:
    """Načte výsledky/zápasy z ESPN API pro danou ligu."""
    import requests
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league_path}/scoreboard"
    r = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    events = r.json().get("events", [])
    results = []
    for ev in events:
        comp   = ev.get("competitions", [{}])[0]
        status = comp.get("status", {}).get("type", {}).get("description", "?")
        detail = comp.get("status", {}).get("type", {}).get("detail", "")
        clock  = comp.get("status", {}).get("displayClock", "")
        period = comp.get("status", {}).get("period", 0)

        teams = comp.get("competitors", [])
        home = next((t for t in teams if t.get("homeAway") == "home"), teams[0] if teams else {})
        away = next((t for t in teams if t.get("homeAway") == "away"), teams[1] if len(teams)>1 else {})

        home_name  = home.get("team", {}).get("displayName", "?")
        away_name  = away.get("team", {}).get("displayName", "?")
        home_score = home.get("score", "")
        away_score = away.get("score", "")

        # Datum/čas zápasu
        date_str = ev.get("date", "")
        try:
            from datetime import timezone
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            local_dt = dt.astimezone(timezone.utc)
            time_label = local_dt.strftime("%d.%m %H:%M")
        except Exception:
            time_label = date_str[:10]

        results.append({
            "home": home_name, "away": away_name,
            "home_score": home_score, "away_score": away_score,
            "status": status, "detail": detail,
            "clock": clock, "period": period,
            "time": time_label,
        })
    return results


def _format_match(m: dict) -> str:
    status_label = _STATUS_MAP.get(m["status"], m["status"])
    has_score = m["home_score"] != "" and m["away_score"] != ""

    if has_score:
        score = f"{m['home_score']} – {m['away_score']}"
        if m["status"] == "In Progress":
            # clock může být prázdné — fallback na periodu/poločas
            if m["clock"]:
                clock = f" ({m['clock']})"
            elif m.get("period"):
                clock = f" (p.{m['period']})"
            else:
                clock = " (nyní)"
            return f"{status_label}{clock}  {m['home']} {score} {m['away']}"
        return f"{status_label}  {m['home']} {score} {m['away']}"
    else:
        return f"{status_label} {m['time']}  {m['home']} vs {m['away']}"


def _brave_sports_search(search_query: str) -> str | None:
    """Vyhledá sportovní výsledky přes Brave Search API a naformátuje je."""
    try:
        from mcp_bridge import get_mcp_bridge
        bridge = get_mcp_bridge()
        if not bridge or not bridge.is_available("brave-search"):
            return None
        raw = bridge.call_tool("brave-search", "brave_web_search", {
            "query": search_query,
            "count": 8,
        })
        if not raw or raw == "(prázdný výsledek)" or "Chyba" in str(raw):
            return None

        # Pokus o parsování JSON výsledků do čitelné podoby
        import json as _json, re as _re
        lines = []
        # Každý řádek může být JSON objekt
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                title = obj.get("title", "")
                url   = obj.get("url", "")
                desc  = obj.get("description", "")
                if title:
                    lines.append(f"**{title}**")
                if desc:
                    # Zkrátit popis na 200 znaků
                    lines.append(f"  {desc[:200]}")
                if url:
                    lines.append(f"  🔗 {url}")
                lines.append("")
            except _json.JSONDecodeError:
                # Není JSON — přidej jako text
                if line and not line.startswith("{"):
                    lines.append(line)

        if not lines:
            # Fallback — raw text
            return raw[:2000] if len(raw) > 2000 else raw

        return "\n".join(lines).strip()
    except Exception:
        return None


def cmd_sports(query: str = "") -> str:
    """Sportovní výsledky — primárně Brave Search (aktuální data), fallback ESPN API.

    query může být: "fotbal", "premier league", "nhl", "nba", "výsledky dnes" atd.
    """

    q = query.lower().strip()
    today = datetime.now().strftime("%-d. %-m. %Y")

    # ── 1. Brave Search — aktuální data z webu ───────────────────────────────
    brave_query = f"sportovní výsledky dnes {query}".strip() if query else f"fotbalové výsledky dnes {today}"
    brave_result = _brave_sports_search(brave_query)
    if brave_result:
        return f"**Sportovní výsledky** *(Brave Search — živá data)*\n\n{brave_result}"

    # ── 2. Fallback: ESPN API ────────────────────────────────────────────────
    target_league = None
    target_label  = None
    for keyword, path in _SPORT_LEAGUES.items():
        if keyword in q:
            target_league = path
            target_label  = keyword.title()
            break

    lines = []

    if target_league:
        try:
            matches = _fetch_espn_scores(target_league)
            if not matches:
                return f"Žádné zápasy nenalezeny pro {target_label}."
            lines.append(f"**{target_label}** — {len(matches)} zápasů\n")
            for m in matches[:10]:
                lines.append(f"  {_format_match(m)}")
        except Exception as e:
            return f"Chyba při načítání dat pro {target_label}: {e}"
    else:
        lines.append(f"**Sportovní přehled — {today}**\n")

        found_any = False
        for label, path in _DEFAULT_LEAGUES:
            try:
                matches = _fetch_espn_scores(path)
                live    = [m for m in matches if m["status"] == "In Progress"]
                today_m = [m for m in matches if m["status"] in ("Scheduled", "In Progress", "Halftime")]
                ended   = [m for m in matches if "Final" in m["status"] or "Full Time" in m["status"]]

                if not matches:
                    continue

                found_any = True
                lines.append(f"{label}:")
                show = live or today_m or ended[:3]
                for m in show[:4]:
                    lines.append(f"  {_format_match(m)}")
                lines.append("")
            except Exception:
                continue

        if not found_any:
            return "Nepodařilo se načíst sportovní data. Zkus: 'premier league výsledky'"

    return "\n".join(lines).rstrip()
