from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
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