import asyncio
from datetime import UTC, datetime

import pytest

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.feeds.fallback_provider import FallbackMarketDataProvider


def _tick(price: float) -> Tick:
    return Tick(symbol=Symbol.XAUUSD, price=price, timestamp=datetime(2026, 1, 1, tzinfo=UTC))


class _FakeProvider(MarketDataProvider):
    """Scripted fake: `ticks` is either a list of ticks to yield-then-hang,
    or an Exception to raise immediately. Hangs (not returns) after the
    scripted ticks — matching real providers' infinite-stream contract —
    so a clean generator end is never confused with "ran out of script".
    `history`/`history_error` control fetch_history the same way."""

    def __init__(
        self,
        status: FeedStatus,
        ticks: list[Tick] | Exception,
        history: list[Candle] | None = None,
        history_error: Exception | None = None,
    ) -> None:
        self._status = status
        self._ticks = ticks
        self._history = history if history is not None else []
        self._history_error = history_error
        self.connect_count = 0
        self.disconnect_count = 0

    @property
    def nominal_status(self) -> FeedStatus:
        return self._status

    async def connect(self) -> None:
        self.connect_count += 1

    async def disconnect(self) -> None:
        self.disconnect_count += 1

    async def stream_ticks(self, symbols: list[Symbol]):
        if isinstance(self._ticks, Exception):
            raise self._ticks
        for tick in self._ticks:
            yield tick
        await asyncio.Event().wait()

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        if self._history_error is not None:
            raise self._history_error
        return self._history


class _FakeTimeSource:
    """Advances one step per call — deterministic stand-in for wall-clock
    time so fallback_max_duration_seconds can be tested without real waits."""

    def __init__(self, start: float = 0.0, step: float = 1.0) -> None:
        self._value = start
        self._step = step

    def __call__(self) -> float:
        current = self._value
        self._value += self._step
        return current


def test_constructor_rejects_an_empty_provider_list() -> None:
    with pytest.raises(ValueError, match="at least one provider"):
        FallbackMarketDataProvider([])


async def test_stream_ticks_uses_the_primary_when_it_succeeds() -> None:
    # Both fakes hang after their scripted ticks (matching real providers'
    # infinite-stream contract), so consume a bounded number via anext()
    # rather than exhausting the (never-ending) generator with a list comp.
    primary = _FakeProvider(FeedStatus.LIVE, [_tick(1.0), _tick(2.0)])
    fallback = _FakeProvider(FeedStatus.MOCK, [])
    provider = FallbackMarketDataProvider([primary, fallback])

    stream = provider.stream_ticks([Symbol.XAUUSD])
    first = await anext(stream)
    second = await anext(stream)

    assert [first.price, second.price] == [1.0, 2.0]
    assert provider.nominal_status == FeedStatus.LIVE


async def test_stream_ticks_falls_back_immediately_when_the_primary_fails() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, RuntimeError("primary down"))
    fallback = _FakeProvider(FeedStatus.MOCK, [_tick(9.0)])
    provider = FallbackMarketDataProvider([primary, fallback])

    tick = await anext(provider.stream_ticks([Symbol.XAUUSD]))

    assert tick.price == 9.0
    assert provider.nominal_status == FeedStatus.MOCK


async def test_stream_ticks_ends_after_fallback_duration_elapses_to_retry_primary() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, RuntimeError("primary down"))
    fallback = _FakeProvider(FeedStatus.MOCK, [_tick(1.0), _tick(2.0), _tick(3.0), _tick(4.0)])
    # time_source advances by 1.0 per call; max duration 2.0 means the
    # deadline check trips after the second tick's post-yield time check.
    provider = FallbackMarketDataProvider(
        [primary, fallback], fallback_max_duration_seconds=2.0, time_source=_FakeTimeSource(start=0.0, step=1.0)
    )

    seen = [tick async for tick in provider.stream_ticks([Symbol.XAUUSD])]

    # Pins the exact deadline arithmetic, not just "ended early": tick1's
    # post-yield check reads 1.0 (< 2.0, continue), tick2's reads 2.0
    # (>= 2.0, return) — ticks 3 and 4 are never reached.
    assert [t.price for t in seen] == [1.0, 2.0]
    assert provider.nominal_status == FeedStatus.LIVE  # active_index reset to primary on return


async def test_stream_ticks_raises_when_every_provider_fails() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, RuntimeError("primary down"))
    fallback = _FakeProvider(FeedStatus.MOCK, RuntimeError("fallback down too"))
    provider = FallbackMarketDataProvider([primary, fallback])

    with pytest.raises(RuntimeError, match="Every provider"):
        async for _ in provider.stream_ticks([Symbol.XAUUSD]):
            pass

    assert provider.nominal_status == FeedStatus.LIVE  # reset to the primary


async def test_fetch_history_falls_back_when_the_primary_raises() -> None:
    candles = [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=Timeframe.M15,
            open_time=datetime(2026, 1, 1, tzinfo=UTC),
            close_time=datetime(2026, 1, 1, 0, 15, tzinfo=UTC),
            open=1.0,
            high=1.0,
            low=1.0,
            close=1.0,
        )
    ]
    primary = _FakeProvider(FeedStatus.LIVE, [], history_error=RuntimeError("rate limited"))
    fallback = _FakeProvider(FeedStatus.MOCK, [], history=candles)
    provider = FallbackMarketDataProvider([primary, fallback])

    result = await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=100)

    assert result == candles


async def test_fetch_history_raises_the_last_error_when_every_provider_fails() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, [], history_error=RuntimeError("primary error"))
    fallback = _FakeProvider(FeedStatus.MOCK, [], history_error=RuntimeError("fallback error"))
    provider = FallbackMarketDataProvider([primary, fallback])

    with pytest.raises(RuntimeError, match="fallback error"):
        await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=100)


async def test_connect_and_disconnect_delegate_to_every_provider() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, [])
    fallback = _FakeProvider(FeedStatus.MOCK, [])
    provider = FallbackMarketDataProvider([primary, fallback])

    await provider.connect()
    await provider.disconnect()

    assert primary.connect_count == 1
    assert fallback.connect_count == 1
    assert primary.disconnect_count == 1
    assert fallback.disconnect_count == 1


def test_nominal_status_defaults_to_the_first_providers() -> None:
    primary = _FakeProvider(FeedStatus.LIVE, [])
    fallback = _FakeProvider(FeedStatus.MOCK, [])
    provider = FallbackMarketDataProvider([primary, fallback])

    assert provider.nominal_status == FeedStatus.LIVE
