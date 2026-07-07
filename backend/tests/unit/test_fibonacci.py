import pytest

from app.core.constants import Direction
from app.features.fibonacci import compute_ote_zone


def test_ote_zone_for_a_bullish_leg_retraces_down_from_the_high() -> None:
    # leg: swept low 100 -> swing high 200, range 100
    zone = compute_ote_zone(leg_start=100.0, leg_end=200.0, direction=Direction.BULLISH)

    assert zone.low == pytest.approx(200.0 - 0.79 * 100.0)
    assert zone.high == pytest.approx(200.0 - 0.705 * 100.0)
    assert zone.low < zone.high


def test_ote_zone_for_a_bearish_leg_retraces_up_from_the_low() -> None:
    # leg: swept high 200 -> swing low 100, range 100
    zone = compute_ote_zone(leg_start=200.0, leg_end=100.0, direction=Direction.BEARISH)

    assert zone.low == pytest.approx(100.0 + 0.705 * 100.0)
    assert zone.high == pytest.approx(100.0 + 0.79 * 100.0)
    assert zone.low < zone.high


def test_ote_zone_respects_custom_ratios() -> None:
    zone = compute_ote_zone(
        leg_start=0.0, leg_end=100.0, direction=Direction.BULLISH, shallow_ratio=0.618, deep_ratio=0.786
    )

    assert zone.low == pytest.approx(100.0 - 0.786 * 100.0)
    assert zone.high == pytest.approx(100.0 - 0.618 * 100.0)
