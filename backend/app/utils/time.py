"""Timeframe bucketing helpers shared by candle aggregation and storage."""

from datetime import UTC, datetime

from app.core.constants import Timeframe

_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    Timeframe.M1: 60,
    Timeframe.M5: 300,
    Timeframe.M15: 900,
    Timeframe.H1: 3_600,
    Timeframe.H4: 14_400,
    Timeframe.D1: 86_400,
    Timeframe.W1: 604_800,
}


def timeframe_seconds(timeframe: Timeframe) -> int:
    return _TIMEFRAME_SECONDS[timeframe]


def bucket_start(timestamp: datetime, timeframe: Timeframe) -> datetime:
    """Floor `timestamp` to the start of its timeframe bucket, in UTC.

    Every timeframe up to D1 divides evenly into a day, so flooring
    against the Unix epoch (1970-01-01T00:00 UTC, itself a day boundary)
    always lands on UTC-midnight-aligned buckets — matching any
    conventional day-boundary expectation. W1 (604800s) is the one
    exception: since epoch 0 was a *Thursday*, epoch-floored weekly
    buckets start on Thursdays, not the Monday (or Sunday) most trading
    platforms anchor a "week" to — including TradingView's own
    server-aggregated weekly bars, which this pipeline's Twelve
    Data/mock-sourced weekly candles will therefore not line up with day-
    for-day. Accepted for now: this only affects the tick-aggregated
    pipeline (TradingView's bars are pre-aggregated server-side, unaffected),
    and the rolling-window indicators this feeds (RSI/SMA/momentum, ~100
    weekly bars) aren't meaningfully sensitive to a few days' boundary
    shift. Revisit with a Monday-aligned offset if the day-for-day
    mismatch between sources becomes a real problem someone hits.
    """
    seconds = timeframe_seconds(timeframe)
    epoch_seconds = timestamp.astimezone(UTC).timestamp()
    floored = (epoch_seconds // seconds) * seconds
    return datetime.fromtimestamp(floored, tz=UTC)
