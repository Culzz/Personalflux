from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

def connect_args_for(url: str, statement_timeout_ms: int) -> dict:
    """psycopg arguments for one database URL.

    Two server behaviours need to be stated here rather than left to chance:

    * A statement timeout stops one stuck query from holding a worker and a
      pooled connection indefinitely, which is what turns a slow query into an
      outage. It travels in the startup packet, and a PgBouncer pooler refuses
      startup parameters it does not recognise (Neon answers "unsupported
      startup parameter in options"), so it is only sent to a direct connection.
    * A URL naming a PgBouncer pooler (Neon's `-pooler` endpoint is one) is
      running in transaction mode, where a protocol-level prepared statement
      cannot be reused across transactions. psycopg starts preparing a statement
      after it has run five times, so on a pooler that produces intermittent
      "prepared statement does not exist" errors under load. Disabling the
      threshold keeps the pooler usable.

    In practice the app connects to the direct endpoint when one is published
    (see Settings.connection_url), so the pooler branch is the fallback.
    """
    args: dict = {}
    if url.startswith("postgresql"):
        if "-pooler" in url:
            args["prepare_threshold"] = None
        else:
            args["options"] = f"-c statement_timeout={statement_timeout_ms}"
    return args


engine = create_engine(
    settings.connection_url,
    pool_pre_ping=True,                       # drop connections the server closed underneath us
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_timeout=settings.db_pool_timeout_seconds,
    connect_args=connect_args_for(settings.connection_url, settings.db_statement_timeout_ms),
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
