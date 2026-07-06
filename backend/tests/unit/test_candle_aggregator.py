from datetime import UTC, datetime

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Tick
from app.services.candle_aggregator import CandleAggregator


def _tick(symbol: Symbol, price: float, minute: int, second: int, volume: float = 0.0) -> Tick:
    return Tick(
        symbol=symbol,
        price=price,
        timestamp=datetime(2026, 1, 1, 10, minute, second, tzinfo=UTC),
        volume=volume,
    )


def test_first_tick_opens_a_candle_without_closing_one() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))
    assert closed == []


def test_ticks_within_the_same_bucket_do_not_close_a_candle() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))
    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2351.0, 0, 30))
    assert closed == []


def test_tick_in_the_next_bucket_closes_the_prior_candle_with_correct_ohlc() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))
    aggregator.ingest(_tick(Symbol.XAUUSD, 2355.0, 0, 10))
    aggregator.ingest(_tick(Symbol.XAUUSD, 2348.0, 0, 20))

    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2352.0, 1, 0))

    assert len(closed) == 1
    candle = closed[0]
    assert candle.symbol == Symbol.XAUUSD
    assert candle.timeframe == Timeframe.M1
    assert candle.open == 2350.0
    assert candle.high == 2355.0
    assert candle.low == 2348.0
    assert candle.close == 2348.0
    assert candle.open_time == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert candle.close_time == datetime(2026, 1, 1, 10, 1, 0, tzinfo=UTC)


def test_the_new_bucket_tick_opens_its_own_candle() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))
    aggregator.ingest(_tick(Symbol.XAUUSD, 2352.0, 1, 0))

    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2360.0, 2, 0))

    assert len(closed) == 1
    assert closed[0].open == 2352.0
    assert closed[0].open_time == datetime(2026, 1, 1, 10, 1, 0, tzinfo=UTC)


def test_symbols_are_tracked_independently() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))
    aggregator.ingest(_tick(Symbol.EURUSD, 1.085, 0, 0))

    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2351.0, 1, 0))

    assert len(closed) == 1
    assert closed[0].symbol == Symbol.XAUUSD


def test_volume_of_the_opening_tick_is_not_dropped() -> None:
    aggregator = CandleAggregator([Timeframe.M1])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0, volume=5.0))
    aggregator.ingest(_tick(Symbol.XAUUSD, 2351.0, 0, 30, volume=3.0))

    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2352.0, 1, 0, volume=1.0))

    assert len(closed) == 1
    assert closed[0].volume == 8.0


def test_timeframes_are_tracked_independently() -> None:
    aggregator = CandleAggregator([Timeframe.M1, Timeframe.M5])
    aggregator.ingest(_tick(Symbol.XAUUSD, 2350.0, 0, 0))

    closed = aggregator.ingest(_tick(Symbol.XAUUSD, 2351.0, 1, 0))

    assert len(closed) == 1
    assert closed[0].timeframe == Timeframe.M1
