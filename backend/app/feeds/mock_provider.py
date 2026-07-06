"""Synthetic tick generator used before a live feed is wired in.

Prices random-walk around fixed base levels — good enough to exercise the
pipeline end-to-end, but never mistake this for market data. Callers must
surface FeedStatus.MOCK to the UI whenever this provider is active.
"""

import asyncio
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.core.constants import Symbol
from app.feeds.base import MarketDataProvider, Tick

_BASE_PRICES: dict[Symbol, float] = {
    Symbol.XAUUSD: 2350.0,
    Symbol.EURUSD: 1.0850,
    Symbol.AUDUSD: 0.6600,
}

_TICK_INTERVAL_SECONDS = 1.0
_MAX_STEP_RATIO = 0.0005  # caps synthetic price jump per tick to 0.05%


class MockMarketDataProvider(MarketDataProvider):
    """Generates synthetic ticks for local development and demos."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._connected = False
        self._last_price: dict[Symbol, float] = dict(_BASE_PRICES)
        self._rng = rng if rng is not None else random.Random()

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def stream_ticks(self, symbols: list[Symbol]) -> AsyncIterator[Tick]:
        if not self._connected:
            raise RuntimeError("MockMarketDataProvider.connect() must be called before streaming")

        while self._connected:
            for symbol in symbols:
                self._last_price[symbol] = self._next_price(symbol)
                yield Tick(
                    symbol=symbol,
                    price=self._last_price[symbol],
                    timestamp=datetime.now(UTC),
                )
            await asyncio.sleep(_TICK_INTERVAL_SECONDS)

    def _next_price(self, symbol: Symbol) -> float:
        current = self._last_price[symbol]
        step = current * _MAX_STEP_RATIO * self._rng.uniform(-1, 1)
        return round(current + step, 5)
