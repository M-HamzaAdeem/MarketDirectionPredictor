import pytest

from app.features.volume_profile import compute_volume_profile


def test_compute_volume_profile_returns_none_for_empty_input() -> None:
    assert compute_volume_profile([], [], []) is None


def test_compute_volume_profile_returns_none_for_a_zero_price_range() -> None:
    assert compute_volume_profile([10.0, 10.0], [10.0, 10.0], [5.0, 5.0]) is None


def test_compute_volume_profile_returns_none_when_every_candle_has_zero_volume() -> None:
    # OTC forex/commodity feeds (e.g. Twelve Data) report no real volume —
    # a "highest-volume bin" over all-zero input would be meaningless noise
    # (whichever bin happens to sort first), not a real point of control.
    highs = [10.0, 20.0, 100.0]
    lows = [9.0, 19.0, 99.0]
    volumes = [0.0, 0.0, 0.0]

    assert compute_volume_profile(highs, lows, volumes) is None


def test_compute_volume_profile_places_poc_at_the_highest_volume_bin() -> None:
    # A tall, narrow spike of volume clustered near the bottom of the range.
    highs = [10.0, 20.0, 100.0]
    lows = [9.0, 19.0, 99.0]
    volumes = [1.0, 1.0, 1000.0]

    profile = compute_volume_profile(highs, lows, volumes, bin_count=10)

    assert profile is not None
    assert 90.0 <= profile.poc_price <= 100.0


def test_compute_volume_profile_value_area_captures_the_target_share_of_volume() -> None:
    highs = [i + 1.0 for i in range(20)]
    lows = [float(i) for i in range(20)]
    volumes = [1.0] * 20  # evenly distributed volume across the range

    profile = compute_volume_profile(highs, lows, volumes, bin_count=20, value_area_ratio=0.70)

    total_volume = sum(b.volume for b in profile.bins)
    value_area_volume = sum(
        b.volume
        for b in profile.bins
        if b.price_low >= profile.value_area_low and b.price_high <= profile.value_area_high
    )
    assert value_area_volume == pytest.approx(total_volume * 0.70, abs=total_volume * 0.10)
    assert profile.value_area_low < profile.value_area_high


def test_compute_volume_profile_bins_sum_to_total_input_volume() -> None:
    highs = [10.0, 15.0, 20.0]
    lows = [5.0, 10.0, 15.0]
    volumes = [3.0, 4.0, 5.0]

    profile = compute_volume_profile(highs, lows, volumes, bin_count=15)

    assert sum(b.volume for b in profile.bins) == pytest.approx(12.0)
