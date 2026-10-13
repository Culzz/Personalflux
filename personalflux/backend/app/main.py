from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Is the API itself running? Does not depend on the database."""
    return {"status": "ok", "service": "personaflux-api"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Can the API reach the database?"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception:
        # Never show internal error details to the client.
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unreachable"},
        )