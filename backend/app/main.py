import os
from contextlib import asynccontextmanager

import httpx
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


async def _prewarm_pyne(pine_source: str) -> None:
    """
    Send the active Pine script to Pyne at startup so the first user
    request doesn't pay the ~1s compile cost.
    """
    pyne_url = os.getenv("PYNE_API_URL", "http://127.0.0.1:5002").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{pyne_url}/compile/prewarm",
                json={"script": pine_source},
            )
            resp.raise_for_status()
            print(f"[startup] Pyne prewarmed: {pyne_url}")
    except Exception as exc:
        print(f"[startup] Pyne prewarm skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await _prewarm_pyne(SPIKE_PINE)
    yield
    # Shutdown — nothing to clean up yet


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

    return app


app = create_app()