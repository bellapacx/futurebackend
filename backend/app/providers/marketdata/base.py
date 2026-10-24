from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Candle:
    time: int          # unix seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch_candles(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> list[Candle]: ...