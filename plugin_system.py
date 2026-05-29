"""
JARVIS v4.2 — Plugin / Skill System
Podporuje dva formáty:
  1. Složka se skill.py + manifest.json  (Leon-style)
  2. Jednoduchý .py soubor s get_routes() / get_actions()

Skills se načítají lazy — pouze pokud manifest existuje nebo .py soubor nalezen.
"""

from __future__ import annotations
import ast
import sys
import json
import importlib
import importlib.util
import inspect
import logging
import concurrent.futures
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

_PLUGIN_ROUTE_TIMEOUT = 3.0   # max sekundy na jedno routování
_PLUGIN_ACTION_TIMEOUT = 10.0  # max sekundy na jedno vykonání akce

logger = logging.getLogger(__name__)

# Moduly povolené v pluginech bez explicitního svolení v manifestu.
# Pokrývá stdlib utility a běžné datové knihovny — vynechává os.system,
# subprocess, socket, ctypes a další nebezpečné moduly záměrně.
_SAFE_IMPORTS: Set[str] = {
    # stdlib — bezpečné
    "abc", "base64", "bisect", "calendar", "cmath", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal",
    "difflib", "enum", "fractions", "functools", "hashlib", "heapq",
    "html", "html.parser", "http.client", "http.cookiejar",
    "inspect", "io", "itertools", "json", "logging", "math",
    "operator", "pathlib", "pprint", "queue", "random", "re",
    "shlex", "signal", "statistics", "string", "struct", "textwrap",
    "threading", "time", "traceback", "typing", "unicodedata",
    "unittest", "unittest.mock", "urllib", "urllib.parse",
    "urllib.request", "uuid", "warnings", "weakref", "xml",
    "xml.etree", "xml.etree.ElementTree", "zipfile",
    # třetí strany — běžně používané v JARVIS pluginech
    "requests", "bs4", "beautifulsoup4", "pydantic", "yaml",
    "numpy", "pandas", "PIL", "pillow",
    # vlastní moduly projektu
    "jarvis_skill_",
}

# Moduly které manifest může explicitně povolit přes "permissions".
# Klíč = název permission, hodnota = množina kořenových modulů.
MANIFEST_SCHEMA = {
    "required": ["name", "version", "description", "permissions"],
    "types": {
        "name":        str,
        "version":     str,
        "description": str,
        "author":      str,
        "permissions": list,
        "triggers":    list,
    },
    "valid_permissions": {"answer", "system", "media", "files", "mcp", "internal", "safe_eval"},
}


class ManifestValidator:
    @staticmethod
    def validate(manifest: dict) -> tuple:
        """Vrátí (True, '') nebo (False, 'chybová zpráva')."""
        for field in MANIFEST_SCHEMA["required"]:
            if field not in manifest:
                return False, f"Chybí povinné pole: {field}"
        for field, expected_type in MANIFEST_SCHEMA["types"].items():
            if field in manifest and not isinstance(manifest[field], expected_type):
                return False, f"Pole '{field}' musí být {expected_type.__name__}"
        for perm in manifest.get("permissions", []):
            if perm not in MANIFEST_SCHEMA["valid_permissions"]:
                return False, f"Neplatné oprávnění: '{perm}'"
        return True, ""


_PERMISSION_MODULES: Dict[str, Set[str]] = {
    # Základní permissions definované v MANIFEST_SCHEMA
    "answer":     set(),  # jen stdlib — žádné extra moduly
    "system":     {"os", "os.path", "subprocess", "shutil", "glob",
                   "tempfile", "psutil", "platform", "pyautogui", "pyperclip"},
    "media":      {"os", "os.path", "subprocess", "webbrowser", "yt_dlp",
                   "pyautogui", "pyperclip"},
    "files":      {"os", "os.path", "shutil", "glob", "tempfile",
                   "fnmatch", "pathlib", "mcp_bridge"},
    "mcp":        {"mcp_bridge", "mcp", "os", "os.path", "config",
                   "memory", "from __future__"},
    # Rozšířené permissions pro interní použití
    "os":         {"os", "os.path"},
    "subprocess": {"subprocess"},
    "socket":     {"socket", "ssl", "asyncio"},
    "filesystem": {"shutil", "glob", "tempfile", "fnmatch"},
    "database":   {"sqlite3", "sqlalchemy"},
    "crypto":     {"cryptography", "hmac", "secrets"},
    # Speciální: povolí import interních JARVIS modulů
    "internal":   {"mcp_bridge", "config", "memory", "llm", "commands",
                   "plugin_marketplace", "vision", "stt", "tts"},
}


