"""Timeframe bucketing helpers shared by candle aggregation and storage."""

from datetime import UTC, datetime

from app.core.constants import Timeframe

_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    Timeframe.M1: 60,
    Timeframe.M5: 300,
    Timeframe.M15: 900,
    Timeframe.H1: 3_600,
    Timeframe.H4: 14_400,
}


def timeframe_seconds(timeframe: Timeframe) -> int:
    return _TIMEFRAME_SECONDS[timeframe]


def bucket_start(timestamp: datetime, timeframe: Timeframe) -> datetime:
    """Floor `timestamp` to the start of its timeframe bucket, in UTC."""
    seconds = timeframe_seconds(timeframe)
    epoch_seconds = timestamp.astimezone(UTC).timestamp()
    floored = (epoch_seconds // seconds) * seconds
    return datetime.fromtimestamp(floored, tz=UTC)
