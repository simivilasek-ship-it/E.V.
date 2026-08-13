"""Register all API routers on the FastAPI app."""
import logging
from src.api.routers import (
    activity,
    agents,
    broadcast,
    chat,
    commands,
    config,
    docs,
    graph,
    marketplace,
    memory,
    missions,
    missions_checklist,
    monitoring,
    settings,
    skills,
    vision,
    vision_post,
    websockets,
    workflows,
    ws_agents,
)

logger = logging.getLogger(__name__)

ROUTERS = (
    monitoring,
    commands,
    marketplace,
    memory,
    config,
    workflows,
    missions,
    missions_checklist,
    activity,
    vision,
    agents,
    skills,
    chat,
    websockets,
    settings,
    vision_post,
    graph,
    ws_agents,
    broadcast,
    docs,
)


def register_all(app):
    for mod in ROUTERS:
        mod.register(app)
    try:
        from src.api.routers.proactive import router as proactive_router
        app.include_router(proactive_router)
    except Exception as e:
        logger.warning("Proactive router: %s", e)
