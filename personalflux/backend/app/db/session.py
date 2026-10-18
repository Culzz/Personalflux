from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# A statement timeout stops one stuck query from holding a worker and a pooled
# connection indefinitely, which is what turns a slow query into an outage.
_connect_args: dict = {}
if settings.database_url.startswith("postgresql"):
    _connect_args["options"] = f"-c statement_timeout={settings.db_statement_timeout_ms}"

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,                       # drop connections the server closed underneath us
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_timeout=settings.db_pool_timeout_seconds,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """All database tables will inherit from this."""


def get_db():
    """One database session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
