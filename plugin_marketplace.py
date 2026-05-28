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


class PluginMarketplace:
    # Registr vestavěných pluginů dodávaných s JARVIS.
    # Tyto pluginy jsou součástí repozitáře v plugins/builtin/ —
    # "instalace" jen zkopíruje složku do plugins/custom/.
    REGISTRY = {
        "hello-world": {
            "repo":        "simivilasek-ship-it/jarvis-plugin-hello",
            "description": "Ukázkový plugin — základ pro vlastní vývoj",
            "author":      "JARVIS team",
            "builtin":     False,
        },
        "calculator": {
            "repo":        None,
            "description": "Rozšířená kalkulačka s historií výpočtů",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/calculator",
        },
        "timer": {
            "repo":        None,
            "description": "Časovač s hlasovým upozorněním",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/timer",
        },
        "clipboard": {
            "repo":        None,
            "description": "Správa schránky — kopírování, vkládání, historie",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/clipboard",
        },
        "greeting": {
            "repo":        None,
            "description": "Pozdravy a základní konverzace",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/greeting",
        },
        "mcp-filesystem": {
            "repo":        None,
            "description": "MCP Filesystem — čtení souborů a adresářů",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/mcp_filesystem",
        },
        "mcp-brave": {
            "repo":        None,
            "description": "MCP Brave Search — webové vyhledávání (vyžaduje BRAVE_API_KEY)",
            "author":      "JARVIS team",
            "builtin":     True,
            "builtin_path": "plugins/builtin/mcp_brave",
        },
    }

    def __init__(self, plugins_dir: str = None):
        from pathlib import Path
        self.plugins_dir = Path(plugins_dir or "plugins/custom")

    def list_available(self) -> str:
        """Vrátí seznam pluginů z REGISTRY."""
        if not self.REGISTRY:
            return "Marketplace je prázdný. Přidej pluginy do REGISTRY."
        lines = ["Dostupné pluginy:"]
        for name, info in self.REGISTRY.items():
            installed = (self.plugins_dir / name).exists()
            status = "✓ nainstalován" if installed else "○ dostupný"
            lines.append(f"  {status}  {name} — {info['description']} (by {info['author']})")
        return "\n".join(lines)

    def install(self, name: str) -> str:
        """Stáhne plugin z GitHub jako ZIP a rozbalí do plugins/custom/."""
        import zipfile, io, requests
        info = self.REGISTRY.get(name.lower())
        if not info:
            return f"Plugin '{name}' není v marketplace. Zkus 'marketplace seznam'."
        dest = self.plugins_dir / name
        if dest.exists():
            return f"Plugin '{name}' je již nainstalován. Použij 'aktualizuj plugin {name}'."
        repo = info["repo"]
        url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                # Extrahuj do tmp, přesuň do plugins_dir/name
                repo_name = repo.split("/")[1]
                prefix = f"{repo_name}-main/"
                dest.mkdir(parents=True, exist_ok=True)
                for member in z.namelist():
                    if member.startswith(prefix) and not member.endswith("/"):
                        data = z.read(member)
                        rel = member[len(prefix):]
                        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                        (dest / rel).write_bytes(data)
            return f"Plugin '{name}' nainstalován do {dest}. Restartuj JARVIS pro aktivaci."
        except Exception as e:
            if dest.exists():
                import shutil; shutil.rmtree(dest, ignore_errors=True)
            return f"Chyba instalace '{name}': {e}"

    def uninstall(self, name: str) -> str:
        import shutil
        dest = self.plugins_dir / name
        if not dest.exists():
            return f"Plugin '{name}' není nainstalován."
        shutil.rmtree(dest)
        return f"Plugin '{name}' odinstalován."

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
