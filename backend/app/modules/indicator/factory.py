from functools import lru_cache

from app.core.config import get_settings
from app.providers.indicator.base import IndicatorRuntime
from app.providers.indicator.stub import StubIndicatorRuntime


@lru_cache
def get_indicator_runtime() -> IndicatorRuntime:
    settings = get_settings()
    if settings.indicator_runtime == "stub":
        return StubIndicatorRuntime()
    raise NotImplementedError(
        f"Indicator runtime '{settings.indicator_runtime}' not implemented"
    )