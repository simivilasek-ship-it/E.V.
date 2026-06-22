"""
JARVIS router — constants, lookup tables and pure parse utilities.
"""
import re

# ── Webové stránky ─────────────────────────────────────────────────────────
_SITES = {
    "dashboard": "http://localhost:8002",
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "github":    "https://github.com",
    "facebook":  "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "reddit":    "https://www.reddit.com",
    "twitch":    "https://www.twitch.tv",
    "netflix":   "https://www.netflix.com",
    "gmail":     "https://mail.google.com",
    "twitter":   "https://www.twitter.com",
    "maps":      "https://maps.google.com",
    # ── user-overrides section ─────────────────────────────────────────────
    # This entry can be overridden via config.json `custom_sites` key.
    # Example: {"custom_sites": {"moodle": "https://moodle.your-school.cz"}}
    "moodle":    "https://moodle.sspu-opava.cz",
    # ──────────────────────────────────────────────────────────────────────
    "spotify":   "https://open.spotify.com",
    "discord":   "https://discord.com/app",
    "chatgpt":   "https://chat.openai.com",
    "wikipedia": "https://cs.wikipedia.org",
}

# ── Aplikace ───────────────────────────────────────────────────────────────
_APPS = {
    "chrome": "chrome", "chromium": "chromium", "firefox": "firefox",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vscode": "code", "code": "code", "telegram": "telegram", "vlc": "vlc",
    "kalkulačka": "calc", "calc": "calc", "notepad": "notepad",
    "průzkumník": "nautilus", "soubory": "nautilus", "nautilus": "nautilus",
    "gimp": "gimp", "inkscape": "inkscape", "blender": "blender",
    "terminal": "bash", "bash": "bash",
}

# ── Přeložení názvů procesů ────────────────────────────────────────────────
_PROC_ALIASES = {
    "youtube": "chromium", "chrome": "chrome", "firefox": "firefox",
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "vs code": "code", "vscode": "code", "vlc": "vlc",
    "gimp": "gimp", "telegram": "telegram",
    "kalkulačka": "gnome-calculator",
}

# ── Trigger slova ──────────────────────────────────────────────────────────
_MUSIC_STOP = re.compile(
    r"\b(pust|zahraj|prehraj|play|spust|dej\s+mi|chci\s+slyset"
    r"|spotif[yi]|youtube\s+music|hudbu|muziku|pisni?cku?|song|track|skladbu|zvuk)\b",
    re.IGNORECASE,
)

_CLOSE_TRIGGER = re.compile(
    r"\b(zavri|ukonci|zabij|kill|stop|ukoncit|zabi|vypni\s+(?!pc|pocitac|laptop))\b",
    re.IGNORECASE,
)

_OPEN_TRIGGER = re.compile(
    r"\b(otevri|spust|open|start|nastartuj|otvirej)\b",
    re.IGNORECASE,
)

