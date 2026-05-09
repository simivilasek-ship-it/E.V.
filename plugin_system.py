"""
JARVIS v3.0 — Plugin System
Extensible plugin architecture for JARVIS commands and features.
"""

import os
import sys
import json
import importlib
import inspect
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata o pluginu"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_api_version: str = "3.0.0"


@dataclass
class PluginManifest:
    """Manifest pluginu načtený z manifest.json"""
    name: str
    version: str
    description: str
    author: str = ""
    entry_point: str = "main"
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class PluginBase:
    """
    Základní třída pro všechny pluginy.
    Každý plugin musí dědit z této třídy a implementovat požadované metody.
    """

    def __init__(self, metadata: PluginMetadata, config: Dict[str, Any] = None):
        self.metadata = metadata
        self.config = config or {}
        self._enabled = True
        self._logger = logging.getLogger(f"plugin.{metadata.name}")

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        """Povolí plugin"""
        self._enabled = True
        self._logger.info(f"Plugin '{self.name}' povolen")

    def disable(self):
        """Zakáže plugin"""
        self._enabled = False
        self._logger.info(f"Plugin '{self.name}' zakázán")

    def on_load(self):
        """Volá se při načtení pluginu"""
        pass

    def on_unload(self):
        """Volá se při odpojení pluginu"""
        pass

    def on_config_change(self, key: str, value: Any):
        """Volá se při změně konfigurace"""
        pass

    def get_commands(self) -> Dict[str, Callable]:
        """
        Vrátí slovník příkazů poskytovaných pluginem.
        Klíč = název příkazu, hodnota = callable.
        """
        return {}

    def get_actions(self) -> Dict[str, Callable]:
        """
        Vrátí slovník akcí poskytovaných pluginem.
        Klíč = název akce, hodnota = callable(params) -> str.
        """
        return {}

    def get_routes(self) -> List[Dict[str, Any]]:
        """
        Vrátí seznam routovacích pravidel.
        Každé pravidlo: {"pattern": regex, "action": str, "handler": callable(text) -> tuple}
        """
        return []

    def get_ui_elements(self) -> List[Dict[str, Any]]:
        """
        Vrátí seznam UI elementů pro GUI.
        """
        return []


