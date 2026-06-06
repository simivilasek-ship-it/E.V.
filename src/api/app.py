"""
JARVIS FastAPI application factory.

Spuštění: python dashboard.py  (port 8002)
"""
from __future__ import annotations

import threading

from src.api.deps import HAS_FASTAPI, logger

if HAS_FASTAPI:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.lifespan import lifespan
    from src.api.paths import ROOT
    from src.api.routers import register_all
    from src.api.ws import broadcast_graph_event

    app = FastAPI(title="JARVIS Dashboard", docs_url=None, redoc_url=None)
    app.router.lifespan_context = lifespan
    app.broadcast_graph_event = broadcast_graph_event

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_all(app)


_web_mounted = False


def mount_web_app() -> bool:
    """Připojí Next.js static export (web_dist/) na /app."""
    global _web_mounted
    if not HAS_FASTAPI or _web_mounted:
        return _web_mounted

    web_dist = ROOT / "web_dist"
    index = web_dist / "index.html"
    if not index.is_file():
        return False

    try:
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        if (web_dist / "_next").is_dir():
            app.mount(
                "/app/_next",
                StaticFiles(directory=str(web_dist / "_next")),
                name="web_next",
            )

        @app.get("/app", include_in_schema=False)
        @app.get("/app/", include_in_schema=False)
        async def web_app_root():
            return FileResponse(str(index))

        @app.get("/app/{full_path:path}", include_in_schema=False)
        async def web_app(full_path: str):
            target = web_dist / full_path
            if target.is_file():
                return FileResponse(str(target))
            return FileResponse(str(index))

        _web_mounted = True
        return True

    except Exception as e:
        import logging as _log

        _log.getLogger(__name__).warning(f"Web app mount selhal: {e}")
        return False


if HAS_FASTAPI:
    mount_web_app()


def run_dashboard(port: int = 8002):
    if not HAS_FASTAPI:
        print("FastAPI není nainstalováno: pip install fastapi uvicorn")
        return
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


run = run_dashboard


def run_dashboard_background(port: int = 8002):
    t = threading.Thread(target=run_dashboard, kwargs={"port": port}, daemon=True)
    t.start()
    return t
