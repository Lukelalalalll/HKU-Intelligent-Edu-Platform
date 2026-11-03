"""SQLAlchemy engine, session factory and declarative base.

Handlers receive one session per request through ``get_db``; background
workers open their own short-lived sessions and never reuse request state.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""
    pass


# Ping a pooled connection on checkout so a database restart does not surface
# as a stale-connection error on the next request.
engine = create_engine(settings.database_url, pool_pre_ping=True)
# Sessions never autocommit or autoflush; services decide when staged rows
# become visible to the next query.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Yield one session per request and always close it.

    Yields:
        Session: Request-scoped session.  Streaming handlers must close it
        before returning a ``StreamingResponse`` and poll with short-lived
        sessions instead, otherwise one connection is held for the whole
        stream.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

