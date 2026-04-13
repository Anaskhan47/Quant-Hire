from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware


_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)
