import asyncio
import time
from datetime import datetime, timedelta, timezone

import databento as db
from databento.common.error import BentoClientError

from app.core.config import get_settings
from app.providers.marketdata.base import Candle, MarketDataProvider

# In-memory cache: (symbol, timeframe) -> (timestamp, candles)
_CACHE: dict[tuple[str, str], tuple[float, list[Candle]]] = {}
_CACHE_LOCK = asyncio.Lock()
CACHE_TTL = 60  # seconds

# How far back each timeframe pulls (end = now - 25h to stay in free-credit range)
TF_WINDOW = {
    "1m": timedelta(hours=5),
    "5m": timedelta(hours=12),
    "15m": timedelta(days=1),
    "1h": timedelta(days=3),
    "1d": timedelta(days=14),
}

TF_SCHEMA = {
    "1m": "ohlcv-1m",
    "5m": "ohlcv-1m",
    "15m": "ohlcv-1m",
    "1h": "ohlcv-1m",
    "1d": "ohlcv-1d",
}


class DatabentoProvider(MarketDataProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.databento_api_key:
            raise RuntimeError("DATABENTO_API_KEY is not set")
        self._client = db.Historical(settings.databento_api_key)

    async def fetch_candles(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> list[Candle]:
        key = (symbol, timeframe)
        now = time.time()

        # Fast path: serve from cache without acquiring the lock
        cached = _CACHE.get(key)
        if cached is not None:
            ts, rows = cached
            if now - ts < CACHE_TTL:
                return rows[-limit:]

        # Slow path: single fetch under lock
        async with _CACHE_LOCK:
            # Re-check after acquiring (another task may have populated it)
            cached = _CACHE.get(key)
            if cached is not None:
                ts, rows = cached
                if time.time() - ts < CACHE_TTL:
                    return rows[-limit:]

            rows = await asyncio.to_thread(
                self._fetch_from_databento, symbol, timeframe
            )
            _CACHE[key] = (time.time(), rows)
            return rows[-limit:]

    def _fetch_from_databento(
        self, symbol: str, timeframe: str
    ) -> list[Candle]:
        """Blocking Databento fetch — runs in a thread via to_thread."""
        end = datetime.now(timezone.utc) - timedelta(hours=25)
        window = TF_WINDOW.get(timeframe, timedelta(hours=5))
        start = end - window

        schema = TF_SCHEMA.get(timeframe, "ohlcv-1m")
        continuous_symbol = f"{symbol}.v.0"

        try:
            data = self._client.timeseries.get_range(
                dataset="GLBX.MDP3",
                schema=schema,
                symbols=continuous_symbol,
                stype_in="continuous",
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except BentoClientError:
            return []

        df = data.to_df()
        if df.empty:
            return []

        rows: list[Candle] = []
        for ts, row in df.iterrows():
            rows.append(
                Candle(
                    time=int(ts.timestamp()),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )

        if timeframe in ("5m", "15m", "1h") and schema == "ohlcv-1m":
            rows = _aggregate(rows, timeframe)

        return rows


def _aggregate(candles: list[Candle], timeframe: str) -> list[Candle]:
    bucket_seconds = {"5m": 300, "15m": 900, "1h": 3600}[timeframe]
    buckets: dict[int, Candle] = {}

    for c in candles:
        key = (c.time // bucket_seconds) * bucket_seconds
        if key not in buckets:
            buckets[key] = Candle(
                time=key,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
        else:
            b = buckets[key]
            b.high = max(b.high, c.high)
            b.low = min(b.low, c.low)
            b.close = c.close
            b.volume += c.volume

    return [buckets[k] for k in sorted(buckets)]