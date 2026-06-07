"""JARVIS LLM — Engine, Router, Cloud Router."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from llm import LLMEngine  # noqa: F401
except Exception:
    try:
        from .llm import LLMEngine  # noqa: F401
    except Exception:
        pass
try:
    from cloud_router import CloudRouter, get_cloud_router  # noqa: F401
except Exception:
    try:
        from .cloud_router import CloudRouter, get_cloud_router  # noqa: F401
    except Exception:
        pass
try:
    from local_router import LocalRouter  # noqa: F401
except Exception:
    try:
        from .local_router import LocalRouter  # noqa: F401
    except Exception:
        pass
