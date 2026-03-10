from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.db_connection_string,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        logger.error("Database error: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


def verify_connection():
    """Called at startup to confirm Oracle is reachable."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1 FROM DUAL"))
    logger.info("Oracle connection verified successfully.")
