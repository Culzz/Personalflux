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
from app.services.model_admin import startup_load_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    startup_load_model()        # a missing or invalid model means fallback mode, not a crash
    yield


app = FastAPI(
    title=f"{settings.app_name} API", version="0.2.0", lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json",
)

# Added last = outermost: request IDs and logging wrap everything else.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
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
