"""Optional LAN API token authentication middleware."""
from __future__ import annotations

from config import CONFIG
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LOCALHOST_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _is_exempt_path(path: str) -> bool:
    if path in ("/health", "/api/health"):
        return True
    return path == "/app" or path.startswith("/app/")


def _is_localhost(request: Request) -> bool:
    if request.client is None:
        return False
    return request.client.host in _LOCALHOST_HOSTS


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    header_token = request.headers.get("X-Jarvis-Token")
    if header_token:
        return header_token.strip()
    return None


class ApiTokenAuthMiddleware(BaseHTTPMiddleware):
    """Require API token for non-localhost requests when enabled in config."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not CONFIG.get("api_auth_required"):
            return await call_next(request)

        path = request.url.path
        if _is_exempt_path(path) or _is_localhost(request):
            return await call_next(request)

        expected = CONFIG.get("api_token") or ""
        provided = _extract_token(request)
        if not expected or provided != expected:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)
