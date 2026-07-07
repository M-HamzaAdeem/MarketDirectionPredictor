from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus
from app.services.signal_tracker import SignalTracker
from app.storage.database import Base
from app.storage.repositories.signal_repository import SignalRepository


class _RecordingBroadcaster:
    def __init__(self) -> None:
        self.signals: list[Signal] = []

    async def broadcast_signal(self, signal: Signal) -> None:
        self.signals.append(signal)


class _FlakyBroadcaster:
    """Raises on the first call, then records every subsequent one — used
    to prove one signal's broadcast failure doesn't cost the others theirs."""

    def __init__(self) -> None:
        self.signals: list[Signal] = []
        self._calls = 0

    async def broadcast_signal(self, signal: Signal) -> None:
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("simulated broadcast failure")
        self.signals.append(signal)


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def _open_signal(opened_at: datetime) -> Signal:
    return Signal(
        symbol=Symbol.XAUUSD,
        entry_timeframe=Timeframe.M15,
        direction=Direction.BULLISH,
        entry=100.0,
        stop=95.0,
        target=110.0,
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


async def test_on_candle_closed_resolves_and_persists_a_win(session_factory) -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        await SignalRepository(session).save(_open_signal(opened_at))

    broadcaster = _RecordingBroadcaster()
    tracker = SignalTracker(session_factory, broadcaster)
    winning_candle = _candle(low=101.0, high=111.0, close_time=opened_at + timedelta(minutes=15))
    await tracker.on_candle_closed(winning_candle)

    async with session_factory() as session:
        recent = await SignalRepository(session).get_recent(Symbol.XAUUSD)

    assert len(recent) == 1
    assert recent[0].status == SignalStatus.WIN
    assert recent[0].realized_rr == 2.0
    assert recent[0].closed_at == winning_candle.close_time

    assert len(broadcaster.signals) == 1
    assert broadcaster.signals[0].status == SignalStatus.WIN
    assert broadcaster.signals[0].realized_rr == 2.0


async def test_on_candle_closed_ignores_signals_on_a_different_timeframe(session_factory) -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    signal = _open_signal(opened_at)
    async with session_factory() as session:
        await SignalRepository(session).save(signal)

    tracker = SignalTracker(session_factory, _RecordingBroadcaster())
    candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.H1,  # signal's entry_timeframe is M15
        open_time=opened_at,
        close_time=opened_at + timedelta(hours=1),
        open=105.0,
        high=111.0,
        low=101.0,
        close=105.0,
        volume=0.0,
    )
    await tracker.on_candle_closed(candle)

    async with session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)

    assert len(open_signals) == 1


async def test_on_candle_closed_leaves_an_unresolved_signal_open(session_factory) -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        await SignalRepository(session).save(_open_signal(opened_at))

    broadcaster = _RecordingBroadcaster()
    tracker = SignalTracker(session_factory, broadcaster)
    neutral_candle = _candle(low=99.0, high=101.0, close_time=opened_at + timedelta(minutes=15))
    await tracker.on_candle_closed(neutral_candle)

    async with session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)

    assert len(open_signals) == 1
    assert open_signals[0].status == SignalStatus.OPEN
    assert broadcaster.signals == []


async def test_a_broadcast_failure_on_one_signal_does_not_block_others(session_factory) -> None:
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        repository = SignalRepository(session)
        await repository.save(_open_signal(opened_at))
        await repository.save(_open_signal(opened_at))

    broadcaster = _FlakyBroadcaster()
    tracker = SignalTracker(session_factory, broadcaster)
    winning_candle = _candle(low=101.0, high=111.0, close_time=opened_at + timedelta(minutes=15))
    await tracker.on_candle_closed(winning_candle)

    async with session_factory() as session:
        recent = await SignalRepository(session).get_recent(Symbol.XAUUSD)

    # Both persisted as WIN regardless of the broadcast failure...
    assert len(recent) == 2
    assert all(signal.status == SignalStatus.WIN for signal in recent)
    # ...and the second signal's broadcast still went through despite the first raising.
    assert len(broadcaster.signals) == 1
