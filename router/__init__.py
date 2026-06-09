"""
JARVIS router package.
Re-exports LocalRouter (defined in local_router) and all domain routing
functions for direct use.
"""
from local_router import LocalRouter  # noqa: F401

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
    "LocalRouter",
    "route_apps", "route_sites",
    "route_music", "route_vision",
    "route_system", "route_files",
    "route_memory",
    "_extract_app_name", "_extract_install_name",
    "_SITES", "_APPS", "_PROC_ALIASES",
    "_MUSIC_STOP", "_CLOSE_TRIGGER", "_OPEN_TRIGGER",
    "_FUZZY_COMMANDS", "_FUZZY_THRESHOLD", "_INSTALL_APP_NAMES",
]
