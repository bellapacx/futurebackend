from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser,  get_current_user
from app.modules.entitlements.deps import require_entitlement
from app.modules.marketdata.schemas import CandleOut, CandlesResponse
from app.providers.marketdata.factory import get_marketdata_provider

router = APIRouter(prefix="/marketdata", tags=["marketdata"])

VALID_TIMEFRAMES = {"1m", "5m", "15m", "1h", "1d"}
VALID_SYMBOLS = {"NQ", "MNQ"}


@router.get("/candles", response_model=CandlesResponse)
async def candles(
    symbol: str = Query("NQ"),
    timeframe: str = Query("1m"),
    limit: int = Query(500, ge=10, le=5000),
    user: CurrentUser = Depends(get_current_user),
) -> CandlesResponse:
    if symbol not in VALID_SYMBOLS:
        return CandlesResponse(symbol=symbol, timeframe=timeframe, candles=[])
    if timeframe not in VALID_TIMEFRAMES:
        return CandlesResponse(symbol=symbol, timeframe=timeframe, candles=[])

    provider = get_marketdata_provider()
    raw = await provider.fetch_candles(symbol, timeframe, limit=limit)

    return CandlesResponse(
        symbol=symbol,
        timeframe=timeframe,
        candles=[
            CandleOut(
                time=c.time,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in raw
        ],
    )