# ── Datové struktury ──────────────────────────────────

@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_api_version: str = "3.0.0"


@dataclass
class SkillManifest:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    entry_point: str = "skill"          # soubor bez .py
    permissions: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    path: str = ""                       # absolutní cesta ke složce / souboru


# ── PluginBase (třídní API — zpětná kompatibilita) ────

class PluginBase:
    """Základní třída pro class-based pluginy."""

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

    def enable(self):  self._enabled = True
    def disable(self): self._enabled = False

    def on_load(self): pass
    def on_unload(self): pass

    def get_commands(self) -> Dict[str, Callable]: return {}
    def get_actions(self)  -> Dict[str, Callable]: return {}
    def get_routes(self)   -> List[Dict[str, Any]]: return []
    def get_ui_elements(self) -> List[Dict[str, Any]]: return []


# ── Wrapper pro module-level skills ───────────────────

class ModuleSkillWrapper(PluginBase):
    """Obalí modul s get_routes()/get_actions() do PluginBase rozhraní."""

    def __init__(self, module, manifest: SkillManifest):
        meta = PluginMetadata(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
        )
        super().__init__(meta)
        self._module = module
        self._manifest = manifest

    def get_routes(self) -> List[Dict[str, Any]]:
        fn = getattr(self._module, "get_routes", None)
        return fn() if callable(fn) else []

    def get_actions(self) -> Dict[str, Callable]:
        fn = getattr(self._module, "get_actions", None)
        return fn() if callable(fn) else {}

    def get_commands(self) -> Dict[str, Callable]:
        fn = getattr(self._module, "get_commands", None)
        return fn() if callable(fn) else {}


# ── Skill Loader ──────────────────────────────────────

def _collect_imports(source: str) -> Set[str]:
    """Vrátí množinu kořenových názvů modulů použitých v zdrojovém kódu."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    roots: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


# eval je zakázáno jen jako nekontrolovaný builtin.
# Pokud plugin explicitně deklaruje permission "safe_eval", povolí se.
_DANGEROUS_BUILTINS = {"exec", "__import__", "breakpoint"}
_CONDITIONAL_BUILTINS = {"eval", "compile"}  # povoleno s "safe_eval" permission


def _check_dangerous_calls(source: str, allow_eval: bool = False) -> Optional[str]:
    """Detekuje přímá volání exec/eval/compile jako BUILTINY (ne jako metody).
    re.compile() nebo pattern.compile() jsou povoleny — pouze compile() bez prefixu je zakázáno.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
                # exec/__import__/breakpoint — vždy zakázáno
                if name in _DANGEROUS_BUILTINS:
                    found.append(name)
                # eval/compile — zakázáno pokud plugin nemá safe_eval permission
                elif name in _CONDITIONAL_BUILTINS and not allow_eval:
                    found.append(name)
            # Attribute volání (re.compile, obj.eval…) jsou POVOLENA
    if found:
        return f"Zakázaná volání: {', '.join(sorted(set(found)))}"
    return None


def _check_imports(source: str, permissions: List[str], plugin_name: str) -> Optional[str]:
    """Zkontroluje importy a nebezpečná volání pluginu. Vrátí chybový řetězec nebo None."""
    # 1. Kontrola nebezpečných builtinů (exec/eval bez importu)
    allow_eval = "safe_eval" in permissions
    danger = _check_dangerous_calls(source, allow_eval=allow_eval)
    if danger:
        return danger

    # 2. Kontrola importů
    allowed = set(_SAFE_IMPORTS)
    for perm in permissions:
        extra = _PERMISSION_MODULES.get(perm)
        if extra:
            allowed.update(extra)
        else:
            logger.warning(f"Plugin '{plugin_name}': neznámá permission '{perm}'")

    used = _collect_imports(source)
    # Povolíme inter-plugin importy a __future__ (standardní Python)
    blocked = {m for m in used
               if m not in allowed
               and not m.startswith("jarvis_skill_")
               and m != "__future__"}
    if blocked:
        return f"Zakázané importy: {', '.join(sorted(blocked))}"
    return None


