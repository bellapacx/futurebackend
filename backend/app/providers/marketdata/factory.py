from functools import lru_cache

from app.core.config import get_settings
from app.providers.marketdata.base import MarketDataProvider
from app.providers.marketdata.databento import DatabentoProvider
from app.providers.marketdata.yahoo import YahooProvider


@lru_cache
def get_marketdata_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.marketdata_provider == "databento":
        return DatabentoProvider()
    if settings.marketdata_provider == "yahoo":
        return YahooProvider()
    raise NotImplementedError(
        f"Marketdata provider '{settings.marketdata_provider}' not implemented"
    )