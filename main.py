import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from utils.logger import configure_logging

# Configure logging FIRST — before any other local imports so module-level
# log calls in database/connection.py are captured.
configure_logging()
logger = logging.getLogger(__name__)

from database.connection import verify_connection  # noqa: E402
from api.v1.router import api_router  # noqa: E402
from middleware.error_handler import (  # noqa: E402
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting %s v%s …", settings.api_title, settings.api_version)
    try:
        verify_connection()
        logger.info("Oracle DB connection verified")
    except Exception as exc:
        # Don't crash — let endpoint calls surface the error clearly
        logger.error("Could not connect to Oracle at startup: %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down %s …", settings.api_title)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    # Disable interactive docs in production — they expose your full API surface.
    # Set DEBUG=True in .env (local only) to re-enable.
    docs_url      ="/docs"         if settings.debug else None,
    redoc_url     ="/redoc"        if settings.debug else None,
    openapi_url   ="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any prod domain listed in .env
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": settings.api_version}


@app.get("/", tags=["health"])
def root():
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
    }
