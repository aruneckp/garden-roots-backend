import atexit
import base64
import logging
import os
import tempfile
from typing import Optional

import oracledb
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config.settings import settings

logger = logging.getLogger(__name__)

_schema = settings.db_schema or None


class Base(DeclarativeBase):
    metadata = MetaData(schema=_schema)


def _build_wallet_dir() -> Optional[str]:
    """
    Write wallet files from env vars into a temp directory.
    Returns the path, or None for local Oracle XE (no wallet).
    """
    if not settings.oracle_ewallet_pem_b64:
        return None

    tmp = tempfile.mkdtemp(prefix="oracle_wallet_")
    atexit.register(_cleanup_wallet, tmp)

    try:
        pem_bytes = base64.b64decode(settings.oracle_ewallet_pem_b64)
    except Exception as exc:
        logger.error("ORACLE_EWALLET_PEM_B64 is not valid base64: %s", exc)
        raise
    # oracledb thin mode requires ewallet.pem (PEM format), not ewallet.p12
    with open(os.path.join(tmp, "ewallet.pem"), "wb") as f:
        f.write(pem_bytes)

    if settings.oracle_tnsnames:
        with open(os.path.join(tmp, "tnsnames.ora"), "w") as f:
            f.write(settings.oracle_tnsnames)

    if settings.oracle_sqlnet:
        with open(os.path.join(tmp, "sqlnet.ora"), "w") as f:
            f.write(settings.oracle_sqlnet)

    # Override any pre-set TNS_ADMIN (e.g. Railway env var pointing to a
    # non-existent volume) so oracledb finds tnsnames.ora in our temp dir.
    os.environ["TNS_ADMIN"] = tmp
    logger.info("Oracle wallet dir ready: %s  (TNS_ADMIN overridden)", tmp)
    return tmp


def _cleanup_wallet(path: str) -> None:
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


_wallet_dir = _build_wallet_dir()


def _make_connection():
    """
    oracledb.connect() called directly so SQLAlchemy never parses the DSN.
    For ADB:  dsn = TNS alias  →  resolved via tnsnames.ora in config_dir.
    For XE:   dsn = host:port/service  →  plain TCP.
    """
    if _wallet_dir:
        return oracledb.connect(
            user=settings.db_user,
            password=settings.db_password,
            dsn=settings.db_service,
            config_dir=_wallet_dir,
            wallet_location=_wallet_dir,
            wallet_password=settings.oracle_wallet_password or None,
        )

    logger.debug(
        "Connecting via TCP | host=%s port=%s service=%s",
        settings.db_host, settings.db_port, settings.db_service,
    )
    return oracledb.connect(
        user=settings.db_user,
        password=settings.db_password,
        dsn=f"{settings.db_host}:{settings.db_port}/{settings.db_service}",
    )


if _wallet_dir:
    print(f"[DB] mode=ADB-wallet  service={settings.db_service}", flush=True)
    logger.info("DB mode: ADB wallet | service=%s", settings.db_service)
else:
    print(
        f"[DB] mode=local-TCP  host={settings.db_host}:{settings.db_port}"
        f"  service={settings.db_service}",
        flush=True,
    )
    logger.info(
        "DB mode: local TCP | host=%s:%s service=%s",
        settings.db_host, settings.db_port, settings.db_service,
    )

engine = create_engine(
    "oracle+oracledb://",
    creator=_make_connection,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    echo=settings.debug,
)

if _schema:
    logger.info("Oracle schema: %s", _schema)

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