# ── Fuzzy příkazy ──────────────────────────────────────────────────────────
_FUZZY_COMMANDS = [
    ("otevri chrome",    "open_app",        lambda: {"app": "chrome"}),
    ("otevri firefox",   "open_app",        lambda: {"app": "firefox"}),
    ("otevri spotify",   "open_app",        lambda: {"app": "spotify"}),
    ("otevri discord",   "open_app",        lambda: {"app": "discord"}),
    ("kolik je hodin",   "get_time",        lambda: {}),
    ("jake je datum",    "get_date",        lambda: {}),
    ("screenshot",       "screenshot",      lambda: {}),
    ("info o systemu",   "system_info",     lambda: {}),
    ("prehled o pc",     "pc_overview",     lambda: {}),
    ("stav pocitace",    "pc_overview",     lambda: {}),
    ("top procesy",      "top_processes",   lambda: {"limit": 10, "sort_by": "cpu"}),
    ("nejvice cpu",      "top_processes",   lambda: {"limit": 10, "sort_by": "cpu"}),
    ("nejvice ram",      "top_processes",   lambda: {"limit": 10, "sort_by": "ram"}),
    ("stav site",        "network_status",  lambda: {}),
    ("wifi stav",        "network_status",  lambda: {}),
    ("sitove pripojeni", "network_status",  lambda: {}),
    ("rekni komponenty", "hardware_info",   lambda: {}),
    ("jaky mas hardware","hardware_info",   lambda: {}),
    ("moje pc komponenty","hardware_info",  lambda: {}),
    ("fotbalove vysledky","sports",         lambda: {"query": "fotbal"}),
    ("fotbal vysledky",  "sports",          lambda: {"query": "fotbal"}),
    ("fotbal vysledek",  "sports",          lambda: {"query": "fotbal"}),
    ("vysledky fotbalu", "sports",          lambda: {"query": "fotbal"}),
    ("sportovni vysledky","sports",         lambda: {"query": ""}),
    ("sport vysledky",   "sports",          lambda: {"query": ""}),
    ("vysledky sportu",  "sports",          lambda: {"query": ""}),
    ("kdo hraje dnes",   "sports",          lambda: {"query": "fotbal"}),
    ("hraje dnes",       "sports",          lambda: {"query": "sport"}),
    ("dnes fotbal",      "sports",          lambda: {"query": "fotbal dnes"}),
    ("fotbal dnes",      "sports",          lambda: {"query": "fotbal dnes"}),
    ("jaky fotbal",      "sports",          lambda: {"query": "fotbal"}),
    ("jake zapasy",      "sports",          lambda: {"query": "fotbal"}),
    ("dnesni zapasy",    "sports",          lambda: {"query": "fotbal"}),
    ("sport dnes",       "sports",          lambda: {"query": ""}),
    ("premier league",   "sports",          lambda: {"query": "premier league"}),
    ("champions league", "sports",          lambda: {"query": "champions league"}),
    ("la liga",          "sports",          lambda: {"query": "la liga"}),
    ("bundesliga",       "sports",          lambda: {"query": "bundesliga"}),
    ("nhl",              "sports",          lambda: {"query": "nhl"}),
    ("nba",              "sports",          lambda: {"query": "nba"}),
    ("kolik mam mista",  "disk_space",      lambda: {"path": "/"}),
    ("kolik je mista",   "disk_space",      lambda: {"path": "/"}),
    ("misto na disku",   "disk_space",      lambda: {"path": "/"}),
    ("volne misto",      "disk_space",      lambda: {"path": "/"}),
    ("co mam na plose",  "list_directory",  lambda: {"path": "~/Plocha"}),
    ("co je na plose",   "list_directory",  lambda: {"path": "~/Plocha"}),
    ("co mam v dokumentech", "list_directory", lambda: {"path": "~/Dokumenty"}),
    ("co mam ve stazene","list_directory",  lambda: {"path": "~/Stažené"}),
    ("obsah domovske slozky","list_directory", lambda: {"path": "~"}),
    ("vypni pocitac",    "shutdown",        lambda: {"delay": 0}),
    ("restartuj pocitac","restart",         lambda: {"delay": 0}),
    ("co vidis",         "screen_describe", lambda: {}),
    ("popis obrazovku",  "screen_describe", lambda: {}),
    ("precti obrazovku", "screen_ocr",      lambda: {}),
    ("zapni kameru",     "webcam_describe", lambda: {}),
]

_FUZZY_THRESHOLD = 82  # 0–100, 82 = toleruje 1–2 překlepy

# ── Instalovatelné aplikace ────────────────────────────────────────────────
_INSTALL_APP_NAMES = {
    "instagram", "whatsapp", "telegram", "discord", "spotify", "vlc",
    "chrome", "chromium", "firefox", "vscode", "code", "steam", "gimp",
    "blender", "inkscape", "libreoffice", "zoom", "slack", "teams",
    "signal", "element", "thunderbird", "obs", "audacity", "krita",
    *_APPS.keys(),
}


# ── Pure parse utilities ───────────────────────────────────────────────────

def _parse_timer(a: str) -> dict:
    parts = a.split(None, 1)
    secs  = int(parts[0]) if parts and parts[0].isdigit() else 60
    label = parts[1] if len(parts) > 1 else "Timer"
    return {"seconds": secs, "label": label}


def _parse_move(a: str) -> dict:
    import os
    for sep in (" -> ", " → ", " na ", " do "):
        if sep in a:
            src, dst = a.split(sep, 1)
            return {"src": os.path.expanduser(src.strip()),
                    "dst": os.path.expanduser(dst.strip())}
    return {"src": a, "dst": ""}


def _parse_translate(a: str) -> dict:
    parts = a.split(" to ", 1)
    text = parts[0].strip()
    to_lang = parts[1].strip() if len(parts) > 1 else "cs"
    return {"text": text, "to_lang": to_lang}


def _parse_currency(a: str) -> dict:
    parts = a.upper().split()
    amount = 1.0
    from_curr = "USD"
    to_curr = "CZK"
    try:
        if parts and parts[0].replace(".", "").isdigit():
            amount = float(parts[0])
            parts = parts[1:]
        if parts:
            from_curr = parts[0]
        found = False
        for sep in ("NA", "TO", "IN"):
            if sep in parts:
                idx = parts.index(sep)
                to_curr = parts[idx + 1] if idx + 1 < len(parts) else to_curr
                found = True
                break
        if not found and len(parts) >= 2:
            to_curr = parts[-1]
    except (ValueError, IndexError):
        pass
    return {"amount": amount, "from_curr": from_curr, "to_curr": to_curr}


def _parse_reminder(a: str) -> dict:
    parts = a.split(" za ", 1)
    text = parts[0].strip()
    time_str = parts[1].strip() if len(parts) > 1 else "1 minuta"
    return {"text": text, "time_str": time_str}


def _parse_memory_store(a: str) -> dict:
    parts = a.split(" s důležitostí ", 1)
    content = parts[0].strip()
    importance = float(parts[1].strip()) if len(parts) > 1 else 0.5
    return {"content": content, "importance": importance}
