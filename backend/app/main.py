import os
import sys
from contextlib import asynccontextmanager

import httpx
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging
from app.modules.billing.router import router as billing_router
from app.modules.entitlements.router import router as entitlements_router
from app.modules.health.router import router as health_router
from app.modules.identity.router import router as identity_router
from app.modules.indicator.router import SPIKE_PINE, router as indicator_router
from app.modules.marketdata.router import router as marketdata_router

# --------------------------------------------------------------------------
# Pyne (Flask) integration
# --------------------------------------------------------------------------
# The vendored pyne source lives at backend/pyne. Add its parent (backend/)
# to sys.path so that the inner package `backend.app` (which is pyne's
# own module namespace) can be imported as `pyne_backend.app`.
#
#   backend/
#   ├── app/            <- this FastAPI app
#   └── pyne/
#       ├── pyproject.toml
#       └── backend/
#           └── app.py  <- Flask `app` object
#
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PYNE_DIR = os.path.join(_BACKEND_DIR, "pyne")
if _PYNE_DIR not in sys.path:
    sys.path.insert(0, _PYNE_DIR)

# Import pyne's Flask app. `backend.app` here refers to pyne's own backend
# package (the vendored source), not our FastAPI `app` package.
from backend.app import app as pyne_flask_app  # noqa: E402


def _pyne_base_url() -> str:
    """
    When mounted in-process, Pyne is reachable at /pyne on the same port
    the FastAPI app listens on. Allow override via PYNE_API_URL for local
    dev where you might still run Pyne standalone on :5002.
    """
    explicit = os.getenv("PYNE_API_URL")
    if explicit:
        return explicit.rstrip("/")
    port = os.getenv("PORT", "8000")
    return f"http://127.0.0.1:{port}/pyne"


async def _prewarm_pyne(pine_source: str) -> None:
    """
    Send the active Pine script to Pyne at startup so the first user
    request doesn't pay the ~1s compile cost.
    """
    base = _pyne_base_url()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base}/compile/prewarm",
                json={"script": pine_source},
            )
            resp.raise_for_status()
            print(f"[startup] Pyne prewarmed: {base}")
    except Exception as exc:
        print(f"[startup] Pyne prewarm skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _prewarm_pyne(SPIKE_PINE)
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Futures Charting API",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)

    app.include_router(health_router)
    app.include_router(identity_router, prefix=settings.api_v1_prefix)
    app.include_router(entitlements_router, prefix=settings.api_v1_prefix)
    app.include_router(billing_router, prefix=settings.api_v1_prefix)
    app.include_router(marketdata_router, prefix=settings.api_v1_prefix)
    app.include_router(indicator_router, prefix=settings.api_v1_prefix)

    # Mount the Pyne Flask app at /pyne. All routes defined inside pyne
    # (e.g. POST /run, POST /compile/prewarm) become /pyne/run, /pyne/compile/prewarm.
    app.mount("/pyne", WSGIMiddleware(pyne_flask_app))

    return app


app = create_app()