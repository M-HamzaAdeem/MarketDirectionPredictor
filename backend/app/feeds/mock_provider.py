"""Synthetic tick generator used before a live feed is wired in.

Prices random-walk around fixed base levels — good enough to exercise the
pipeline end-to-end, but never mistake this for market data. Callers must
surface FeedStatus.MOCK to the UI whenever this provider is active.

Tick timestamps advance on a virtual clock rather than wall-clock time, so
`time_acceleration` can compress hours of candle formation into seconds of
real time (a real feed would never do this — its ticks arrive at whatever
rate the market actually trades). Default is real-time (1.0); acceleration
is a deliberate dev/demo convenience, configured via Settings.

The virtual clock advances a fixed step per tick loop (`_TICK_INTERVAL_SECONDS
* time_acceleration`) — it does not measure actual elapsed wall-clock time
between iterations. That's deliberate: candle formation stays deterministic
and reproducible even if the event loop stalls (GC, a slow handler), rather
than drifting with real scheduling variance. A real feed has no equivalent
concept; this only makes sense for a synthetic clock.
"""

import asyncio
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick

_BASE_PRICES: dict[Symbol, float] = {
    Symbol.XAUUSD: 2350.0,
    Symbol.EURUSD: 1.0850,
    Symbol.AUDUSD: 0.6600,
}

_TICK_INTERVAL_SECONDS = 1.0
_MAX_STEP_RATIO = 0.0005  # caps synthetic price jump per tick to 0.05%
_MIN_TICK_VOLUME = 0.1
_MAX_TICK_VOLUME = 5.0  # synthetic per-tick size; gives candle aggregation and
# volume-profile analysis something non-zero to work with — not real volume.


class MockMarketDataProvider(MarketDataProvider):
    """Generates synthetic ticks for local development and demos."""

    def __init__(self, rng: random.Random | None = None, time_acceleration: float = 1.0) -> None:
        self._connected = False
        self._last_price: dict[Symbol, float] = dict(_BASE_PRICES)
        self._rng = rng if rng is not None else random.Random()
        self._time_acceleration = time_acceleration
        self._virtual_time: datetime | None = None

    @property
    def nominal_status(self) -> FeedStatus:
        return FeedStatus.MOCK

    async def connect(self) -> None:
        self._connected = True
        self._virtual_time = datetime.now(UTC)

    async def disconnect(self) -> None:
        self._connected = False

    async def stream_ticks(self, symbols: list[Symbol]) -> AsyncIterator[Tick]:
        if not self._connected or self._virtual_time is None:
            raise RuntimeError("MockMarketDataProvider.connect() must be called before streaming")

        while self._connected:
            for symbol in symbols:
                self._last_price[symbol] = self._next_price(symbol)
                yield Tick(
                    symbol=symbol,
                    price=self._last_price[symbol],
                    timestamp=self._virtual_time,
                    volume=self._next_volume(),
                )
            await asyncio.sleep(_TICK_INTERVAL_SECONDS)
            self._virtual_time += timedelta(seconds=_TICK_INTERVAL_SECONDS * self._time_acceleration)

    def _next_price(self, symbol: Symbol) -> float:
        current = self._last_price[symbol]
        step = current * _MAX_STEP_RATIO * self._rng.uniform(-1, 1)
        return round(current + step, 5)

    def _next_volume(self) -> float:
        return round(self._rng.uniform(_MIN_TICK_VOLUME, _MAX_TICK_VOLUME), 3)

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        # Synthetic feed has no historical concept — startup backfill is a
        # deliberate no-op here; the mock pipeline builds up state live
        # instead, accelerated by time_acceleration.
        return []