class PluginManager:
    """
    Správce pluginů — načítá, spravuje a poskytuje pluginy.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.plugins: Dict[str, PluginBase] = {}
        self._commands: Dict[str, Callable] = {}
        self._actions: Dict[str, Callable] = {}
        self._routes: List[Dict[str, Any]] = []
        self._ui_elements: List[Dict[str, Any]] = []
        self._plugin_dirs: List[str] = []
        self._disabled_plugins: set = set()

        # Výchozí adresáře pro pluginy
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._plugin_dirs = [
            os.path.join(base_dir, "plugins"),
            os.path.join(base_dir, "plugins", "builtin"),
        ]

        # Načti seznam zakázaných pluginů z konfigurace
        self._disabled_plugins = set(
            self.config.get("disabled_plugins", [])
        )

    def discover_plugins(self) -> List[PluginManifest]:
        """
        Prohledá adresáře pluginů a vrátí seznam manifestů.
        """
        manifests = []

        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue

            for item in os.listdir(plugin_dir):
                plugin_path = os.path.join(plugin_dir, item)

                # Podpora pro jednotlivé soubory i adresáře
                manifest_path = None
                if os.path.isdir(plugin_path):
                    manifest_path = os.path.join(plugin_path, "manifest.json")
                elif item.endswith(".py") and item != "__init__.py":
                    # Python soubor bez manifestu
                    manifest_path = plugin_path

                if manifest_path and os.path.isfile(manifest_path):
                    try:
                        manifest = self._load_manifest(manifest_path, plugin_path)
                        if manifest:
                            manifests.append(manifest)
                    except Exception as e:
                        logger.warning(f"Chyba načítání manifestu {manifest_path}: {e}")

        return manifests

    def _load_manifest(self, manifest_path: str, plugin_path: str) -> Optional[PluginManifest]:
        """Načte manifest pluginu"""
        if manifest_path.endswith(".json"):
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PluginManifest(
                name=data.get("name", os.path.basename(plugin_path)),
                version=data.get("version", "0.1.0"),
                description=data.get("description", ""),
                author=data.get("author", ""),
                entry_point=data.get("entry_point", "main"),
                dependencies=data.get("dependencies", []),
                permissions=data.get("permissions", []),
                config_schema=data.get("config_schema", {}),
            )
        elif manifest_path.endswith(".py"):
            # Python soubor bez manifestu — vytvoř základní manifest
            name = os.path.splitext(os.path.basename(manifest_path))[0]
            return PluginManifest(
                name=name,
                version="0.1.0",
                description=f"Plugin: {name}",
                entry_point=name,
            )
        return None

    def load_plugin(self, manifest: PluginManifest) -> Optional[PluginBase]:
        """
        Načte plugin podle manifestu.
        """
        if manifest.name in self.plugins:
            logger.warning(f"Plugin '{manifest.name}' je již načten")
            return self.plugins[manifest.name]

        if manifest.name in self._disabled_plugins:
            logger.info(f"Plugin '{manifest.name}' je zakázán, přeskočen")
            return None

        try:
            # Najdi cestu k pluginu
            plugin_path = self._find_plugin_path(manifest.name)
            if not plugin_path:
                logger.error(f"Plugin '{manifest.name}' nenalezen")
                return None

            # Přidej cestu do sys.path
            plugin_dir = os.path.dirname(plugin_path) if os.path.isfile(plugin_path) else plugin_path
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)

            # Importuj modul
            module_name = os.path.splitext(os.path.basename(plugin_path))[0] if os.path.isfile(plugin_path) else manifest.entry_point
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.error(f"Import pluginu '{manifest.name}' selhal: {e}")
                return None

            # Najdi třídu pluginu
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginBase) and
                    obj is not PluginBase):
                    plugin_class = obj
                    break

            if not plugin_class:
                logger.error(f"Plugin '{manifest.name}' neobsahuje třídu dědící z PluginBase")
                return None

            # Vytvoř instanci
            metadata = PluginMetadata(
                name=manifest.name,
                version=manifest.version,
                description=manifest.description,
                author=manifest.author,
                dependencies=manifest.dependencies,
            )

            plugin_config = self.config.get("plugins", {}).get(manifest.name, {})
            plugin = plugin_class(metadata=metadata, config=plugin_config)

            # Zaregistruj
            self.plugins[manifest.name] = plugin
            plugin.on_load()

            # Registruj příkazy a akce
            self._register_plugin_commands(plugin)
            self._register_plugin_actions(plugin)
            self._register_plugin_routes(plugin)
            self._register_plugin_ui(plugin)

            logger.info(f"Plugin '{manifest.name}' v{manifest.version} načten")
            return plugin

        except Exception as e:
            logger.error(f"Chyba načítání pluginu '{manifest.name}': {e}", exc_info=True)
            return None

    def _find_plugin_path(self, name: str) -> Optional[str]:
        """Najde cestu k souboru/adresáři pluginu"""
        for plugin_dir in self._plugin_dirs:
            # Jako adresář
            dir_path = os.path.join(plugin_dir, name)
            if os.path.isdir(dir_path):
                main_file = os.path.join(dir_path, "__init__.py")
                if os.path.isfile(main_file):
                    return main_file
                # Hledej hlavní soubor
                for f in os.listdir(dir_path):
                    if f.endswith(".py") and f != "__init__.py":
                        return os.path.join(dir_path, f)

            # Jako soubor
            file_path = os.path.join(plugin_dir, f"{name}.py")
            if os.path.isfile(file_path):
                return file_path

        return None

    def _register_plugin_commands(self, plugin: PluginBase):
        """Zaregistruje příkazy pluginu"""
        for cmd_name, cmd_func in plugin.get_commands().items():
            full_name = f"{plugin.name}.{cmd_name}"
            self._commands[full_name] = cmd_func
            logger.debug(f"Příkaz registrován: {full_name}")

    def _register_plugin_actions(self, plugin: PluginBase):
        """Zaregistruje akce pluginu"""
        for action_name, action_func in plugin.get_actions().items():
            full_name = f"{plugin.name}.{action_name}"
            self._actions[full_name] = action_func
            logger.debug(f"Akce registrována: {full_name}")

    def _register_plugin_routes(self, plugin: PluginBase):
        """Zaregistruje routovací pravidla pluginu"""
        for route in plugin.get_routes():
            route["plugin"] = plugin.name
            self._routes.append(route)
            logger.debug(f"Route registrována: {route.get('pattern')}")

    def _register_plugin_ui(self, plugin: PluginBase):
        """Zaregistruje UI elementy pluginu"""
        for element in plugin.get_ui_elements():
            element["plugin"] = plugin.name
            self._ui_elements.append(element)

    def unload_plugin(self, name: str) -> bool:
        """Odpojí plugin"""
        if name not in self.plugins:
            logger.warning(f"Plugin '{name}' není načten")
            return False

        plugin = self.plugins[name]
        plugin.on_unload()

        # Odstraň příkazy
        self._commands = {k: v for k, v in self._commands.items() if not k.startswith(f"{name}.")}
        self._actions = {k: v for k, v in self._actions.items() if not k.startswith(f"{name}.")}
        self._routes = [r for r in self._routes if r.get("plugin") != name]
        self._ui_elements = [e for e in self._ui_elements if e.get("plugin") != name]

        del self.plugins[name]
        logger.info(f"Plugin '{name}' odpojen")
        return True

    def reload_plugin(self, name: str) -> Optional[PluginBase]:
        """Znovu načte plugin"""
        self.unload_plugin(name)

        # Najdi manifest
        manifests = self.discover_plugins()
        for manifest in manifests:
            if manifest.name == name:
                return self.load_plugin(manifest)

        logger.error(f"Plugin '{name}' nelze znovu načíst — manifest nenalezen")
        return None

    def load_all_plugins(self) -> List[PluginBase]:
        """Načte všechny dostupné pluginy"""
        loaded = []
        manifests = self.discover_plugins()

        for manifest in manifests:
            plugin = self.load_plugin(manifest)
            if plugin:
                loaded.append(plugin)

        logger.info(f"Načteno {len(loaded)}/{len(manifests)} pluginů")
        return loaded

    def get_command(self, name: str) -> Optional[Callable]:
        """Získá příkaz podle názvu"""
        return self._commands.get(name)

    def get_action(self, name: str) -> Optional[Callable]:
        """Získá akci podle názvu"""
        return self._actions.get(name)

    def get_all_commands(self) -> Dict[str, Callable]:
        """Vrátí všechny registrované příkazy"""
        return dict(self._commands)

    def get_all_actions(self) -> Dict[str, Callable]:
        """Vrátí všechny registrované akce"""
        return dict(self._actions)

    def get_routes(self) -> List[Dict[str, Any]]:
        """Vrátí všechna routovací pravidla"""
        return list(self._routes)

    def get_ui_elements(self) -> List[Dict[str, Any]]:
        """Vrátí všechny UI elementy"""
        return list(self._ui_elements)

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Vrátí informace o pluginu"""
        if name not in self.plugins:
            return None

        plugin = self.plugins[name]
        return {
            "name": plugin.name,
            "metadata": {
                "version": plugin.metadata.version,
                "description": plugin.metadata.description,
                "author": plugin.metadata.author,
            },
            "enabled": plugin.enabled,
            "commands": list(plugin.get_commands().keys()),
            "actions": list(plugin.get_actions().keys()),
            "routes": len(plugin.get_routes()),
        }

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Vypíše všechny načtené pluginy"""
        return [
            self.get_plugin_info(name)
            for name in sorted(self.plugins.keys())
            if self.get_plugin_info(name)
        ]

    def disable_plugin(self, name: str) -> bool:
        """Zakáže plugin"""
        if name in self.plugins:
            self.plugins[name].disable()
            self._disabled_plugins.add(name)
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        """Povolí plugin"""
        if name in self.plugins:
            self.plugins[name].enable()
            self._disabled_plugins.discard(name)
            return True
        return False


# ══════════════════════════════════════════════════════
#  BUILT-IN PLUGIN: System
# ══════════════════════════════════════════════════════

class SystemPlugin(PluginBase):
    """Základní systémový plugin — poskytuje jádrové funkce"""

    def __init__(self, metadata: PluginMetadata, config: Dict[str, Any] = None):
        super().__init__(metadata, config)
        self._notes_file = os.path.join(
            os.path.expanduser("~"), "jarvis_notes.txt"
        )

    def get_commands(self) -> Dict[str, Callable]:
        return {
            "system_info": self._cmd_system_info,
            "get_time": self._cmd_get_time,
            "get_date": self._cmd_get_date,
        }

    def get_actions(self) -> Dict[str, Callable]:
        return {
            "note_add": self._action_note_add,
            "note_list": self._action_note_list,
        }

    def _cmd_system_info(self) -> str:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return (
            f"CPU: {cpu:.0f}% | "
            f"RAM: {ram.percent:.0f}% ({ram.used // 1024 // 1024}/{ram.total // 1024 // 1024} MB) | "
            f"Disk: {disk.percent:.0f}%"
        )

    def _cmd_get_time(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _cmd_get_date(self) -> str:
        return datetime.now().strftime("%d. %m. %Y")

    def _action_note_add(self, note: str) -> str:
        with open(self._notes_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}\n")
        return "Poznámka uložena."

    def _action_note_list(self) -> str:
        if os.path.exists(self._notes_file):
            with open(self._notes_file, "r", encoding="utf-8") as f:
                return f.read().strip() or "Žádné poznámky."
        return "Žádné poznámky."


# ══════════════════════════════════════════════════════
#  BUILT-IN PLUGIN: Web Search
# ══════════════════════════════════════════════════════

class WebSearchPlugin(PluginBase):
    """Plugin pro webové vyhledávání"""

    def get_routes(self) -> List[Dict[str, Any]]:
        import re
        return [
            {
                "pattern": re.compile(r"\b(hledej|vyhledej|search)\b", re.IGNORECASE),
                "action": "search_web",
                "handler": self._route_search,
            },
            {
                "pattern": re.compile(r"\b(wiki|wikipedia)\b", re.IGNORECASE),
                "action": "wiki_search",
                "handler": self._route_wiki,
            },
        ]

    def _route_search(self, text: str) -> tuple:
        import re
        query = re.sub(r"\b(hledej|vyhledej|search)\b\s*", "", text, flags=re.IGNORECASE).strip()
        if query:
            return f"Hledám: {query}.", {"action": "search_web", "params": {"query": query}}
        return None, None

    def _route_wiki(self, text: str) -> tuple:
        import re
        query = re.sub(r"\b(wiki|wikipedia|co\s+je)\b\s*", "", text, flags=re.IGNORECASE).strip()
        if query:
            return f"Hledám na Wikipedii: {query}", {"action": "wiki_search", "params": {"query": query}}
        return None, None


# ══════════════════════════════════════════════════════
#  FACTORY
# ══════════════════════════════════════════════════════

def create_plugin_manager(config: Dict[str, Any] = None) -> PluginManager:
    """Vytvoří a inicializuje PluginManager s built-in pluginy"""
    manager = PluginManager(config)

    # Zaregistruj built-in pluginy
    builtin_plugins = [
        SystemPlugin(
            PluginMetadata(
                name="system",
                version="3.0.0",
                description="Základní systémové funkce",
                author="JARVIS Team",
            )
        ),
        WebSearchPlugin(
            PluginMetadata(
                name="web_search",
                version="1.0.0",
                description="Webové vyhledávání",
                author="JARVIS Team",
            )
        ),
    ]

    for plugin in builtin_plugins:
        manager.plugins[plugin.name] = plugin
        plugin.on_load()
        manager._register_plugin_commands(plugin)
        manager._register_plugin_actions(plugin)
        manager._register_plugin_routes(plugin)
        manager._register_plugin_ui(plugin)
        logger.info(f"Built-in plugin '{plugin.name}' v{plugin.metadata.version} načten")

    return manager