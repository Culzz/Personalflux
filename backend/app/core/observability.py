"""Request IDs, structured access logs, size limit and latency metrics."""
import json
import logging
import re
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import metrics
from app.core.config import settings
from app.core.errors import error_body

logger = logging.getLogger("personaflux")
_RID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format="%(message)s")


_GROUPS = ("recommendations", "products", "events", "customers",
           "auth", "analytics", "ml", "admin")


def _group(path: str) -> str:
    """Latency is kept per route family, so one slow area is visible."""
    for segment in path.split("/"):
        if segment in _GROUPS:
            return segment
    return "other"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id", "")
        if not _RID.match(rid):
            rid = uuid.uuid4().hex
        request.state.request_id = rid

        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > settings.max_request_bytes:
            resp = JSONResponse(
                status_code=413,
                content=error_body("payload_too_large", "Request body too large.", request),
            )
            resp.headers["X-Request-ID"] = rid
            return resp

        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            ms = (time.perf_counter() - start) * 1000
            metrics.record(_group(request.url.path), ms, status)
            # Path only: query strings can contain personal data and are not logged.
            logger.info(json.dumps({
                "event": "request", "request_id": rid, "method": request.method,
                "path": request.url.path, "status": status, "duration_ms": round(ms, 1),
            }))