class SkillLoader:
    """Statická třída pro načítání skill modulů."""

    _PLUGIN_ROOT: Path = Path(__file__).parent / "plugins"

    @staticmethod
    def load_module(path: str, module_name: str, permissions: List[str] = None):
        """Načte Python modul ze souboru po kontrole importů.

        Canonizuje cestu a zabrání path traversal útokům.
        """
        plugin_path = Path(path).resolve()
        plugin_root = SkillLoader._PLUGIN_ROOT.resolve()
        try:
            plugin_path.relative_to(plugin_root)
        except ValueError:
            raise ImportError(
                f"Sandbox odmítl plugin '{module_name}': cesta mimo plugins/ adresář: {plugin_path}"
            )
        source = plugin_path.read_text(encoding="utf-8")
        err = _check_imports(source, permissions or [], module_name)
        if err:
            raise ImportError(f"Sandbox odmítl plugin '{module_name}': {err}")

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            raise ImportError(f"Nelze načíst spec pro {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def find_plugin_class(module) -> Optional[type]:
        """Najde třídu dědící z PluginBase v modulu."""
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, PluginBase) and obj is not PluginBase:
                return obj
        return None

    @staticmethod
    def has_module_api(module) -> bool:
        """Vrátí True pokud modul má get_routes nebo get_actions."""
        return callable(getattr(module, "get_routes", None)) or \
               callable(getattr(module, "get_actions", None))


# ── Plugin Manager ────────────────────────────────────

