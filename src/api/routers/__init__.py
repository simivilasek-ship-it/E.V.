"""Register all API routers on the FastAPI app."""
from src.api.routers import (
    activity,
    agents,
    broadcast,
    chat,
    commands,
    config,
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
)


def register_all(app):
    for mod in ROUTERS:
        mod.register(app)
