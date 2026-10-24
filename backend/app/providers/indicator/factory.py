from functools import lru_cache

from app.core.config import get_settings
from app.providers.indicator.base import IndicatorRuntime
from app.providers.indicator.hoox_pyne import HooxPyneRuntime


class _StubRuntime(IndicatorRuntime):
    async def execute(self, pine_source, candles):
        return {
            "status": "success",
            "overlay": False,
            "plot_meta": {},
            "series": {},
            "bars": len(candles),
            "mode": "stub",
        }


@lru_cache
def get_indicator_runtime() -> IndicatorRuntime:
    settings = get_settings()
    if settings.indicator_runtime == "hoox_pyne":
        return HooxPyneRuntime()
    return _StubRuntime()