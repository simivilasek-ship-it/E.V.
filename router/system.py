"""
JARVIS router — system and file routing.
Handles system info, shutdown/restart, disk, network, weather, timers, file
operations, search, MCP tools, and misc utilities.
"""
import os
import re
from datetime import datetime

from .apps import _is_video_download_intent
from .constants import _parse_currency

_HOME = os.path.expanduser("~")


def route_system(text: str, t: str, dt: datetime | None = None) -> tuple:
    """
    Handles system-level commands: time/date, hardware, disk, network,
    power management, volume, media controls, sport, weather, timer,
    web search, MCP tools, and miscellaneous utilities.
    """
    if dt is None:
        dt = datetime.now()

    # Time
    if re.search(r"\b(kolik je|jaky je|cas|hodin|time)\b", t) and \
       not re.search(r"\b(pracovni|volny|cas na)\b", t):
        return f"Je {dt.strftime('%H:%M:%S')}.", {"action": "get_time", "params": {}}

    # Date
    if re.search(r"\b(datum|dnes|jaky den|ktery den|date)\b", t):
        return f"Dnes je {dt.strftime('%-d. %-m. %Y')}.", {"action": "get_date", "params": {}}

    # Screenshot
    if re.search(r"\b(screenshot|sniiek\s+obrazovky|printscreen|screenshoot|snimek)\b", t):
        return "Pořizuji screenshot.", {"action": "screenshot", "params": {}}

    # Undo
    if re.search(r"\b(vrat|undo|zpet\s+akci|zrus\s+posledni|obnov\s+posledni)\b", t):
        return "Vracím poslední akci.", {"action": "undo", "params": {}}
    if re.search(r"\b(undo\s+history|historie\s+akci|co\s+mohu\s+vratit)\b", t):
        return "Historie vrátitelných akcí:", {"action": "undo_history", "params": {}}

    # Hardware info
    if re.search(
        r"\b(hardware|komponenty|komponenta|procesoru?|grafick|grafika|gpu|cpu\s+model"
        r"|zakladni\s+deska|ram\s+typ|jaka\s+mas|jaky\s+mas|moje\s+pc|muj\s+pocitac"
        r"|rekni.*komponenty|zjisti.*hardware|co\s+mas\s+za\s+pc|spec(ifikace)?)\b", t,
    ):
        return "Zjišťuji hardwarové komponenty...", {"action": "hardware_info", "params": {}}

    # Disk space
    m = re.search(
        r"\b(kolik\s+(mam|je)\s+(misto|volno|volne|gb|space)|misto\s+na\s+disku"
        r"|volne\s+misto|disk\s+space|free\s+space|jak\s+plny|obsazeni\s+disku"
        r"|kapacita\s+disku)\b", t,
    )
    if m:
        path_m = re.search(r"(/\S+|~/\S*)", text)
        path = path_m.group(1) if path_m else "/"
        return "Zjišťuji místo na disku...", {"action": "disk_space", "params": {"path": path}}

    # Top processes
    if re.search(
        r"\b(top\s+proces|nejvice\s+(cpu|ram|pameti)|co\s+zere\s+(cpu|ram|pamet)"
        r"|procesy\s+podle\s+(cpu|ram)|spotreba\s+proces)\b", t, re.I,
    ):
        sort_by = "ram" if re.search(r"\b(ram|pamet|paměti|memory)\b", t, re.I) else "cpu"
        return "Top procesy:", {"action": "top_processes", "params": {"limit": 10, "sort_by": sort_by}}

    # Network / WiFi
    if re.search(
        r"\b(stav\s+(site|siti|wifi|wi-?fi|sitoveho\s+pripojeni)"
        r"|sitove\s+pripojeni|wifi\s+stav|jsem\s+online|mam\s+internet)\b", t, re.I,
    ):
        return "Stav sítě:", {"action": "network_status", "params": {}}

    # PC overview
    if re.search(
        r"\b(prehled\s+(o\s+)?(pc|pocitaci|systemu|počítači)"
        r"|stav\s+(pc|pocitace|počítače|systemu)"
        r"|jak\s+je\s+na\s+tom\s+(pc|pocitac|počítač)"
        r"|co\s+(bezi|běží)\s+na\s+(pc|pocitaci|počítači)"
        r"|co\s+se\s+deje\s+na\s+(pc|pocitaci)"
        r"|spravuj\s+pc|pc\s+overview|system\s+overview)\b", t, re.I,
    ):
        return "Přehled o počítači:", {"action": "pc_overview", "params": {}}

    # System info
    if re.search(r"\b(využití\s+(cpu|ram|disk)|system\s+info|stav\s+systému|kolik\s+ram)\b", t):
        return None, {"action": "system_info", "params": {}}

    # Shutdown
    if re.search(r"\b(vypni\s+(pc|pocitac|laptop|komputer)|shutdown)\b", t):
        return "Vypínám počítač.", {"action": "shutdown", "params": {"delay": 0}}

    # Restart
    if re.search(r"\b(restartuj|restart\s+(pc|pocitac))\b", t):
        return "Restartuji počítač.", {"action": "restart", "params": {"delay": 0}}

    # Sleep
    if re.search(r"\b(uspi\s+(pc|pocitac)|sleep\s+pc|spanek\s+pc)\b", t):
        return "Uspávám počítač.", {"action": "sleep_pc", "params": {}}

    # System update
    if re.search(r"\b(aktualizuj\s+system|apt\s+upgrade|update\s+system)\b", t):
        return "Spouštím aktualizaci.", {"action": "update_system", "params": {}}

    # Volume
    vol = re.search(r"\b(hlasitost|volume|zvuk)\s*(na|:)?\s*(\d+)", t)
    if vol:
        lvl = min(100, max(0, int(vol.group(3))))
        return f"Hlasitost: {lvl}%.", {"action": "volume", "params": {"level": lvl}}
    if re.search(r"\b(ztlum|mute|umlc)\b", t):
        return "Ztlumeno.", {"action": "volume", "params": {"action": "mute"}}
    if re.search(r"\b(odtlum|unmute|zesil\s+zvuk)\b", t):
        return "Odtlumeno.", {"action": "volume", "params": {"action": "unmute"}}
    vol2 = re.search(r"\b(zvys|sniz|zesil|ztlum)\s+zvuk\s+na\s*(\d+)", t)
    if vol2:
        lvl = min(100, max(0, int(vol2.group(2))))
        return f"Hlasitost: {lvl}%.", {"action": "volume", "params": {"level": lvl}}

    # Brightness
    jas = re.search(r"\b(jas|brightness)\s*(na|:)?\s*(\d+)", t)
    if jas:
        lvl = min(100, max(1, int(jas.group(3))))
        return f"Jas: {lvl}%.", {"action": "set_brightness", "params": {"level": lvl}}

    # Media controls
    if re.search(r"\b(pozastav|pauza|pause)\b", t):
        return "Pozastavuji.", {"action": "media", "params": {"action": "play_pause"}}
    if re.search(r"\b(preskocit|dalsi\s+skladb|next\s+track)\b", t):
        return "Další skladba.", {"action": "media", "params": {"action": "next"}}
    if re.search(r"\b(predchozi\s+skladb|zpet\s+skladb)\b", t):
        return "Předchozí.", {"action": "media", "params": {"action": "prev"}}

    # YT-DLP: download video/audio
    if _is_video_download_intent(t, text):
        audio = bool(re.search(r"\b(audio|mp3|hudbu|zvuk|skladbu|pisnicku)\b", t))
        quality = (
            "720p" if "720" in t else
            "1080p" if "1080" in t else
            "480p" if "480" in t else "best"
        )
        query = re.sub(
            r"\b(stahni|download|stahnout|uloz|video|audio|mp3|hudbu|zvuk|z\s+youtube|youtube)\b",
            "", text, flags=re.IGNORECASE,
        ).strip(" ,.-")
        if query:
            mode = "audio MP3" if audio else f"video {quality}"
            return f"Stahuji {mode}: {query}", {
                "action": "youtube_download",
                "params": {"query": query, "audio_only": audio, "quality": quality}}

    # YT-DLP: video info
    if re.search(r"\b(info\s+o\s+videu|informace\s+o\s+videu|jak\s+dlouhe|delka\s+videa)\b", t):
        query = re.sub(
            r"\b(info|informace|o\s+videu|jak\s+dlouhe|delka)\b", "", text,
            flags=re.IGNORECASE,
        ).strip(" ,.-")
        if query:
            return f"Zjišťuji info: {query}", {
                "action": "youtube_info", "params": {"query": query}}

    # Sport
    if re.search(
        r"\b(sport|fotbal|hokej|nhl|nba|nfl|mlb|basket"
        r"|premier\s*league|champions\s*league|liga\s*mistr"
        r"|la\s*liga|serie\s*a|bundesliga|ligue\s*1|fortuna\s*liga"
        r"|zapas|zapasy|vysledky|skore|live\s*score"
        r"|hraje\s+dnes|kdo\s+hraje|co\s+se\s+hraje|novinky\s+sport)\b", t,
    ) and not re.search(r"^\s*dnes\s*$", t):
        query = re.sub(
            r"\b(rekni|rici|zjisti|ukazmi|jak\s+to\s+dopadlo|co\s+je|jake\s+jsou)\b",
            "", text, flags=re.IGNORECASE,
        ).strip()
        return "Načítám sportovní výsledky...", {"action": "sports", "params": {"query": query}}

    # Weather
    if re.search(r"\b(pocasi|počasí|weather|bude\s+prset|teplota\s+v|jake\s+je\s+pocasi)\b", t):
        city = ""
        m = re.search(r"\b(?:v|ve)\s+([a-záčďéěíňóřšťúůýž]+)", t)
        if m:
            city = m.group(1)
        if not city:
            m = re.search(r"\b(?:pocasi|počasí|weather)\b\s+(?:v\s+)?([a-záčďéěíňóřšťúůýž]+)", t)
            if m:
                city = m.group(1)
        if not city:
            m = re.search(r"\b([a-záčďéěíňóřšťúůýž]+)\s+(?:pocasi|počasí|weather)\b", t)
            if m:
                city = m.group(1)
        if city.lower() in ("pocasi", "počasí", "weather", "dnes", "zitra", "bude", "jake", "je"):
            city = ""
        elif city:
            _cities = {
                "praha": "Praha", "praze": "Praha", "brno": "Brno", "ostrava": "Ostrava",
                "plzen": "Plzeň", "plzni": "Plzeň", "liberec": "Liberec", "olomouc": "Olomouc",
            }
            city = _cities.get(city.lower(), city[0].upper() + city[1:])
        return f"Počasí{' — ' + city if city else ''}:", {
            "action": "weather", "params": {"city": city}}

    # Timer
    if re.search(r"\b(timer|casovac|pripominka|upozorni\s+za|za\s+\d+\s+minut)\b", t):
        m = re.search(r"(\d+)\s*(minut|sekund|hodin)", t)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            secs = n * (3600 if unit.startswith("hodin") else
                        60   if unit.startswith("minut") else 1)
            return f"Timer {n} {unit}.", {
                "action": "set_timer", "params": {"seconds": secs, "label": "Timer"}}

    # Sport & news — DDG realtime search
    sport_m = re.search(
        r"\b(vs\.?|versus|proti|zapas|zápas|vysledek|výsledek|skore|skóre"
        r"|goal|gol|liga|champions|premier|bundesliga|serie\s*a|laliga"
        r"|nba|nhl|nfl|mlb|f1|formula|mma|ufc|wta|atp|tenis|golf"
        r"|ko\s+\d|\d+:\d+|final[ae]?|semifinal[ae]?"
        r"|paris|arsenal|chelsea|manchester|real\s+madrid|barcelona"
        r"|liverpool|inter|juventus|milan|dortmund)\b", t, re.IGNORECASE,
    )
    if sport_m:
        try:
            from plugins.custom.mcp_fetch.skill import _ddg_search
            result = _ddg_search(text, max_chars=1200)
            if result and len(result) > 50:
                return result, {"action": "answer", "params": {}}
        except Exception:
            pass
        return f"Hledám na googlu: {text}.", {
            "action": "search_web", "params": {"query": text}}

    # News & crypto — DDG realtime search
    news_m = re.search(
        r"\b(novinky|aktualni|trending|co\s+se\s+deje"
        r"|kurz\s+(eura|dolaru|btc|koruny)|cena\s+(akcie|bitcoinu|bitcoin|zlata|ropy|btc)"
        r"|kdo\s+vyhral|kdo\s+postoupil|vysledky\s+dnes|zapasy\s+dnes|dnesni\s+zapasy"
        r"|tabulka\s+(ligy|standings)|kam\s+postoupil|kdo\s+sestoupil"
        r"|bitcoin|ethereum|krypto)\b", t, re.IGNORECASE,
    )
    if news_m:
        try:
            from plugins.custom.mcp_fetch.skill import _ddg_search
            result = _ddg_search(text, max_chars=1200)
            if result and len(result) > 50:
                return result, {"action": "answer", "params": {}}
        except Exception:
            pass
        return f"Hledám: {text}.", {
            "action": "search_web", "params": {"query": text}}

    # Web search
    if re.search(r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b", t):
        query = re.sub(
            r"\b(hledej|vyhledej|najdi\s+na\s+googlu|search)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if query:
            return f"Hledám: {query}.", {"action": "search_web", "params": {"query": query}}

    # Calculator
    if re.search(r"\b(vypočítej|spočítej|kolik\s+je|calculate)\b", t):
        expr = re.sub(
            r"\b(vypočítej|spočítej|kolik\s+je|calculate)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if expr:
            return f"Vypočítávám: {expr}", {"action": "calculate", "params": {"expression": expr}}

    # Translate
    if re.search(r"\b(přelož|překlad|translate)\b", t):
        txt = re.sub(r"\b(přelož|překlad|translate)\b\s*", "", text,
                     flags=re.IGNORECASE).strip()
        if txt:
            return f"Překládám: {txt}", {"action": "translate", "params": {"text": txt}}

    # Notes
    if re.search(r"\b(přidej\s+poznámku|ulož\s+poznámku|note\s+add)\b", t):
        note = re.sub(
            r"\b(přidej\s+poznámku|ulož\s+poznámku|note\s+add)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if note:
            return "Přidávám poznámku.", {"action": "note_add", "params": {"note": note}}
    if re.search(r"\b(zobraz\s+poznámky|ukáž\s+poznámky|note\s+list)\b", t):
        return "Poznámky:", {"action": "note_list", "params": {}}

    # Reminder
    if re.search(r"\b(připomeň|reminder|upozorni)\b", t):
        reminder = re.sub(
            r"\b(připomeň|reminder|upozorni)\b\s*", "", text, flags=re.IGNORECASE,
        ).strip()
        if reminder:
            return "Nastavuji připomínku.", {
                "action": "reminder_set", "params": {"text": reminder, "time_str": "1 minuta"}}

    # YouTube transcripts (MCP)
    if re.search(r"\b(titulky|subtitles?|transcript|prepis\s+videa|titulky\s+z)\b", t):
        query = re.sub(
            r"\b(titulky|subtitles?|transcript|prepis\s+videa|titulky\s+z)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if query:
            return f"Načítám titulky: {query}", {
                "action": "mcp_tool",
                "params": {
                    "server": "youtube-transcript", "tool": "get_transcript",
                    "arguments": {"url": query},
                }}

    # GitHub (MCP)
    if re.search(r"\b(github|issue|pull\s*request|pr\b|commit|repo\b)\b", t) and \
       re.search(r"\b(vytvor|otevri|zobraz|najdi|seznam|search|create|list|get)\b", t):
        query = re.sub(
            r"\b(github|issue|pull\s*request|pr|commit|repo)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        return f"GitHub: {text}", {
            "action": "mcp_tool",
            "params": {"server": "github", "tool": "search_issues",
                       "arguments": {"query": query or text}}}

    # Google Maps (MCP)
    if re.search(r"\b(naviguj|trasa|vzdalenost|jak\s+se\s+dostat|kde\s+je|mapa|maps)\b", t):
        query = re.sub(
            r"\b(naviguj|trasa|vzdalenost|jak\s+se\s+dostat|kde\s+je|mapa|maps)\b\s*", "", text,
            flags=re.IGNORECASE,
        ).strip()
        if query:
            return f"Google Maps: {query}", {
                "action": "mcp_tool",
                "params": {"server": "google-maps", "tool": "geocode",
                           "arguments": {"address": query}}}

    # Wikipedia
    if re.search(r"\b(wiki|wikipedia|co\s+je)\b", t):
        query = re.sub(r"\b(wiki|wikipedia|co\s+je)\b\s*", "", text,
                       flags=re.IGNORECASE).strip()
        if query:
            return f"Hledám na Wikipedii: {query}", {
                "action": "wiki_search", "params": {"query": query}}

    # Currency conversion
    if re.search(
        r"\b(prevod|prevest|zmen|konvertuj|convert)\b.{0,20}\b(meny|mena|currency|usd|eur|czk|gbp)\b",
        t,
    ) or re.search(r"\b\d+\s*(usd|eur|czk|gbp|jpy|pln|chf)\b.{0,20}\b(na|to|in)\b", t):
        curr = re.sub(
            r"\b(prevod|prevest|zmen|konvertuj|convert)\s*(meny|mena|currency)?\s*", "", t,
            flags=re.IGNORECASE,
        ).strip()
        if curr:
            return f"Převádím měnu: {curr}", {
                "action": "currency_convert", "params": _parse_currency(curr)}

    # Parallel agents
    if re.search(
        r"\b(paraleln[eě]|soubehn[eě]|vsechny\s+agenty|spust\s+agenty"
        r"|multi.?agent|vice\s+agentu?|parallel\s+agent)\b", t,
    ):
        task = re.sub(
            r"\b(paraleln[eě]|soubehn[eě]|vsechny\s+agenty|spust\s+agenty"
            r"|multi.?agent|vice\s+agentu?|parallel\s+agent)\b\s*",
            "", text, flags=re.IGNORECASE,
        ).strip()
        if task:
            return f"Spouštím paralelní agenty: {task}", {
                "action": "agent_parallel_task", "params": {"task": task}}

    # Computer Use (Accessibility / UI automation)
    if re.search(r"\b(ui\s+strom|ui\s+tree|accessibility\s+tree|strom\s+elementu)\b", t):
        return "Získávám strom UI elementů…", {"action": "ui_tree", "params": {"max_nodes": 400}}
    m = re.search(r"\b(ui\s+klikni|ui\s+click|klikni\s+na\s+ui)\b\s+(.+)", t)
    if m:
        label = m.group(2).strip()
        return f"Klikám na UI element: {label}", {
            "action": "ui_click", "params": {"text": label, "role": ""}}

    # Shadow Mode
    if re.search(
        r"\b(shadow\s+mode|shadow\s+navrh|shadow\s+suggest"
        r"|navrhni\s+refaktor|navrhni\s+zlepseni)\b", t,
    ):
        return "Generuji návrhy (Shadow Mode)…", {"action": "shadow_suggest", "params": {}}

    # MCP hub
    m = re.search(r"\b(mcp\s+suggest|doporu[cč]\s+mcp|mcp\s+server)\b\s*(.*)", t)
    if m:
        task = (m.group(2) or "").strip() or text
        return "Doporučuji MCP server…", {"action": "mcp_suggest", "params": {"task": task}}

    return None, None


def route_files(text: str, t: str) -> tuple:
    """
    Handles file/directory operations: listing, create, delete, move/rename,
    find, clipboard, and text typing.
    """
    # List directory
    m = re.search(
        r"\b(co\s+(mam|je)\s+v\s+|obsah\s+(slozky|adresare|zlozky)|vypis\s+slozky"
        r"|seznam\s+souboru|ls\s+|dir\s+|browse\s+|procházej?\s+|what.s\s+in)\b", t,
    )
    if m:
        path_m = re.search(
            r"(/\S+|~/\S*|(?:plocha|dokumenty|stazene|desktop|downloads)\b)", text, re.I,
        )
        if path_m:
            raw = path_m.group(1)
            folder_map = {
                "plocha": "~/Plocha", "desktop": "~/Desktop",
                "dokumenty": "~/Dokumenty", "documents": "~/Documents",
                "stazene": "~/Stažené", "downloads": "~/Downloads",
            }
            path = folder_map.get(raw.lower(), raw)
        else:
            path = "~"
        return f"Prohlížím složku {path}...", {"action": "list_directory", "params": {"path": path}}

    # Direct folder shortcuts
    for keyword, path in [
        ("obsah plochy", "~/Plocha"), ("co mam na plose", "~/Plocha"),
        ("co mam na ploche", "~/Plocha"), ("obsah dokumentu", "~/Dokumenty"),
        ("obsah stazene", "~/Stažené"), ("domovsky adresar", "~"),
        ("home folder", "~"), ("what.*desktop", "~/Desktop"),
    ]:
        if keyword in t or re.search(keyword, t):
            return f"Prohlížím složku {path}...", {
                "action": "list_directory", "params": {"path": path}}

    # File info
    m = re.search(
        r"\b(info\s+o\s+souboru|detail.*soubor|jak\s+velky|velikost\s+souboru"
        r"|file\s+info|stat\s+souboru)\b", t,
    )
    if m:
        path_m = re.search(r"(/\S+|~/\S+)", text)
        path = path_m.group(1) if path_m else ""
        return "Zjišťuji info o souboru...", {"action": "file_info", "params": {"path": path}}

    # Create folder
    m = re.search(r"\b(vytvor|vytvorit|mkdir)\s+slozku\s+(.+)", t)
    if m:
        name = m.group(2).strip()
        path = os.path.join(_HOME, name)
        return f"Vytvářím složku {name}.", {
            "action": "create_folder", "params": {"path": path}}

    # Create file
    m = re.search(r"\b(vytvor|vytvorit|touch|new)\s+soubor\s+(\S+)", t)
    if m:
        name = m.group(2).strip()
        path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
        return f"Vytvářím soubor {name}.", {
            "action": "create_file", "params": {"path": os.path.expanduser(path)}}

    # Delete file
    m = re.search(r"\b(smaz|smazat|odstra(n|ň)|delete|rm)\s+soubor\s+(\S+)", t)
    if not m:
        m = re.search(r"\b(smaz|smazat|odstra(n|ň)|delete)\s+(\S+\.\w+)\b", t)
    if m:
        name = m.group(m.lastindex).strip()
        path = name if name.startswith("/") or name.startswith("~") else os.path.join(_HOME, name)
        return f"Mažu soubor {name}.", {
            "action": "delete_file", "params": {"path": os.path.expanduser(path)}}

    # Move / rename file
    m = re.search(
        r"\b(presun|přesuň|presuv|přejmenuj|mv|rename)\s+(.+?)\s+(do|na|->|→|to)\s+(.+)", t,
    )
    if m:
        src = m.group(2).strip()
        dst = m.group(4).strip()
        src_p = src if src.startswith("/") or src.startswith("~") else os.path.join(_HOME, src)
        dst_p = dst if dst.startswith("/") or dst.startswith("~") else os.path.join(_HOME, dst)
        return f"Přesouvám {src} → {dst}.", {
            "action": "move_file",
            "params": {
                "src": os.path.expanduser(src_p),
                "dst": os.path.expanduser(dst_p),
            }}

    # Find file
    m = re.search(r"\b(najdi|hledej)\s+soubor\s+(.+)", t)
    if m:
        name = m.group(2).strip()
        return f"Hledám soubor: {name}.", {
            "action": "find_files", "params": {"name": name, "path": _HOME}}

    # Clipboard
    m = re.search(r"\b(zkopíruj|kopíruj|dej\s+do\s+schránky)\s+(.+)", text, re.IGNORECASE)
    if m:
        txt = m.group(2).strip()
        return f"Zkopírováno: {txt}", {"action": "clipboard_set", "params": {"text": txt}}

    # Type text
    m = re.search(r"\b(napiš|napsat|typ(uj)?)\s+(.+)", text, re.IGNORECASE)
    if m:
        txt = m.group(3).strip()
        return f"Píšu: {txt}", {"action": "write_text", "params": {"text": txt}}

    return None, None
