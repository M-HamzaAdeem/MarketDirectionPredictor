from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import Direction, Symbol, Timeframe
from app.prediction.signal import Signal, SignalStatus
from app.storage.database import Base
from app.storage.models import TradingViewSignalORM
from app.storage.repositories.signal_repository import SignalRepository


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def _signal(**overrides: object) -> Signal:
    defaults: dict[str, object] = {
        "symbol": Symbol.XAUUSD,
        "entry_timeframe": Timeframe.M15,
        "direction": Direction.BULLISH,
        "entry": 2350.0,
        "stop": 2345.0,
        "target": 2365.0,
        "risk_reward": 3.0,
        "reason": "sweep + CHoCH + OTE/OB confluence",
        "details": {"poi_type": "order_block", "ote_low": 2348.0, "ote_high": 2351.0},
        "opened_at": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


async def test_save_persists_and_returns_a_signal_with_an_id(session_factory) -> None:
    async with session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    assert saved.id is not None
    assert saved.status == SignalStatus.OPEN
    assert saved.details == {"poi_type": "order_block", "ote_low": 2348.0, "ote_high": 2351.0}


async def test_save_persists_created_at_distinctly_from_opened_at(session_factory) -> None:
    created_at = datetime(2026, 1, 1, 15, 0, tzinfo=UTC)  # hours after the 10:00 opened_at default

    async with session_factory() as session:
        saved = await SignalRepository(session).save(_signal(created_at=created_at))

    assert saved.created_at == created_at
    assert saved.opened_at != saved.created_at

    async with session_factory() as session:
        recent = await SignalRepository(session).get_recent(Symbol.XAUUSD)
    assert recent[0].created_at == created_at


async def test_get_open_returns_only_open_signals_for_the_requested_symbol(session_factory) -> None:
    async with session_factory() as session:
        repository = SignalRepository(session)
        await repository.save(_signal(symbol=Symbol.XAUUSD))
        await repository.save(_signal(symbol=Symbol.EURUSD))

    async with session_factory() as session:
        open_xauusd = await SignalRepository(session).get_open(Symbol.XAUUSD)

    assert len(open_xauusd) == 1
    assert open_xauusd[0].symbol == Symbol.XAUUSD


async def test_update_outcome_resolves_a_signal_to_win(session_factory) -> None:
    async with session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    closed_at = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)
    async with session_factory() as session:
        await SignalRepository(session).update_outcome(saved.id, SignalStatus.WIN, closed_at, realized_rr=3.0)

    async with session_factory() as session:
        recent = await SignalRepository(session).get_recent(Symbol.XAUUSD)

    assert len(recent) == 1
    assert recent[0].status == SignalStatus.WIN
    assert recent[0].closed_at == closed_at
    assert recent[0].realized_rr == 3.0


async def test_resolved_signals_are_excluded_from_get_open(session_factory) -> None:
    async with session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    async with session_factory() as session:
        await SignalRepository(session).update_outcome(
            saved.id, SignalStatus.LOSS, datetime.now(UTC), realized_rr=-1.0
        )

    async with session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)

    assert open_signals == []


async def test_get_recent_returns_ascending_order_by_opened_at(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        repository = SignalRepository(session)
        await repository.save(_signal(opened_at=base + timedelta(hours=2)))
        await repository.save(_signal(opened_at=base))
        await repository.save(_signal(opened_at=base + timedelta(hours=1)))

    async with session_factory() as session:
        recent = await SignalRepository(session).get_recent(Symbol.XAUUSD)

    assert [s.opened_at for s in recent] == [base, base + timedelta(hours=1), base + timedelta(hours=2)]


async def test_model_param_isolates_writes_and_reads_to_the_alternate_table(session_factory) -> None:
    # The whole TradingView dual-source feature depends on this: a save()
    # against model=TradingViewSignalORM must be invisible to the default
    # (Twelve Data) SignalORM table, and vice versa -- never a shared table
    # filtered by a column, an actually separate table.
    async with session_factory() as session:
        await SignalRepository(session, model=TradingViewSignalORM).save(_signal())

    async with session_factory() as session:
        default_table_open = await SignalRepository(session).get_open(Symbol.XAUUSD)
        tradingview_table_open = await SignalRepository(session, model=TradingViewSignalORM).get_open(
            Symbol.XAUUSD
        )

    assert default_table_open == []
    assert len(tradingview_table_open) == 1
    assert tradingview_table_open[0].symbol == Symbol.XAUUSD
