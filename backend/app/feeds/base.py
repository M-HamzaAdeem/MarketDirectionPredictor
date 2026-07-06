"""Market data provider contract.

Every feed (mock, TradingView, broker fallback) implements this interface so
the rest of the system — aggregation, storage, prediction — never depends on
a concrete provider. Swapping the live feed in later is a new class here,
not a change anywhere else (Open/Closed).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from app.core.constants import Symbol


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: Symbol
    price: float
    timestamp: datetime
    volume: float = 0.0


class MarketDataProvider(ABC):
    """Adapter contract for a live/mock market data source."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish the underlying connection. Idempotent."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down the underlying connection. Idempotent."""

    @abstractmethod
    def stream_ticks(self, symbols: list[Symbol]) -> AsyncIterator[Tick]:
        """Yield ticks for the given symbols until disconnected.

        Implementations are async generators — call with
        `async for tick in provider.stream_ticks(...)`, never `await`.
        Must raise if the first tick is requested before connect() (the
        check runs when iteration starts, not when this method is called).
        """
