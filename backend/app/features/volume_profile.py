"""Fixed Range Volume Profile: buckets candle volume into price bins over a
given range, to find the Point of Control (highest-volume price) and Value
Area (the band around it holding a target share of total volume).

Used as a confluence check for POI selection — a POI aligning with a
high-volume node/POC carries more weight than one sitting in a low-volume
gap the market moved through quickly.
"""

from dataclasses import dataclass

DEFAULT_BIN_COUNT = 24
DEFAULT_VALUE_AREA_RATIO = 0.70


@dataclass(frozen=True, slots=True)
class VolumeBin:
    price_low: float
    price_high: float
    volume: float


@dataclass(frozen=True, slots=True)
class VolumeProfile:
    bins: list[VolumeBin]
    poc_price: float
    value_area_low: float
    value_area_high: float


def compute_volume_profile(
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    bin_count: int = DEFAULT_BIN_COUNT,
    value_area_ratio: float = DEFAULT_VALUE_AREA_RATIO,
) -> VolumeProfile | None:
    """Distributes each candle's volume evenly across the price bins its
    [low, high] range overlaps. `highs`/`lows`/`volumes` must cover exactly
    the fixed range being profiled (e.g. one impulse leg). Returns None if
    there's no usable range (empty input, or zero price range)."""
    if not highs:
        return None

    range_low = min(lows)
    range_high = max(highs)
    if range_high == range_low:
        return None

    bin_size = (range_high - range_low) / bin_count
    bin_volumes = _distribute_volume(highs, lows, volumes, range_low, bin_size, bin_count)

    bins = [
        VolumeBin(
            price_low=range_low + i * bin_size,
            price_high=range_low + (i + 1) * bin_size,
            volume=bin_volumes[i],
        )
        for i in range(bin_count)
    ]

    poc_index = max(range(bin_count), key=lambda i: bin_volumes[i])
    poc_price = (bins[poc_index].price_low + bins[poc_index].price_high) / 2
    value_area_low, value_area_high = _expand_value_area(bins, poc_index, value_area_ratio)

    return VolumeProfile(
        bins=bins, poc_price=poc_price, value_area_low=value_area_low, value_area_high=value_area_high
    )


def _distribute_volume(
    highs: list[float], lows: list[float], volumes: list[float], range_low: float, bin_size: float, bin_count: int
) -> list[float]:
    bin_volumes = [0.0] * bin_count
    for high, low, volume in zip(highs, lows, volumes, strict=True):
        first_bin = max(0, int((low - range_low) / bin_size))
        last_bin = min(bin_count - 1, int((high - range_low) / bin_size))
        span = last_bin - first_bin + 1
        for b in range(first_bin, last_bin + 1):
            bin_volumes[b] += volume / span
    return bin_volumes


def _expand_value_area(bins: list[VolumeBin], poc_index: int, value_area_ratio: float) -> tuple[float, float]:
    """Grows outward from the POC bin, always adding whichever neighboring
    bin (low or high side) carries more volume, until the target share of
    total volume is captured — the standard value-area algorithm."""
    total_volume = sum(b.volume for b in bins)
    target_volume = total_volume * value_area_ratio

    accumulated = bins[poc_index].volume
    low_index = high_index = poc_index

    while accumulated < target_volume and (low_index > 0 or high_index < len(bins) - 1):
        next_low = low_index - 1
        next_high = high_index + 1
        low_volume = bins[next_low].volume if next_low >= 0 else -1.0
        high_volume = bins[next_high].volume if next_high < len(bins) else -1.0

        if high_volume >= low_volume and next_high < len(bins):
            accumulated += bins[next_high].volume
            high_index = next_high
        elif next_low >= 0:
            accumulated += bins[next_low].volume
            low_index = next_low
        else:
            break

    return bins[low_index].price_low, bins[high_index].price_high
