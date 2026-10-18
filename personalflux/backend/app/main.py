from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.observability import RequestContextMiddleware, configure_logging
from app.db.session import get_db
from app.ml.artifact_fetch import ensure_artifacts
from app.services.model_admin import (start_version_poller, startup_load_model,
                                      stop_version_poller)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    ensure_artifacts()          # no-op unless MODEL_ARTIFACT_URL is set
    startup_load_model()        # a missing or invalid model means fallback mode, not a crash
    start_version_poller()      # adopt promotions made by other workers
    yield
    stop_version_poller()


app = FastAPI(
    title=f"{settings.app_name} API", version="0.2.0", lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json",
)

# Added last = outermost: request IDs and logging wrap everything else.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,                  # needed for the HttpOnly refresh cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Session-Id", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)
install_error_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    """Liveness: is the API process up? Does not depend on the database."""
    return {"status": "ok", "service": "personaflux-api"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Readiness: can the API reach the database?"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception:
        return JSONResponse(status_code=503,
                            content={"status": "degraded", "database": "unreachable"})


@app.get("/health/model")
def health_model():
    """Whether this worker is serving the version the database asks for.

    Degraded (503) means either no model at all, or this worker has not yet
    caught up with a promotion. It never blocks /health/liveness.
    """
    from app.ml.registry import registry

    behind = registry.is_behind()
    healthy = registry.model is not None and not behind
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "serving_version": registry.serving_version,
            "desired_version": registry.desired_version,
            "worker_behind": behind,
            "last_check_at": registry.last_check_at.isoformat() if registry.last_check_at else None,
            "error": registry.error or registry.poll_error,
        },
    )
