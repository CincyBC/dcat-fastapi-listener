from __future__ import annotations

from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

_current_route: ContextVar[tuple[str, str] | None] = ContextVar("_current_route", default=None)


def get_current_route() -> tuple[str, str] | None:
    return _current_route.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            method = request.method
            path_template = self._resolve_path_template(request)
            _current_route.set((method, path_template))
        except Exception:
            pass

        try:
            response: Response = await call_next(request)
        finally:
            _current_route.set(None)
        return response

    @staticmethod
    def _resolve_path_template(request: Request) -> str:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return getattr(route, "path", request.url.path)
        return request.url.path
