"""JARVIS LLM — Engine, Router, Cloud Router."""
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from llm import LLMEngine  # noqa: F401
except Exception as exc:
    logger.warning("Failed to import LLMEngine from root llm: %s", exc)
    try:
        from .llm import LLMEngine  # noqa: F401
    except Exception as exc2:
        logger.warning("Failed to import LLMEngine from src.llm.llm: %s", exc2)
try:
    from cloud_router import CloudRouter, get_cloud_router  # noqa: F401
except Exception as exc:
    logger.warning("Failed to import CloudRouter from root cloud_router: %s", exc)
    try:
        from .cloud_router import CloudRouter, get_cloud_router  # noqa: F401
    except Exception as exc2:
        logger.warning("Failed to import CloudRouter from src.llm.cloud_router: %s", exc2)
try:
    from local_router import LocalRouter  # noqa: F401
except Exception as exc:
    logger.warning("Failed to import LocalRouter from root local_router: %s", exc)
    try:
        from .local_router import LocalRouter  # noqa: F401
    except Exception as exc2:
        logger.warning("Failed to import LocalRouter from src.llm.local_router: %s", exc2)
