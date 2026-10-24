from pydantic import BaseModel


class PlotMeta(BaseModel):
    title: str
    color: str | None = None
    linewidth: int = 1
    kind: str = "plot"
    index: int = 0


class IndicatorPlotsResponse(BaseModel):
    symbol: str
    timeframe: str
    status: str
    overlay: bool = False
    plot_meta: dict[str, PlotMeta] = {}
    series: dict[str, list[float | None]] = {}
    bars: int = 0
    error: str | None = None