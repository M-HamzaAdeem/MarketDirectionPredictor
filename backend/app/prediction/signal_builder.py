"""ICT-style signal builder: 4H bias -> 1H setup (sweep + POI + OTE +
volume-profile confluence) -> 15m entry confirmation.

A Signal is only ever constructed once every stage confirms AND the
resulting risk:reward clears MIN_RISK_REWARD — there is no "maybe" output,
no partial signal, no fallback score. Any stage failing to confirm means
build_signal() returns None. This is a deliberately stricter contract than
the Phase 3 rule-based PredictionStrategy (which always returns a
direction/confidence): this pipeline only ever produces winning-caliber,
fully-specified trade setups, per PROJECT.md's "only create winning
signals" requirement.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.features.fibonacci import OteZone, compute_ote_zone
from app.features.indicators import average_true_range
from app.features.poi import FairValueGap, OrderBlock, detect_fair_value_gaps, detect_order_blocks
from app.features.structure import (
    StructureBreak,
    StructureEvent,
    Sweep,
    SwingKind,
    SwingPoint,
    detect_structure_breaks,
    detect_swing_points,
    detect_sweeps,
    weak_points,
)
from app.features.volume_profile import VolumeProfile, compute_volume_profile
from app.prediction.signal import Signal

MIN_RISK_REWARD = 1.8
DEFAULT_STOP_ATR_BUFFER_MULTIPLIER = 0.25
_FALLBACK_STOP_BUFFER_RATIO = 0.001  # used only if ATR isn't available yet


@dataclass(frozen=True, slots=True)
class _Setup:
    direction: Direction
    entry_low: float
    entry_high: float
    poi_type: str
    stop: float
    target: float
    swept_level: float
    ote: OteZone
    volume_profile_poc: float | None
    confirming_event: StructureEvent
    # The OTE zone is only known once leg_end is in — this is that 1H
    # candle's close_time. A 15m "tap" that closed before this is just the
    # original impulsive move passing through the zone's price range before
    # the zone existed, not a genuine retracement into it; see
    # decisions.md's stale-entry-tap entry.
    earliest_entry_time: datetime


def build_signal(
    symbol: Symbol,
    candles_4h: list[Candle],
    candles_1h: list[Candle],
    candles_15m: list[Candle],
) -> Signal | None:
    """Every candle list must be closed candles in ascending open_time order."""
    bias = _determine_bias(candles_4h)
    if bias == Direction.NEUTRAL:
        return None

    setup = _find_setup(bias, candles_1h)
    if setup is None:
        return None

    tap_candle = _check_entry(setup.entry_low, setup.entry_high, candles_15m, setup.earliest_entry_time)
    if tap_candle is None:
        return None

    return _assemble_signal(symbol, setup, tap_candle)


def eligible_entry_candles(candles: list[Candle], after: datetime | None) -> list[Candle]:
    """15m candles eligible as a fresh entry tap: strictly after the tap
    candle of the last signal already opened for this symbol, if any.
    Without this, `_check_entry`'s rolling window can rediscover the exact
    same historical tap and reopen it the instant its predecessor
    resolves, for as long as it remains inside the window — see
    [[backtest-rapid-reopen-fix]] in decisions.md. Shared by SignalService
    (live) and run_signal_backtest so the eligibility rule can't silently
    diverge between the two."""
    if after is None:
        return candles
    return [candle for candle in candles if candle.close_time > after]


def _assemble_signal(symbol: Symbol, setup: _Setup, tap_candle: Candle) -> Signal | None:
    entry = (setup.entry_low + setup.entry_high) / 2
    risk = abs(entry - setup.stop)
    if risk <= 0:
        return None

    # Signed, not abs(): the target must sit strictly beyond entry in the
    # trade direction, or the ratio is meaningless even if it looks large
    # (e.g. a degenerate zero-range leg inflating R:R off a tiny risk).
    reward = setup.target - entry if setup.direction == Direction.BULLISH else entry - setup.target
    if reward <= 0:
        return None

    risk_reward = reward / risk
    if risk_reward < MIN_RISK_REWARD:
        return None

    return Signal(
        symbol=symbol,
        entry_timeframe=Timeframe.M15,
        direction=setup.direction,
        entry=entry,
        stop=setup.stop,
        target=setup.target,
        risk_reward=round(risk_reward, 2),
        reason=_build_reason(setup, risk_reward),
        details=_build_details(setup),
        opened_at=tap_candle.close_time,
    )


def _determine_bias(candles: list[Candle]) -> Direction:
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    timestamps = [c.open_time for c in candles]

    swings = detect_swing_points(highs, lows, timestamps)
    breaks = detect_structure_breaks(swings, closes, timestamps)
    return breaks[-1].direction if breaks else Direction.NEUTRAL


def _find_setup(bias: Direction, candles: list[Candle]) -> _Setup | None:
    opens = [c.open for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    timestamps = [c.open_time for c in candles]

    swings = detect_swing_points(highs, lows, timestamps)
    sweeps = detect_sweeps(swings, highs, lows, closes, timestamps)
    breaks = detect_structure_breaks(swings, closes, timestamps)

    confirming_break = next((b for b in reversed(breaks) if b.direction == bias), None)
    if confirming_break is None:
        return None

    swept_kind = SwingKind.LOW if bias == Direction.BULLISH else SwingKind.HIGH
    confirming_sweep = next(
        (
            s
            for s in reversed(sweeps)
            if s.swept_point.kind == swept_kind and s.sweep_index < confirming_break.break_index
        ),
        None,
    )
    if confirming_sweep is None:
        return None

    leg_start_index = confirming_sweep.sweep_index
    leg_start_price = lows[leg_start_index] if bias == Direction.BULLISH else highs[leg_start_index]
    leg_end_index, leg_end_price = _find_leg_end(bias, highs, lows, confirming_break.break_index)

    atr_values = _atr_values(highs, lows, closes)
    order_blocks = detect_order_blocks(opens, highs, lows, closes, atr_values, timestamps)
    fvgs = detect_fair_value_gaps(highs, lows, timestamps)
    candidates = _poi_candidates(bias, order_blocks, fvgs, leg_start_index, leg_end_index)
    if not candidates:
        return None

    ote = compute_ote_zone(leg_start_price, leg_end_price, bias)
    overlaps = [z for poi in candidates if (z := _intersect(poi, ote)) is not None]
    if not overlaps:
        return None

    volume_profile = compute_volume_profile(
        highs[leg_start_index : leg_end_index + 1],
        lows[leg_start_index : leg_end_index + 1],
        [c.volume for c in candles[leg_start_index : leg_end_index + 1]],
    )
    entry_low, entry_high, poi_type = _pick_best_zone(overlaps, volume_profile)

    stop = _compute_stop(bias, leg_start_price, atr_values[leg_start_index])
    target_point = _find_target(bias, entry_low, entry_high, swings, sweeps, breaks)
    if target_point is None:
        return None

    return _Setup(
        direction=bias,
        entry_low=entry_low,
        entry_high=entry_high,
        poi_type=poi_type,
        stop=stop,
        target=target_point,
        swept_level=leg_start_price,
        ote=ote,
        volume_profile_poc=volume_profile.poc_price if volume_profile else None,
        confirming_event=confirming_break.event,
        earliest_entry_time=candles[leg_end_index].close_time,
    )


def _find_leg_end(bias: Direction, highs: list[float], lows: list[float], break_index: int) -> tuple[int, float]:
    tail = range(break_index, len(highs))
    if bias == Direction.BULLISH:
        index = max(tail, key=lambda i: highs[i])
        return index, highs[index]
    index = min(tail, key=lambda i: lows[i])
    return index, lows[index]


def _atr_values(highs: list[float], lows: list[float], closes: list[float]) -> list[float | None]:
    series = average_true_range(pd.Series(highs), pd.Series(lows), pd.Series(closes))
    return [None if pd.isna(v) else float(v) for v in series]


def _poi_candidates(
    bias: Direction,
    order_blocks: list[OrderBlock],
    fvgs: list[FairValueGap],
    leg_start_index: int,
    leg_end_index: int,
) -> list[tuple[float, float, str]]:
    candidates = [
        (ob.low, ob.high, "order_block")
        for ob in order_blocks
        if ob.direction == bias and leg_start_index <= ob.index <= leg_end_index
    ]
    candidates += [
        (fvg.low, fvg.high, "fair_value_gap")
        for fvg in fvgs
        if fvg.direction == bias and leg_start_index <= fvg.index <= leg_end_index
    ]
    return candidates


def _intersect(poi: tuple[float, float, str], ote: OteZone) -> tuple[float, float, str] | None:
    low = max(poi[0], ote.low)
    high = min(poi[1], ote.high)
    if low < high:
        return (low, high, poi[2])
    return None


def _pick_best_zone(
    zones: list[tuple[float, float, str]], volume_profile: VolumeProfile | None
) -> tuple[float, float, str]:
    if volume_profile is None or len(zones) == 1:
        return zones[0]
    return min(zones, key=lambda z: abs((z[0] + z[1]) / 2 - volume_profile.poc_price))


def _compute_stop(bias: Direction, swept_level: float, atr: float | None) -> float:
    if atr is not None:
        buffer = atr * DEFAULT_STOP_ATR_BUFFER_MULTIPLIER
    else:
        buffer = abs(swept_level) * _FALLBACK_STOP_BUFFER_RATIO
    return swept_level - buffer if bias == Direction.BULLISH else swept_level + buffer


def _find_target(
    bias: Direction,
    entry_low: float,
    entry_high: float,
    swings: list[SwingPoint],
    sweeps: list[Sweep],
    breaks: list[StructureBreak],
) -> float | None:
    weak = weak_points(swings, sweeps, breaks)
    opposing_kind = SwingKind.HIGH if bias == Direction.BULLISH else SwingKind.LOW
    opposing = [p for p in weak if p.kind == opposing_kind]

    if bias == Direction.BULLISH:
        beyond = [p for p in opposing if p.price > entry_high]
        return min((p.price for p in beyond), default=None)
    beyond = [p for p in opposing if p.price < entry_low]
    return max((p.price for p in beyond), default=None)


def _check_entry(
    entry_low: float, entry_high: float, candles: list[Candle], earliest_entry_time: datetime
) -> Candle | None:
    for candle in reversed(candles):
        if candle.close_time <= earliest_entry_time:
            break  # candles are ascending order; nothing earlier can qualify either
        if candle.low <= entry_high and candle.high >= entry_low:
            return candle
    return None


def _build_reason(setup: _Setup, risk_reward: float) -> str:
    event_label = "CHoCH" if setup.confirming_event == StructureEvent.CHOCH else "BOS"
    return (
        f"{setup.direction.value} bias confirmed by {event_label}; liquidity swept at {setup.swept_level:.5f}; "
        f"entry at {setup.poi_type} within OTE [{setup.ote.low:.5f}, {setup.ote.high:.5f}]; "
        f"target {setup.target:.5f} (next opposing liquidity); R:R {risk_reward:.2f}"
    )


def _build_details(setup: _Setup) -> dict[str, float | str | None]:
    return {
        "poi_type": setup.poi_type,
        "ote_low": setup.ote.low,
        "ote_high": setup.ote.high,
        "swept_level": setup.swept_level,
        "volume_profile_poc": setup.volume_profile_poc,
        "confirming_event": setup.confirming_event.value,
        "earliest_entry_time": setup.earliest_entry_time.isoformat(),
    }
