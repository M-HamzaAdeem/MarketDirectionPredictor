from datetime import UTC, datetime

import pytest

from app.core.constants import Timeframe
from app.utils.time import bucket_start, timeframe_seconds


@pytest.mark.parametrize(
    ("timeframe", "expected_seconds"),
    [
        (Timeframe.M1, 60),
        (Timeframe.M5, 300),
        (Timeframe.M15, 900),
        (Timeframe.H1, 3_600),
        (Timeframe.H4, 14_400),
        (Timeframe.D1, 86_400),
        (Timeframe.W1, 604_800),
    ],
)
def test_timeframe_seconds(timeframe: Timeframe, expected_seconds: int) -> None:
    assert timeframe_seconds(timeframe) == expected_seconds


def test_bucket_start_floors_to_timeframe_boundary() -> None:
    ts = datetime(2026, 1, 1, 10, 3, 27, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.M1) == datetime(2026, 1, 1, 10, 3, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.M5) == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.M15) == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.H1) == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)


def test_bucket_start_floors_to_a_4_hour_boundary() -> None:
    ts = datetime(2026, 1, 1, 13, 45, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.H4) == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_bucket_start_floors_to_a_utc_midnight_boundary_for_daily() -> None:
    ts = datetime(2026, 1, 1, 13, 45, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.D1) == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_bucket_start_weekly_is_thursday_anchored_not_monday() -> None:
    # Documented quirk (see bucket_start's docstring): epoch 0 was a
    # Thursday, so epoch-floored weekly buckets land on Thursdays, not the
    # Monday most trading platforms (including TradingView's own
    # server-aggregated weekly bars) anchor a week to. 2026-01-01 is
    # itself a Thursday -- this pins that behavior rather than letting it
    # silently drift to a different day if the epoch-floor math ever changes.
    ts = datetime(2026, 1, 1, 13, 45, 0, tzinfo=UTC)
    bucket = bucket_start(ts, Timeframe.W1)
    assert bucket == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert bucket.weekday() == 3  # Thursday


def test_bucket_start_is_idempotent_on_exact_boundary() -> None:
    ts = datetime(2026, 1, 1, 10, 5, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.M5) == ts


def test_bucket_start_normalizes_non_utc_input() -> None:
    from datetime import timedelta, timezone

    plus_two = timezone(timedelta(hours=2))
    ts = datetime(2026, 1, 1, 12, 3, 0, tzinfo=plus_two)  # 10:03 UTC
    assert bucket_start(ts, Timeframe.M1) == datetime(2026, 1, 1, 10, 3, 0, tzinfo=UTC)
