from abc import ABC, abstractmethod
from typing import Any


class IndicatorRuntime(ABC):
    @abstractmethod
    async def execute(
        self, pine_source: str, candles: list[dict[str, Any]]
    ) -> dict[str, Any]: ...