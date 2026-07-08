from datetime import UTC, datetime, timedelta

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus
from app.prediction.signal_resolution import resolve_signal
from app.services.signal_tracker import DEFAULT_EXPIRY


def _signal(direction: Direction, entry: float, stop: float, target: float, opened_at: datetime) -> Signal:
    return Signal(
        id=1,
        symbol=Symbol.XAUUSD,
        entry_timeframe=Timeframe.M15,
        direction=direction,
        entry=entry,
        stop=stop,
        target=target,
        risk_reward=2.0,
        reason="test",
        details={},
        opened_at=opened_at,
    )


def _candle(low: float, high: float, close_time: datetime) -> Candle:
    return Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M15,
        open_time=close_time - timedelta(minutes=15),
        close_time=close_time,
        open=(low + high) / 2,
        high=high,
        low=low,
        close=(low + high) / 2,
        volume=0.0,
    )


def test_bullish_stop_hit_resolves_to_loss() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BULLISH, entry=100.0, stop=95.0, target=110.0, opened_at=opened_at)
    candle = _candle(low=94.0, high=99.0, close_time=opened_at + timedelta(minutes=15))

    outcome = resolve_signal(signal, candle, DEFAULT_EXPIRY)

    assert outcome == (SignalStatus.LOSS, -1.0)


def test_bullish_target_hit_resolves_to_win() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BULLISH, entry=100.0, stop=95.0, target=110.0, opened_at=opened_at)
    candle = _candle(low=101.0, high=111.0, close_time=opened_at + timedelta(minutes=15))

    outcome = resolve_signal(signal, candle, DEFAULT_EXPIRY)

    assert outcome == (SignalStatus.WIN, 2.0)


def test_bearish_stop_and_target_mirror_the_bullish_case() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BEARISH, entry=100.0, stop=105.0, target=90.0, opened_at=opened_at)

    loss_candle = _candle(low=99.0, high=106.0, close_time=opened_at + timedelta(minutes=15))
    assert resolve_signal(signal, loss_candle, DEFAULT_EXPIRY) == (SignalStatus.LOSS, -1.0)

    win_candle = _candle(low=89.0, high=99.0, close_time=opened_at + timedelta(minutes=15))
    assert resolve_signal(signal, win_candle, DEFAULT_EXPIRY) == (SignalStatus.WIN, 2.0)


def test_a_candle_hitting_both_stop_and_target_is_conservatively_scored_a_loss() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BULLISH, entry=100.0, stop=95.0, target=110.0, opened_at=opened_at)
    candle = _candle(low=90.0, high=115.0, close_time=opened_at + timedelta(minutes=15))  # spans both levels

    assert resolve_signal(signal, candle, DEFAULT_EXPIRY) == (SignalStatus.LOSS, -1.0)


def test_neither_hit_and_not_expired_stays_open() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BULLISH, entry=100.0, stop=95.0, target=110.0, opened_at=opened_at)
    candle = _candle(low=99.0, high=101.0, close_time=opened_at + timedelta(hours=1))

    assert resolve_signal(signal, candle, DEFAULT_EXPIRY) is None


def test_neither_hit_but_past_expiry_resolves_to_expired() -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _signal(Direction.BULLISH, entry=100.0, stop=95.0, target=110.0, opened_at=opened_at)
    candle = _candle(low=99.0, high=101.0, close_time=opened_at + timedelta(days=6))

    assert resolve_signal(signal, candle, DEFAULT_EXPIRY) == (SignalStatus.EXPIRED, 0.0)
