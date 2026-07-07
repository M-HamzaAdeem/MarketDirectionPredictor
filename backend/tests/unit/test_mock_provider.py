import random

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.mock_provider import MockMarketDataProvider


async def test_ticks_carry_non_zero_volume() -> None:
    provider = MockMarketDataProvider(rng=random.Random(1))
    await provider.connect()

    tick = await anext(provider.stream_ticks([Symbol.XAUUSD]))

    assert tick.volume > 0


async def test_time_acceleration_advances_virtual_clock_faster_than_real_time() -> None:
    provider = MockMarketDataProvider(rng=random.Random(1), time_acceleration=60.0)
    await provider.connect()

    stream = provider.stream_ticks([Symbol.XAUUSD])
    first = await anext(stream)
    second = await anext(stream)  # one real ~0s later (single symbol, no inner sleep yet)

    # Second tick's virtual timestamp is a full accelerated step ahead,
    # not just ~1 real second ahead.
    elapsed = (second.timestamp - first.timestamp).total_seconds()
    assert elapsed == 60.0


async def test_default_acceleration_is_real_time() -> None:
    provider = MockMarketDataProvider(rng=random.Random(1))
    await provider.connect()

    stream = provider.stream_ticks([Symbol.XAUUSD])
    first = await anext(stream)
    second = await anext(stream)

    elapsed = (second.timestamp - first.timestamp).total_seconds()
    assert elapsed == 1.0


async def test_nominal_status_is_mock() -> None:
    assert MockMarketDataProvider().nominal_status == FeedStatus.MOCK


async def test_fetch_history_returns_empty_list() -> None:
    provider = MockMarketDataProvider()

    candles = await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=100)

    assert candles == []
