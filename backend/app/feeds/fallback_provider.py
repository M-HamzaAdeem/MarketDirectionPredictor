"""Composite MarketDataProvider that tries a priority-ordered list of
providers, falling back to the next one the moment the current one fails —
satisfies PROJECT.md's "safe fallback if live feed is unavailable" rule.

This composes with, rather than duplicates, FeedService's own
reconnect-with-backoff (Phase 8): falling back to the next provider happens
immediately inside a single `stream_ticks()` call, without waiting out a
backoff delay. Only once every provider in the chain has failed does this
raise, letting FeedService's outer loop back off before retrying the whole
chain from the top. While parked on a fallback provider, this deliberately
ends the stream after `fallback_max_duration_seconds` (even though nothing
failed) so FeedService's existing "stream ended -> reconnect -> retry"
handling gives the primary provider another chance periodically, rather
than staying on the fallback forever once it's been used once.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK_MAX_DURATION_SECONDS = 300.0


def _running_loop_time() -> float:
    return asyncio.get_running_loop().time()


class FallbackMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        providers: list[MarketDataProvider],
        fallback_max_duration_seconds: float = _DEFAULT_FALLBACK_MAX_DURATION_SECONDS,
        time_source: Callable[[], float] = _running_loop_time,
    ) -> None:
        if not providers:
            raise ValueError("FallbackMarketDataProvider requires at least one provider")
        self._providers = providers
        self._fallback_max_duration_seconds = fallback_max_duration_seconds
        self._time_source = time_source
        self._active_index = 0

    @property
    def nominal_status(self) -> FeedStatus:
        return self._providers[self._active_index].nominal_status

    async def connect(self) -> None:
        # Connect every provider up front (all connect() implementations in
        # this codebase are cheap/non-blocking), so falling back mid-stream
        # never has to wait on a fresh connection first.
        for provider in self._providers:
            await provider.connect()

    async def disconnect(self) -> None:
        for provider in self._providers:
            await provider.disconnect()

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        last_error: Exception | None = None
        for index, provider in enumerate(self._providers):
            try:
                return await provider.fetch_history(symbol, timeframe, count)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "fetch_history failed on provider %d/%d (%s): %s",
                    index + 1,
                    len(self._providers),
                    type(provider).__name__,
                    exc,
                )
        assert last_error is not None  # providers is non-empty, so the loop ran at least once
        raise last_error

    async def stream_ticks(self, symbols: list[Symbol]) -> AsyncIterator[Tick]:
        for index, provider in enumerate(self._providers):
            self._active_index = index
            is_fallback = index > 0
            deadline = self._time_source() + self._fallback_max_duration_seconds if is_fallback else None

            try:
                async for tick in provider.stream_ticks(symbols):
                    yield tick
                    if deadline is not None and self._time_source() >= deadline:
                        logger.info(
                            "Fallback duration elapsed on %s; ending this attempt so FeedService "
                            "retries from the primary provider",
                            type(provider).__name__,
                        )
                        self._active_index = 0
                        return
            except Exception:
                logger.exception(
                    "stream_ticks failed on provider %d/%d (%s); falling back",
                    index + 1,
                    len(self._providers),
                    type(provider).__name__,
                )
                continue

        self._active_index = 0
        raise RuntimeError("Every provider in the fallback chain failed")
