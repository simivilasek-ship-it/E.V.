"""
E.V. router package — domain routing modules.

NOTE: LocalRouter is defined in local_router.py (root level) for backward
compatibility. Do NOT import local_router here — it imports from this package
and would create a circular dependency.

Import LocalRouter directly:  from local_router import LocalRouter
"""
from .apps import route_apps, route_sites, _extract_app_name, _extract_install_name  # noqa: F401
from .media import route_music, route_vision  # noqa: F401
from .system import route_system, route_files  # noqa: F401
from .memory_routes import route_memory  # noqa: F401
from .constants import (  # noqa: F401
    _SITES, _APPS, _PROC_ALIASES,
    _MUSIC_STOP, _CLOSE_TRIGGER, _OPEN_TRIGGER,
    _FUZZY_COMMANDS, _FUZZY_THRESHOLD, _INSTALL_APP_NAMES,
)

__all__ = [
    "route_apps", "route_sites",
    "route_music", "route_vision",
    "route_system", "route_files",
    "route_memory",
    "_extract_app_name", "_extract_install_name",
    "_SITES", "_APPS", "_PROC_ALIASES",
    "_MUSIC_STOP", "_CLOSE_TRIGGER", "_OPEN_TRIGGER",
    "_FUZZY_COMMANDS", "_FUZZY_THRESHOLD", "_INSTALL_APP_NAMES",
]
