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


def test_bucket_start_is_idempotent_on_exact_boundary() -> None:
    ts = datetime(2026, 1, 1, 10, 5, 0, tzinfo=UTC)
    assert bucket_start(ts, Timeframe.M5) == ts


def test_bucket_start_normalizes_non_utc_input() -> None:
    from datetime import timedelta, timezone

    plus_two = timezone(timedelta(hours=2))
    ts = datetime(2026, 1, 1, 12, 3, 0, tzinfo=plus_two)  # 10:03 UTC
    assert bucket_start(ts, Timeframe.M1) == datetime(2026, 1, 1, 10, 3, 0, tzinfo=UTC)
