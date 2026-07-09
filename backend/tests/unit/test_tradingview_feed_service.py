import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.constants import DataSource, FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle
from app.services.broadcast_service import BroadcastService
from app.services.connection_manager import ConnectionManager
from app.services.tradingview_feed_service import TradingViewFeedService, _ordered_timeframes
from app.storage.database import Base
from app.storage.models import TradingViewCandleORM
from app.storage.repositories.candle_repository import CandleRepository

_real_sleep = asyncio.sleep


class _FakeTradingViewClient:
    def __init__(self, responses: dict[tuple[Symbol, Timeframe], list[Candle] | Exception] | None = None) -> None:
        self._responses: dict[tuple[Symbol, Timeframe], list[Candle] | Exception] = responses or {}
        self.fetch_calls: list[tuple[Symbol, Timeframe, int]] = []

    def set_response(self, symbol: Symbol, timeframe: Timeframe, response: list[Candle] | Exception) -> None:
        self._responses[(symbol, timeframe)] = response

    async def fetch_candles(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        self.fetch_calls.append((symbol, timeframe, count))
        response = self._responses.get((symbol, timeframe), [])
        if isinstance(response, Exception):
            raise response
        return response


class _RecordingHandler:
    def __init__(self) -> None:
        self.candles: list[Candle] = []

    async def on_candle_closed(self, candle: Candle) -> None:
        self.candles.append(candle)


class _FakeSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)
        await _real_sleep(0)


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"symbols": [Symbol.XAUUSD], "timeframes": [Timeframe.M15]}
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _broadcaster() -> BroadcastService:
    return BroadcastService(ConnectionManager(), source=DataSource.TRADINGVIEW)


def _candle(
    open_time: datetime, close: float, symbol: Symbol = Symbol.XAUUSD, timeframe: Timeframe = Timeframe.M15
) -> Candle:
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=close,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=0.0,
    )


async def _wait_until(predicate, timeout: float = 2.0, interval: float = 0.01) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met before timeout")
        await _real_sleep(interval)


def test_ordered_timeframes_sorts_coarsest_to_finest() -> None:
    assert _ordered_timeframes([Timeframe.M15, Timeframe.M1, Timeframe.H4, Timeframe.H1]) == [
        Timeframe.H4,
        Timeframe.H1,
        Timeframe.M15,
        Timeframe.M1,
    ]


def test_ordered_timeframes_filters_to_only_configured_ones() -> None:
    assert _ordered_timeframes([Timeframe.M15]) == [Timeframe.M15]


