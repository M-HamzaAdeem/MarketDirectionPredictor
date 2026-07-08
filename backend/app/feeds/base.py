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

from app.core.constants import FeedStatus, Symbol, Timeframe


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: Symbol
    price: float
    timestamp: datetime
    volume: float = 0.0


@dataclass(frozen=True, slots=True)
class Candle:
    """A closed OHLC candle for one symbol/timeframe bucket."""

    symbol: Symbol
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class MarketDataProvider(ABC):
    """Adapter contract for a live/mock market data source."""

    @property
    @abstractmethod
    def nominal_status(self) -> FeedStatus:
        """The FeedStatus this provider reports while streaming normally
        (e.g. MOCK for the synthetic feed, LIVE for a real one). FeedService
        reads this live from the provider each time rather than caching it
        once at construction, so a provider whose nominal status can change
        over its lifetime is reported correctly."""

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

    @abstractmethod
    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        """Fetch up to `count` most recent CLOSED candles, oldest-first.

        Used to backfill storage on startup so predictions/signals don't
        have to wait for enough live candles to accumulate before they can
        run. A provider with no historical concept (e.g. a pure synthetic
        feed) may return an empty list — backfill is then a no-op for it.
        """
