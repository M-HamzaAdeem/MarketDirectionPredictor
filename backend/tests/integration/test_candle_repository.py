from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.storage.database import Base
from app.storage.models import TradingViewCandleORM
from app.storage.repositories.candle_repository import CandleRepository


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


async def test_get_recent_returns_domain_candles_not_orm_rows(session_factory) -> None:
    async with session_factory() as session:
        await CandleRepository(session).save(
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=0.0,
            )
        )

    async with session_factory() as session:
        candles = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1)

    assert len(candles) == 1
    assert isinstance(candles[0], Candle)
    assert candles[0].symbol == Symbol.XAUUSD
    assert candles[0].close == 100.5


async def test_get_latest_returns_the_most_recent_domain_candle(session_factory) -> None:
    async with session_factory() as session:
        repository = CandleRepository(session)
        await repository.save(
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=0.0,
            )
        )
        await repository.save(
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 0, 2, tzinfo=UTC),
                open=100.5,
                high=102.0,
                low=100.0,
                close=101.5,
                volume=0.0,
            )
        )

    async with session_factory() as session:
        latest = await CandleRepository(session).get_latest(Symbol.XAUUSD, Timeframe.M1)

    assert isinstance(latest, Candle)
    assert latest.close == 101.5


async def test_save_is_idempotent_on_a_duplicate_symbol_timeframe_open_time(session_factory) -> None:
    # A live provider re-delivering the same candle boundary (e.g. around a
    # reconnect) must not raise or skip the caller's downstream handling —
    # see the idempotent-live-candle-save decision.
    candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M1,
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=0.0,
    )

    async with session_factory() as session:
        repository = CandleRepository(session)
        await repository.save(candle)
        await repository.save(candle)  # must not raise

    async with session_factory() as session:
        candles = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1)
    assert len(candles) == 1


async def test_get_latest_returns_none_when_no_candles_exist(session_factory) -> None:
    async with session_factory() as session:
        latest = await CandleRepository(session).get_latest(Symbol.XAUUSD, Timeframe.M1)
    assert latest is None


def _candle(open_time: datetime, close: float) -> Candle:
    return Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=0.0,
    )


async def test_save_many_if_missing_is_a_noop_for_an_empty_list(session_factory) -> None:
    async with session_factory() as session:
        await CandleRepository(session).save_many_if_missing([])
        candles = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1)
    assert candles == []


async def test_save_many_if_missing_inserts_new_and_skips_duplicate_rows(session_factory) -> None:
    first = _candle(datetime(2026, 1, 1, 0, 0, tzinfo=UTC), close=100.0)
    second = _candle(datetime(2026, 1, 1, 0, 1, tzinfo=UTC), close=101.0)

    async with session_factory() as session:
        await CandleRepository(session).save_many_if_missing([first])

    async with session_factory() as session:
        # Overlaps with `first` (same symbol/timeframe/open_time) plus one
        # genuinely new row — the duplicate must be silently skipped, not
        # raise an IntegrityError, and the new row must still land.
        await CandleRepository(session).save_many_if_missing([first, second])

    async with session_factory() as session:
        candles = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1, limit=10)
    assert [c.close for c in candles] == [100.0, 101.0]


async def test_model_param_isolates_writes_and_reads_to_the_alternate_table(session_factory) -> None:
    # The whole TradingView dual-source feature depends on this: a save()
    # against model=TradingViewCandleORM must be invisible to the default
    # (Twelve Data) CandleORM table, and vice versa -- never a shared table
    # filtered by a column, an actually separate table.
    candle = _candle(datetime(2026, 1, 1, tzinfo=UTC), close=100.0)

    async with session_factory() as session:
        await CandleRepository(session, model=TradingViewCandleORM).save(candle)

    async with session_factory() as session:
        default_table_candles = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1)
        tradingview_table_candles = await CandleRepository(session, model=TradingViewCandleORM).get_recent(
            Symbol.XAUUSD, Timeframe.M1
        )

    assert default_table_candles == []
    assert len(tradingview_table_candles) == 1
    assert tradingview_table_candles[0].close == 100.0
