"""
JARVIS Skill — Web Fetch
Načítá obsah webových stránek a vyhledává na DuckDuckGo.
Nepotřebuje API klíč ani MCP server — přímé HTTP přes requests.

Příkazy:
  „načti stránku github.com/python"   → obsah stránky jako text
  „hledej online Python asyncio"      → DuckDuckGo výsledky
  „obsah webu https://..."            → surový obsah URL
"""

import re
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ── Patterny ──────────────────────────────────────────

_FETCH_RE = re.compile(
    r"\b(nacti\s+stranku|obsah\s+webu|fetch\s+url|zobraz\s+web)\b\s+(https?://\S+|\S+\.\S+)",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"\b(hledej\s+online|duckduckgo|ddg|hledej\s+na\s+(webu|internetu))\b\s+(.+)",
    re.IGNORECASE,
)


def _html_to_text(html: str) -> str:
    """Jednoduchý HTML → plain text (bez BeautifulSoup)."""
    import re as _re
    # Odstraň skripty a styly
    html = _re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=_re.DOTALL | _re.IGNORECASE)
    html = _re.sub(r"<style[^>]*>.*?</style>",  " ", html, flags=_re.DOTALL | _re.IGNORECASE)
    # Odstraň HTML tagy
    html = _re.sub(r"<[^>]+>", " ", html)
    # Odstraň nadbytečné bílé znaky
    html = _re.sub(r"[ \t]{2,}", " ", html)
    html = _re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def _fetch(url: str, max_chars: int = 3000) -> str:
    try:
        import requests
        if not url.startswith("http"):
            url = "https://" + url
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JARVIS/3.1)"
        })
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "html" in ct:
            text = _html_to_text(r.text)
        else:
            text = r.text
        if len(text) > max_chars:
            text = text[:max_chars] + "\n…(zkráceno)"
        return text
    except Exception as e:
        return f"Chyba načítání stránky: {e}"


def _ddg_search(query: str, max_chars: int = 2500) -> str:
    """Vyhledá na DuckDuckGo Lite a vrátí výsledky jako text."""
    try:
        import requests
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JARVIS/3.1)",
            "Accept-Language": "cs,en;q=0.9",
        })
        r.raise_for_status()
        # Extrahuj jen výsledky (title + snippet)
        import re as _re
        titles   = _re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', r.text, _re.DOTALL)
        snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</div>', r.text, _re.DOTALL)
        # Fallback — prostý text
        if not titles:
            return _html_to_text(r.text)[:max_chars]
        lines = []
        for i, (t, s) in enumerate(zip(titles[:5], snippets[:5]), 1):
            t_clean = _re.sub(r"<[^>]+>", "", t).strip()
            s_clean = _re.sub(r"<[^>]+>", "", s).strip()
            if t_clean:
                lines.append(f"{i}. **{t_clean}**")
            if s_clean:
                lines.append(f"   {s_clean}")
        result = "\n".join(lines)
        return result[:max_chars] if result else _html_to_text(r.text)[:max_chars]
    except Exception as e:
        return f"Vyhledávání selhalo: {e}"


# ── Handlery ──────────────────────────────────────────

def _handle_fetch(text: str):
    m = _FETCH_RE.search(text)
    if not m:
        return None, None
    url = m.group(2).strip()
    content = _fetch(url)
    return f"**{url}**:\n\n{content}", {"action": "answer", "params": {}}


def _handle_search(text: str):
    m = _SEARCH_RE.search(text)
    if not m:
        return None, None
    query = m.group(3).strip()
    result = _ddg_search(query)
    return f"**DuckDuckGo: {query}**\n\n{result}", {"action": "answer", "params": {}}


def get_routes():
    return [
        {"pattern": _FETCH_RE,  "handler": _handle_fetch},
        {"pattern": _SEARCH_RE, "handler": _handle_search},
    ]


def get_actions():
    return {}
