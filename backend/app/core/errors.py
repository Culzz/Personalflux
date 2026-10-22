"""One consistent error format: {"error": {"code", "message", "request_id", "details?"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("personaflux")

CODES = {
    400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
    409: "conflict", 413: "payload_too_large", 422: "validation_error",
    429: "rate_limited", 501: "not_implemented", 503: "unavailable",
}


def error_body(code: str, message: str, request: Request, details=None) -> dict:
    body = {"error": {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }}
    if details:
        body["error"]["details"] = details
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(CODES.get(exc.status_code, "http_error"), message, request),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Only location + message. Never echo the submitted values back.
        details = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", "Invalid request.", request, details),
        )

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception("unhandled error request_id=%s", getattr(request.state, "request_id", None))
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Something went wrong.", request),
        )
