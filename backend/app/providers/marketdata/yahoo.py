import httpx

from app.providers.marketdata.base import Candle, MarketDataProvider

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

TF_MAP = {
    "1m": ("1m", "1d"),
    "5m": ("5m", "5d"),
    "15m": ("15m", "5d"),
    "1h": ("60m", "1mo"),
    "1d": ("1d", "1y"),
}


class YahooProvider(MarketDataProvider):
    async def fetch_candles(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> list[Candle]:
        interval, range_ = TF_MAP.get(timeframe, ("1m", "1d"))
        yahoo_symbol = f"{symbol}=F"
        params = {
            "interval": interval,
            "range": range_,
            "includePrePost": "false",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                YAHOO_CHART_URL.format(symbol=yahoo_symbol), params=params
            )
            resp.raise_for_status()
            data = resp.json()

        result = data["chart"]["result"][0]
        ts = result.get("timestamp") or []
        q = result["indicators"]["quote"][0]

        candles: list[Candle] = []
        for i, t in enumerate(ts):
            try:
                o = q["open"][i]
                h = q["high"][i]
                l = q["low"][i]
                c = q["close"][i]
                v = q["volume"][i] or 0
            except (IndexError, KeyError, TypeError):
                continue
            if None in (o, h, l, c):
                continue
            candles.append(Candle(time=int(t), open=o, high=h, low=l, close=c, volume=v))

        return candles[-limit:]