async def test_backfill_persists_closed_candles_and_excludes_the_forming_bar(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [_candle(base + timedelta(minutes=15 * i), close=100.0 + i) for i in range(5)]
    client = _FakeTradingViewClient({(Symbol.XAUUSD, Timeframe.M15): candles})
    service = TradingViewFeedService(client, _settings(), _broadcaster(), session_factory, [], poll_interval_seconds=999)

    await service.backfill()

    async with session_factory() as session:
        stored = await CandleRepository(session, model=TradingViewCandleORM).get_recent(
            Symbol.XAUUSD, Timeframe.M15, limit=10
        )
    assert len(stored) == 4  # 5 fetched, last one (forming) excluded


async def test_poll_one_ignores_a_still_forming_only_response(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    client = _FakeTradingViewClient({(Symbol.XAUUSD, Timeframe.M15): [_candle(base, close=100.0)]})
    handler = _RecordingHandler()
    service = TradingViewFeedService(
        client, _settings(), _broadcaster(), session_factory, [handler], poll_interval_seconds=999
    )

    await service._poll_one(Symbol.XAUUSD, Timeframe.M15)

    assert handler.candles == []  # the only bar returned is the forming one -- no closed candle yet
    assert service.latest_price(Symbol.XAUUSD) is not None  # but the forming bar still updates the live price


async def test_poll_one_triggers_handlers_only_for_genuinely_new_closed_candles(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    bars = [
        _candle(base, close=100.0),
        _candle(base + timedelta(minutes=15), close=101.0),
        _candle(base + timedelta(minutes=30), close=102.0),  # forming
    ]
    client = _FakeTradingViewClient({(Symbol.XAUUSD, Timeframe.M15): bars})
    handler = _RecordingHandler()
    service = TradingViewFeedService(
        client, _settings(), _broadcaster(), session_factory, [handler], poll_interval_seconds=999
    )

    await service._poll_one(Symbol.XAUUSD, Timeframe.M15)
    assert [c.close for c in handler.candles] == [100.0, 101.0]  # both closed bars, ascending, forming bar excluded

    # Same bars returned again -- nothing new, handler must not fire again.
    await service._poll_one(Symbol.XAUUSD, Timeframe.M15)
    assert len(handler.candles) == 2


async def test_poll_one_processes_a_bar_that_newly_closed_since_the_last_poll(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    client = _FakeTradingViewClient({(Symbol.XAUUSD, Timeframe.M15): [_candle(base, close=100.0)]})
    handler = _RecordingHandler()
    service = TradingViewFeedService(
        client, _settings(), _broadcaster(), session_factory, [handler], poll_interval_seconds=999
    )

    await service._poll_one(Symbol.XAUUSD, Timeframe.M15)
    assert handler.candles == []  # only bar fetched so far is still forming

    # The previously-forming bar has now closed, and a new one is forming.
    client.set_response(
        Symbol.XAUUSD,
        Timeframe.M15,
        [_candle(base, close=100.0), _candle(base + timedelta(minutes=15), close=101.0)],
    )
    await service._poll_one(Symbol.XAUUSD, Timeframe.M15)

    assert len(handler.candles) == 1
    assert handler.candles[0].close == 100.0


async def test_poll_cycle_processes_timeframes_coarsest_to_finest(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    client = _FakeTradingViewClient(
        {
            (Symbol.XAUUSD, Timeframe.H4): [
                _candle(base, close=1.0, timeframe=Timeframe.H4),
                _candle(base + timedelta(hours=4), close=1.1, timeframe=Timeframe.H4),
            ],
            (Symbol.XAUUSD, Timeframe.H1): [
                _candle(base, close=2.0, timeframe=Timeframe.H1),
                _candle(base + timedelta(hours=1), close=2.1, timeframe=Timeframe.H1),
            ],
            (Symbol.XAUUSD, Timeframe.M15): [
                _candle(base, close=3.0, timeframe=Timeframe.M15),
                _candle(base + timedelta(minutes=15), close=3.1, timeframe=Timeframe.M15),
            ],
        }
    )
    handler = _RecordingHandler()
    # Deliberately configured out of order -- the service must still poll coarsest-first.
    settings = _settings(timeframes=[Timeframe.M15, Timeframe.H1, Timeframe.H4])
    service = TradingViewFeedService(
        client, settings, _broadcaster(), session_factory, [handler], poll_interval_seconds=0.01
    )

    await service.start()
    await _wait_until(lambda: len(handler.candles) == 3)
    await service.stop()

    assert [c.timeframe for c in handler.candles] == [Timeframe.H4, Timeframe.H1, Timeframe.M15]


async def test_a_failing_poll_cycle_surfaces_disconnected_and_backs_off_then_recovers(
    session_factory, monkeypatch
) -> None:
    fake_sleep = _FakeSleep()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    base = datetime(2026, 1, 1, tzinfo=UTC)
    client = _FakeTradingViewClient({(Symbol.XAUUSD, Timeframe.M15): RuntimeError("simulated failure")})
    service = TradingViewFeedService(client, _settings(), _broadcaster(), session_factory, [], poll_interval_seconds=999)

    await service.start()
    await _wait_until(lambda: service.status == FeedStatus.DISCONNECTED)
    assert fake_sleep.delays[:1] == [1.0]  # initial backoff delay

    client.set_response(
        Symbol.XAUUSD, Timeframe.M15, [_candle(base, close=100.0), _candle(base + timedelta(minutes=15), close=101.0)]
    )
    await _wait_until(lambda: service.status == FeedStatus.LIVE)

    await service.stop()