class PluginManager:
    """
    Správce skills/pluginů.
    Skenuje plugins/ adresáře, načítá manifest.json i standalone .py soubory.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.plugins: Dict[str, PluginBase] = {}
        self._commands: Dict[str, Callable] = {}
        self._actions: Dict[str, Callable] = {}
        self._routes: List[Dict[str, Any]] = []
        self._disabled: set = set(self.config.get("disabled_plugins", []))

        base = Path(__file__).parent
        self._skill_dirs: List[Path] = [
            base / "plugins" / "custom",
            base / "plugins" / "builtin",
            base / "plugins" / "system",
            base / "plugins" / "web",
            base / "plugins" / "media",
        ]

    # ── Discovery ─────────────────────────────────────

    def discover_skills(self) -> List[SkillManifest]:
        """Prohledá skill adresáře a vrátí seznam manifestů."""
        manifests: List[SkillManifest] = []
        seen = set()

        for skill_dir in self._skill_dirs:
            if not skill_dir.is_dir():
                continue

            for item in sorted(skill_dir.iterdir()):
                # Složka se skill.py nebo manifest.json
                if item.is_dir():
                    manifest_file = item / "manifest.json"
                    skill_file = item / "skill.py"
                    init_file = item / "__init__.py"

                    if manifest_file.exists():
                        m = self._parse_manifest(manifest_file, item)
                    elif skill_file.exists() or init_file.exists():
                        m = SkillManifest(
                            name=item.name,
                            description=f"Skill: {item.name}",
                            path=str(item),
                        )
                    else:
                        continue

                    if m and m.name not in seen:
                        seen.add(m.name)
                        manifests.append(m)

                # Standalone .py soubor
                elif item.suffix == ".py" and item.name != "__init__.py":
                    name = item.stem
                    if name not in seen:
                        seen.add(name)
                        manifests.append(SkillManifest(
                            name=name,
                            description=f"Skill: {name}",
                            entry_point=name,
                            path=str(item),
                        ))

        return manifests

    def _parse_manifest(self, manifest_file: Path, skill_dir: Path) -> Optional[SkillManifest]:
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            valid, err = ManifestValidator.validate(data)
            if not valid:
                logger.warning(f"Skill '{skill_dir}' má neplatný manifest: {err} — přeskočen")
                return None
            return SkillManifest(
                name=data.get("name", skill_dir.name),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                author=data.get("author", ""),
                entry_point=data.get("entry_point", "skill"),
                permissions=data.get("permissions", []),
                triggers=data.get("triggers", []),
                dependencies=data.get("dependencies", []),
                path=str(skill_dir),
            )
        except Exception as e:
            logger.warning(f"Chyba manifestu {manifest_file}: {e}")
            return None

    # ── Loading ───────────────────────────────────────

    def load_skill(self, manifest: SkillManifest) -> Optional[PluginBase]:
        """Načte skill — podporuje složku+skill.py i standalone .py."""
        if manifest.name in self.plugins:
            return self.plugins[manifest.name]
        if manifest.name in self._disabled:
            logger.debug(f"Skill '{manifest.name}' je zakázán")
            return None

        try:
            skill_path = Path(manifest.path)

            # Najdi Python soubor
            if skill_path.is_dir():
                py_file = skill_path / f"{manifest.entry_point}.py"
                if not py_file.exists():
                    py_file = skill_path / "__init__.py"
                if not py_file.exists():
                    # Vezmi první .py soubor
                    py_files = list(skill_path.glob("*.py"))
                    if not py_files:
                        logger.error(f"Skill '{manifest.name}': žádný .py soubor v {skill_path}")
                        return None
                    py_file = py_files[0]
            else:
                py_file = skill_path  # standalone soubor

            module_name = f"jarvis_skill_{manifest.name}"
            module = SkillLoader.load_module(str(py_file), module_name, manifest.permissions)

            # Preferuj PluginBase třídu, fallback na module-level API
            plugin_class = SkillLoader.find_plugin_class(module)
            if plugin_class:
                meta = PluginMetadata(
                    name=manifest.name, version=manifest.version,
                    description=manifest.description, author=manifest.author,
                )
                cfg = self.config.get("plugins", {}).get(manifest.name, {})
                plugin = plugin_class(metadata=meta, config=cfg)
            elif SkillLoader.has_module_api(module):
                plugin = ModuleSkillWrapper(module, manifest)
            else:
                logger.warning(f"Skill '{manifest.name}': žádné get_routes() ani PluginBase třída")
                return None

            self.plugins[manifest.name] = plugin
            plugin.on_load()
            self._register(plugin)
            logger.info(f"Skill '{manifest.name}' v{manifest.version} načten ✓")
            return plugin

        except Exception as e:
            logger.error(f"Chyba načítání skill '{manifest.name}': {e}", exc_info=True)
            return None

    def load_all_plugins(self) -> List[PluginBase]:
        """Načte všechny dostupné skills."""
        loaded = []
        for manifest in self.discover_skills():
            plugin = self.load_skill(manifest)
            if plugin:
                loaded.append(plugin)
        logger.info(f"Skills načteny: {len(loaded)}")
        return loaded

    # Alias pro zpětnou kompatibilitu
    def load_plugin(self, manifest) -> Optional[PluginBase]:
        if isinstance(manifest, SkillManifest):
            return self.load_skill(manifest)
        # Starý PluginManifest formát
        sm = SkillManifest(
            name=getattr(manifest, "name", "unknown"),
            version=getattr(manifest, "version", "1.0.0"),
            description=getattr(manifest, "description", ""),
            author=getattr(manifest, "author", ""),
            path="",
        )
        return self.load_skill(sm)

    # ── Registration ──────────────────────────────────

    def _register(self, plugin: PluginBase):
        for name, fn in plugin.get_commands().items():
            self._commands[f"{plugin.name}.{name}"] = fn
        for name, fn in plugin.get_actions().items():
            self._actions[name] = fn           # bez prefixu pro přímé volání
        for route in plugin.get_routes():
            route["plugin"] = plugin.name
            self._routes.append(route)

    # ── Unload / Reload ───────────────────────────────

    def unload_plugin(self, name: str) -> bool:
        if name not in self.plugins:
            return False
        self.plugins[name].on_unload()
        self._routes  = [r for r in self._routes if r.get("plugin") != name]
        self._actions = {k: v for k, v in self._actions.items()
                         if not k.startswith(f"{name}.")}
        del self.plugins[name]
        logger.info(f"Skill '{name}' odpojen")
        return True

    def reload_plugin(self, name: str) -> Optional[PluginBase]:
        self.unload_plugin(name)
        for m in self.discover_skills():
            if m.name == name:
                return self.load_skill(m)
        return None

    # ── Getters ───────────────────────────────────────

    # ── Timeout-safe volání ───────────────────────────

    @staticmethod
    def _call_with_timeout(fn: Callable, args: tuple, kwargs: dict,
                           timeout: float, plugin_name: str = "?"):
        """Spustí callable s časovým limitem. Vrátí (result, error_str).

        Executor se uzavírá s wait=False aby hlavní vlákno neblokoval,
        pokud plugin přesáhl timeout a stále běží v pozadí.
        """
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            fut = ex.submit(fn, *args, **kwargs)
            try:
                return fut.result(timeout=timeout), None
            except concurrent.futures.TimeoutError:
                msg = f"Plugin '{plugin_name}' timeout ({timeout}s)"
                logger.warning(msg)
                fut.cancel()
                return None, msg
            except Exception as e:
                logger.error(f"Plugin '{plugin_name}' výjimka: {e}")
                return None, str(e)
        finally:
            ex.shutdown(wait=False)

    def call_route(self, handler: Callable, text: str,
                   plugin_name: str = "?") -> Optional[Tuple]:
        """Zavolá handler s timeoutem. Při chybě vrátí (None, None)."""
        timeout = self.config.get("plugin_handler_timeout", 5.0)
        # cancel_futures=True zajistí že shutdown nečeká na running thread
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(handler, text)
        try:
            result = future.result(timeout=timeout)
            return result
        except concurrent.futures.TimeoutError:
            logger.warning(f"Plugin '{plugin_name}' handler timeout ({timeout}s)")
            future.cancel()
            return None, None
        except Exception as e:
            logger.error(f"Plugin '{plugin_name}' handler chyba: {e}")
            return None, None
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def call_action(self, action_fn: Callable, plugin_name: str = "?",
                    **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """Zavolá plugin action s timeoutem. Vrátí (result, error)."""
        return self._call_with_timeout(
            action_fn, (), kwargs, _PLUGIN_ACTION_TIMEOUT, plugin_name)

    def get_routes(self) -> List[Dict[str, Any]]:
        return list(self._routes)

    def get_action(self, name: str) -> Optional[Callable]:
        return self._actions.get(name)

    def get_all_actions(self) -> Dict[str, Callable]:
        return dict(self._actions)

    def get_all_commands(self) -> Dict[str, Callable]:
        return dict(self._commands)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.name,
                "version": p.metadata.version,
                "description": p.metadata.description,
                "routes": len(p.get_routes()),
                "enabled": p.enabled,
            }
            for p in self.plugins.values()
        ]

    def health_check(self) -> List[Dict]:
        """Zkontroluje zdraví všech načtených pluginů."""
        results = []
        for plugin in self.plugins.values():
            info = {
                "name":    plugin.name,
                "status":  "ok",
                "routes":  0,
                "actions": 0,
                "error":   None,
            }
            try:
                routes  = plugin.get_routes()
                actions = plugin.get_actions()
                info["routes"]  = len(routes) if routes else 0
                info["actions"] = len(actions) if actions else 0
                for r in (routes or []):
                    if not callable(r.get("handler")):
                        raise ValueError(f"handler není callable: {r.get('handler')}")
            except Exception as e:
                info["status"] = "error"
                info["error"]  = str(e)[:100]
            results.append(info)
        return results

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        p = self.plugins.get(name)
        if not p:
            return None
        return {
            "name": p.name,
            "metadata": {
                "version": p.metadata.version,
                "description": p.metadata.description,
                "author": p.metadata.author,
            },
            "enabled": p.enabled,
            "routes": len(p.get_routes()),
        }

    def disable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].disable()
            self._disabled.add(name)
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].enable()
            self._disabled.discard(name)
            return True
        return False


# ── Built-in skills (class-based) ─────────────────────

class SystemPlugin(PluginBase):
    def __init__(self, metadata: PluginMetadata, config: Dict[str, Any] = None):
        super().__init__(metadata, config)

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
        return (f"CPU: {cpu:.0f}% | RAM: {ram.percent:.0f}% | "
                f"Disk: {disk.percent:.0f}%")

    def _cmd_get_time(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _cmd_get_date(self) -> str:
        return datetime.now().strftime("%d. %m. %Y")

    def _action_note_add(self, note: str) -> str:
        path = Path.home() / "jarvis_notes.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}\n")
        return "Poznámka uložena."

    def _action_note_list(self) -> str:
        path = Path.home() / "jarvis_notes.txt"
        if path.exists():
            return path.read_text(encoding="utf-8").strip() or "Žádné poznámky."
        return "Žádné poznámky."


# ── Factory ───────────────────────────────────────────

def create_plugin_manager(config: Dict[str, Any] = None) -> PluginManager:
    """Vytvoří PluginManager s built-in pluginy + načte custom skills."""
    manager = PluginManager(config)

    # Vestavěný systémový plugin
    sys_plugin = SystemPlugin(PluginMetadata(
        name="system", version="3.1.0",
        description="Základní systémové funkce", author="JARVIS",
    ))
    manager.plugins["system"] = sys_plugin
    sys_plugin.on_load()
    manager._register(sys_plugin)
    logger.info("Built-in skill 'system' načten")

    # Načti custom skills ze složek
    manager.load_all_plugins()

    return manager
