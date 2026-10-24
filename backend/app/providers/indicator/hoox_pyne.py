import os
from typing import Any

import httpx

from app.providers.indicator.base import IndicatorRuntime

DEFAULT_PYNE_URL = "http://127.0.0.1:5002"


class HooxPyneRuntime(IndicatorRuntime):
    """
    Executes Pine Script via the self-hosted hoox-pyne Pro API.
    Source never leaves the backend; only numeric series are returned.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("PYNE_API_URL", DEFAULT_PYNE_URL).rstrip("/")

    async def execute(
        self, pine_source: str, candles: list[dict[str, Any]]
    ) -> dict[str, Any]:
        bars = [
            {
                "time": int(c["time"]),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c.get("volume", 0)),
            }
            for c in candles
        ]

        payload = {
            "script": pine_source,
            "data": bars,
            "mode": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/run", json=payload)
                resp.raise_for_status()
                result = resp.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "error_kind": "http",
                "error": f"Pyne HTTP {exc.response.status_code}",
            }
        except httpx.RequestError as exc:
            return {
                "status": "error",
                "error_kind": "network",
                "error": f"Pyne unreachable: {exc}",
            }

        # Contract per docs: {"status": "error", "code": "...", "message": "..."}
        if result.get("status") != "success":
            return {
                "status": "error",
                "error_kind": result.get("error_kind") or result.get("code") or "unknown",
                "error": result.get("message") or result.get("error") or "unknown error",
            }

        return {
            "status": "success",
            "overlay": bool(result.get("overlay", False)),
            "plot_meta": result.get("plot_meta", {}),
            "series": result.get("series", {}),
            "bars": result.get("count", len(bars)),
            "mode": result.get("mode", "auto"),
            "compile_ms": result.get("compile_ms"),
            "cached": result.get("compile_cached", False),
        }