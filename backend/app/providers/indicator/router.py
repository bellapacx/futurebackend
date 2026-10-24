from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser
from app.modules.entitlements.deps import require_entitlement
from app.modules.indicator.schemas import IndicatorPlotsResponse
from app.providers.indicator.factory import get_indicator_runtime
from app.providers.marketdata.factory import get_marketdata_provider

router = APIRouter(prefix="/indicator", tags=["indicator"])


# For the spike, use a hardcoded script. Later this is replaced by
# SELECT pine_source_encrypted FROM indicator_versions WHERE status='active'.
SPIKE_PINE = """//@version=6
indicator("Spike", overlay=true)
fast = ta.ema(close, 9)
slow = ta.ema(close, 21)
plot(fast, "EMA Fast", color=color.blue)
plot(slow, "EMA Slow", color=color.red)
"""


@router.get("/plots", response_model=IndicatorPlotsResponse)
async def plots(
    symbol: str = Query("NQ"),
    timeframe: str = Query("1m"),
    user: CurrentUser = Depends(require_entitlement),
) -> IndicatorPlotsResponse:
    md = get_marketdata_provider()
    candles = await md.fetch_candles(symbol, timeframe, limit=300)

    runtime = get_indicator_runtime()
    result = await runtime.execute(
        SPIKE_PINE,
        [
            {
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ],
    )

    if result.get("status") != "success":
        return IndicatorPlotsResponse(
            symbol=symbol,
            timeframe=timeframe,
            status="error",
            error=result.get("error"),
            plot_meta={},
            series={},
        )

    return IndicatorPlotsResponse(
        symbol=symbol,
        timeframe=timeframe,
        status="success",
        overlay=result["overlay"],
        plot_meta=result["plot_meta"],
        series=result["series"],
        bars=result["bars"],
    )