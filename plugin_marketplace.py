"""
JARVIS Plugin Marketplace
Stahování, seznam a správa pluginů z GitHub.

Příkazy (přes LocalRouter):
  „marketplace seznam"           → seznam dostupných pluginů
  „nainstaluj plugin X"          → stáhne plugin z GitHubu
  „odinstaluj plugin X"          → smaže plugin složku
  „aktualizuj plugin X"          → přestáhne (git pull nebo re-download)
"""

from __future__ import annotations
from pathlib import Path


class PluginMarketplace:
    # Registr vestavěných pluginů dodávaných s JARVIS.
    # Tyto pluginy jsou součástí repozitáře v plugins/builtin/ —
    # "instalace" jen zkopíruje složku do plugins/custom/.
    REGISTRY = {
        "hello-world": {
            "repo":        "simivilasek-ship-it/jarvis-plugin-hello",
            "description": "Ukázkový plugin — základ pro vlastní vývoj",
            "author":      "JARVIS team",
            "version":     "1.0.0",
            "rating":      4.5,
            "downloads":   142,
            "tags":        ["demo", "template"],
            "builtin":     False,
        },
        "calculator": {
            "repo":        None,
            "description": "Rozšířená kalkulačka s historií výpočtů",
            "author":      "JARVIS team",
            "version":     "2.1.0",
            "rating":      4.8,
            "downloads":   1024,
            "tags":        ["math", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/calculator",
        },
        "timer": {
            "repo":        None,
            "description": "Časovač s hlasovým upozorněním",
            "author":      "JARVIS team",
            "version":     "1.3.0",
            "rating":      4.7,
            "downloads":   856,
            "tags":        ["productivity", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/timer",
        },
        "clipboard": {
            "repo":        None,
            "description": "Správa schránky — kopírování, vkládání, historie",
            "author":      "JARVIS team",
            "version":     "1.1.0",
            "rating":      4.6,
            "downloads":   634,
            "tags":        ["system", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/clipboard",
        },
        "greeting": {
            "repo":        None,
            "description": "Pozdravy a základní konverzace",
            "author":      "JARVIS team",
            "version":     "1.0.0",
            "rating":      4.3,
            "downloads":   412,
            "tags":        ["conversation", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/greeting",
        },
        "mcp-filesystem": {
            "repo":        None,
            "description": "MCP Filesystem — čtení souborů a adresářů",
            "author":      "JARVIS team",
            "version":     "1.2.0",
            "rating":      4.9,
            "downloads":   789,
            "tags":        ["files", "mcp", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/mcp_filesystem",
        },
        "mcp-brave": {
            "repo":        None,
            "description": "MCP Brave Search — webové vyhledávání (vyžaduje BRAVE_API_KEY)",
            "author":      "JARVIS team",
            "version":     "1.1.0",
            "rating":      4.7,
            "downloads":   523,
            "tags":        ["search", "mcp", "builtin"],
            "builtin":     True,
            "builtin_path": "plugins/builtin/mcp_brave",
        },
    }

    def __init__(self, plugins_dir: str = None):
        from pathlib import Path
        self.plugins_dir = Path(plugins_dir or "plugins/custom")
        # ratings stored per marketplace in plugins_dir/.ratings.json
        self._ratings_file = self.plugins_dir.parent / "marketplace_ratings.json"
        try:
            self._ratings = json.loads(self._ratings_file.read_text(encoding='utf-8')) if self._ratings_file.exists() else {}
        except Exception:
            self._ratings = {}

    def list_available(self) -> str:
        """Vrátí seznam pluginů z REGISTRY s ratingem a verzí."""
        if not self.REGISTRY:
            return "Marketplace je prázdný. Přidej pluginy do REGISTRY."
        lines = ["Dostupné pluginy:\n"]
        updates = self.check_updates()
        for name, info in self.REGISTRY.items():
            installed = (self.plugins_dir / name).exists()
            status = "✓" if installed else "○"
            rating = info.get("rating", 0)
            stars  = "★" * int(rating) + ("½" if rating % 1 >= 0.5 else "")
            ver    = info.get("version", "?")
            dl     = info.get("downloads", 0)
            upd    = " ⬆ aktualizace" if name in updates else ""
            lines.append(
                f"  {status} {name} v{ver}{upd}\n"
                f"     {stars} {rating} · {dl} stažení\n"
                f"     {info['description']} (by {info['author']})"
            )
        return "\n".join(lines)

    def check_updates(self) -> dict:
        """Porovná verze nainstalovaných pluginů s REGISTRY.
        Vrátí {name: new_version} pro pluginy kde je novější verze."""
        import json as _json
        updates = {}
        for name, info in self.REGISTRY.items():
            manifest = self.plugins_dir / name / "manifest.json"
            if not manifest.exists():
                continue
            try:
                local_ver  = _json.loads(manifest.read_text()).get("version", "0.0.0")
                remote_ver = info.get("version", "0.0.0")
                if self._version_gt(remote_ver, local_ver):
                    updates[name] = remote_ver
            except Exception:
                pass
        return updates

    def auto_update_all(self) -> str:
        """Aktualizuje všechny pluginy kde je dostupná novější verze."""
        updates = self.check_updates()
        if not updates:
            return "Vše je aktuální. Žádné aktualizace nejsou k dispozici."
        results = []
        for name, version in updates.items():
            result = self.update(name)
            results.append(f"  {name} → v{version}: {result}")
        return "Aktualizováno:\n" + "\n".join(results)

    @staticmethod
    def _version_gt(a: str, b: str) -> bool:
        """Vrátí True pokud verze a > b (srovnání tuple)."""
        def parse(v):
            try: return tuple(int(x) for x in v.split("."))
            except Exception: return (0,)
        return parse(a) > parse(b)

    def install(self, name: str) -> str:
        """Stáhne plugin z GitHub jako ZIP, nebo zkopíruje vestavěný plugin.
        If MCP auto-install is enabled in config and plugin has tag 'mcp', delegate to mcp_installer.
        """
        import zipfile, io, requests, shutil
        from config import CONFIG
        info = self.REGISTRY.get(name.lower())
        if not info:
            available = ", ".join(self.REGISTRY.keys())
            return f"Plugin '{name}' není v marketplace. Dostupné: {available}"
        dest = self.plugins_dir / name
        if dest.exists():
            return f"Plugin '{name}' je již nainstalován. Použij 'aktualizuj plugin {name}'."

        # Vestavěné pluginy — kopíruj z builtin adresáře
        if info.get("builtin"):
            src = Path(info["builtin_path"])
            if src.exists():
                shutil.copytree(src, dest)
                return f"Plugin '{name}' nainstalován (builtin). Restartuj JARVIS pro aktivaci."
            return f"Vestavěný plugin '{name}' nebyl nalezen v {src}."

        # If this is an MCP plugin and auto-install is enabled, use mcp_installer
        tags = info.get("tags", [])
        if "mcp" in tags and CONFIG.get("mcp_auto_install_enabled", False):
            try:
                from mcp_installer import install_from_zip_bytes
                repo = info["repo"]
                if not repo:
                    return f"Plugin '{name}' nemá repo pro MCP instalaci."
                url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
                r = requests.get(url, timeout=20)
                r.raise_for_status()
                plan = install_from_zip_bytes(name, r.content)
                if plan.get("ok"):
                    return f"MCP server '{name}' nainstalován do {plan.get('path')}. Restartuj JARVIS pro aktivaci."
                return f"MCP instalace selhala: {plan.get('error')}"
            except Exception as e:
                return f"MCP instalace se nepovedla: {e}"

        repo = info["repo"]
        if not repo:
            return f"Plugin '{name}' nemá URL repozitáře."
        url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 404:
                return f"Repozitář '{repo}' nenalezen na GitHubu (404). Zkontroluj název."
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                repo_name = repo.split("/")[1]
                prefix = f"{repo_name}-main/"
                dest.mkdir(parents=True, exist_ok=True)
                for member in z.namelist():
                    if member.startswith(prefix) and not member.endswith("/"):
                        data = z.read(member)
                        rel = member[len(prefix):]
                        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                        (dest / rel).write_bytes(data)
            # try to save screenshots from manifest if present
            try:
                manifest = dest / 'manifest.json'
                if manifest.exists():
                    import json as _json
                    m = _json.loads(manifest.read_text(encoding='utf-8'))
                    ss = m.get('screenshots') or m.get('screenshot')
                    if ss:
                        # store first screenshot url/text into registry
                        info['screenshot'] = ss if isinstance(ss, str) else (ss[0] if isinstance(ss, list) else None)
            except Exception:
                pass

            return f"Plugin '{name}' nainstalován. Restartuj JARVIS pro aktivaci."
        except Exception as e:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return f"Chyba instalace '{name}': {e}"

    def uninstall(self, name: str) -> str:
        import shutil
        dest = self.plugins_dir / name
        if not dest.exists():
            return f"Plugin '{name}' není nainstalován."
        shutil.rmtree(dest)
        return f"Plugin '{name}' odinstalován."

    def rate_plugin(self, name: str, rating: float) -> str:
        """Rate a plugin (1.0 - 5.0). Stores rating in marketplace_ratings.json."""
        try:
            r = float(rating)
            if r < 1.0 or r > 5.0:
                return "Rating musí být mezi 1.0 a 5.0"
        except Exception:
            return "Neplatný rating"
        self._ratings[name] = self._ratings.get(name, []) + [r]
        try:
            self._ratings_file.parent.mkdir(parents=True, exist_ok=True)
            self._ratings_file.write_text(json.dumps(self._ratings, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        return f"Díky za hodnocení: {name} → {r}"

    def update(self, name: str) -> str:
        self.uninstall(name)
        return self.install(name)

    def install_from_github(self, repo: str) -> str:
        """Přímá instalace z GitHub repo (user/repo nebo URL)."""
        import zipfile, io, requests, re
        # Normalizuj URL → user/repo
        repo = re.sub(r"https?://github\.com/", "", repo).strip("/")
        name = repo.split("/")[-1].lower().replace("-", "_")
        dest = self.plugins_dir / name
        if dest.exists():
            return f"Plugin '{name}' je již nainstalován."
        url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            repo_short = repo.split("/")[1]
            prefix = f"{repo_short}-main/"
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for member in z.namelist():
                    if member.startswith(prefix) and not member.endswith("/"):
                        data = z.read(member)
                        rel = member[len(prefix):]
                        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                        (dest / rel).write_bytes(data)
            return f"Plugin '{name}' nainstalován z {repo}."
        except Exception as e:
            if dest.exists():
                import shutil; shutil.rmtree(dest, ignore_errors=True)
            return f"Chyba: {e}"
