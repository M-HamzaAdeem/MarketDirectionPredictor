from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.services.broadcast_service import BroadcastService
from app.services.signal_service import SignalService
from app.storage.database import Base
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.signal_repository import SignalRepository


class _RecordingConnectionManager:
    def __init__(self) -> None:
        self.broadcasted: list[object] = []

    async def broadcast(self, message: object) -> None:
        self.broadcasted.append(message)


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def _bullish_setup_candles(timeframe: Timeframe) -> list[Candle]:
    # Same validated bullish sweep -> CHoCH -> POI/OTE -> untested target
    # fixture used in tests/unit/test_signal_builder.py.
    opens = [100, 100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118]
    closes = [100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118, 117]
    wicks = [0.3 + 0.02 * i for i in range(len(opens))]
    highs = [max(o, c) + w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows = [min(o, c) - w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows[9] = 89.0

    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=timeframe,
            open_time=base + timedelta(hours=i),
            close_time=base + timedelta(hours=i + 1),
            open=opens[i],
            high=highs[i],
            low=lows[i],
            close=closes[i],
            volume=10.0 + i,
        )
        for i in range(len(closes))
    ]


async def _seed_candles(session_factory, candles: list[Candle]) -> None:
    async with session_factory() as session:
        repository = CandleRepository(session)
        for candle in candles:
            await repository.save(candle)


async def test_on_candle_closed_creates_and_broadcasts_a_signal_on_15m_close(session_factory) -> None:
    await _seed_candles(session_factory, _bullish_setup_candles(Timeframe.H4))
    await _seed_candles(session_factory, _bullish_setup_candles(Timeframe.H1))

    manager = _RecordingConnectionManager()
    service = SignalService(BroadcastService(manager), session_factory)

    tap_candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 2, tzinfo=UTC),
        close_time=datetime(2026, 1, 2, 0, 15, tzinfo=UTC),
        open=97.5,
        high=99.0,
        low=97.0,
        close=98.0,
        volume=1.0,
    )
    await _seed_candles(session_factory, [tap_candle])

    await service.on_candle_closed(tap_candle)

    assert len(manager.broadcasted) == 1
    assert manager.broadcasted[0].direction == Direction.BULLISH

    async with session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)
    assert len(open_signals) == 1


async def test_on_candle_closed_does_not_duplicate_a_still_open_signal(session_factory) -> None:
    await _seed_candles(session_factory, _bullish_setup_candles(Timeframe.H4))
    await _seed_candles(session_factory, _bullish_setup_candles(Timeframe.H1))

    manager = _RecordingConnectionManager()
    service = SignalService(BroadcastService(manager), session_factory)

    tap_candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 2, tzinfo=UTC),
        close_time=datetime(2026, 1, 2, 0, 15, tzinfo=UTC),
        open=97.5,
        high=99.0,
        low=97.0,
        close=98.0,
        volume=1.0,
    )
    await _seed_candles(session_factory, [tap_candle])
    await service.on_candle_closed(tap_candle)

    # A later 15m close that would independently re-derive the exact same
    # still-open setup (same bias/structure, unchanged 1H/4H data) must not
    # be saved as a second signal.
    second_close = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 2, 0, 15, tzinfo=UTC),
        close_time=datetime(2026, 1, 2, 0, 30, tzinfo=UTC),
        open=98.0,
        high=99.0,
        low=97.5,
        close=98.0,
        volume=1.0,
    )
    await _seed_candles(session_factory, [second_close])
    await service.on_candle_closed(second_close)

    assert len(manager.broadcasted) == 1

    async with session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)
    assert len(open_signals) == 1


async def test_on_candle_closed_ignores_non_15m_candles(session_factory) -> None:
    manager = _RecordingConnectionManager()
    service = SignalService(BroadcastService(manager), session_factory)

    hourly_candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.H1,
        open_time=datetime(2026, 1, 2, tzinfo=UTC),
        close_time=datetime(2026, 1, 2, 1, 0, tzinfo=UTC),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1.0,
    )

    await service.on_candle_closed(hourly_candle)

    assert manager.broadcasted == []
