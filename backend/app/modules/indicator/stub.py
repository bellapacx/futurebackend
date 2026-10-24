from typing import Any

from app.providers.indicator.base import IndicatorRuntime


class StubIndicatorRuntime(IndicatorRuntime):
    async def execute(
        self, pine_source: str, candles: list[dict[str, Any]]
    ) -> dict[str, Any]:
        # Returns a placeholder; replaced by hoox_pyne when integrated.
        return {"plots": {}, "note": "stub runtime"}