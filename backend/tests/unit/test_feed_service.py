import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.services.feed_service import FeedService
from app.storage.database import Base
from app.storage.repositories.candle_repository import CandleRepository

_real_sleep = asyncio.sleep


class _RecordingBroadcaster:
    def __init__(self) -> None:
        self.prices: list[Tick] = []
        self.statuses: list[FeedStatus] = []

    async def broadcast_price(self, tick: Tick) -> None:
        self.prices.append(tick)

    async def broadcast_feed_status(self, status: FeedStatus) -> None:
        self.statuses.append(status)


class _RecordingHandler:
    def __init__(self) -> None:
        self.candles: list[Candle] = []

    async def on_candle_closed(self, candle: Candle) -> None:
        self.candles.append(candle)


class _ScriptedProvider(MarketDataProvider):
    """Each entry in `attempts` is one `stream_ticks` call: `None` raises
    immediately (a failed attempt), a list yields those ticks and then hangs
    (so the test controls exactly when the attempt "ends" via cancellation)."""

    def __init__(self, attempts: list[list[Tick] | None]) -> None:
        self._attempts = list(attempts)
        self.connect_count = 0
        self.disconnect_count = 0

    @property
    def nominal_status(self) -> FeedStatus:
        return FeedStatus.MOCK

    async def connect(self) -> None:
        self.connect_count += 1

    async def disconnect(self) -> None:
        self.disconnect_count += 1

    async def stream_ticks(self, symbols: list[Symbol]):
        attempt = self._attempts.pop(0)
        if attempt is None:
            raise RuntimeError("simulated provider failure")
        for tick in attempt:
            yield tick
        await asyncio.Event().wait()

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        return []


class _HistoryProvider(MarketDataProvider):
    """A provider that only serves fetch_history — backfill tests don't
    touch connect/disconnect/stream_ticks. `responses` maps
    (symbol, timeframe) to either a candle list or an exception to raise."""

    def __init__(self, responses: dict[tuple[Symbol, Timeframe], list[Candle] | Exception]) -> None:
        self._responses = responses
        self.fetch_calls: list[tuple[Symbol, Timeframe, int]] = []

    @property
    def nominal_status(self) -> FeedStatus:
        return FeedStatus.LIVE

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def stream_ticks(self, symbols: list[Symbol]):
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        self.fetch_calls.append((symbol, timeframe, count))
        response = self._responses.get((symbol, timeframe), [])
        if isinstance(response, Exception):
            raise response
        return response


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


def _settings() -> Settings:
    return Settings(symbols=[Symbol.XAUUSD], timeframes=[Timeframe.M1])


def _tick(price: float, ts: datetime) -> Tick:
    return Tick(symbol=Symbol.XAUUSD, price=price, timestamp=ts, volume=1.0)


async def _wait_until(predicate: Callable[[], bool], timeout: float = 2.0, interval: float = 0.01) -> None:
    """Polls with real (unpatched) sleeps until `predicate()` is true.

    Needed because the background feed task's persistence step goes through
    aiosqlite's real worker thread — plain `asyncio.sleep(0)` cooperative
    yields aren't enough to guarantee that thread has posted its result back
    before the test's assertions run.
    """
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met before timeout")
        await _real_sleep(interval)


async def test_start_connects_provider_and_broadcasts_nominal_status(session_factory) -> None:
    # The single scripted attempt fails, but the assertions run before the
    # event loop ever gives the background task a chance to execute (no
    # `await` happens between service.start() and the asserts below), so
    # they only observe start()'s own explicit connect() + status broadcast.
    provider = _ScriptedProvider([None])
    broadcaster = _RecordingBroadcaster()
    service = FeedService(provider, _settings(), broadcaster, session_factory, [])

    await service.start()

    assert provider.connect_count == 1
    assert broadcaster.statuses == [FeedStatus.MOCK]

    await service.stop()


async def test_ticks_flow_through_to_handlers_and_persistence(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    ticks = [
        _tick(100.0, base),
        _tick(101.0, base + timedelta(seconds=30)),
        _tick(102.0, base + timedelta(minutes=1)),  # crosses into the next M1 bucket
    ]
    provider = _ScriptedProvider([ticks])
    broadcaster = _RecordingBroadcaster()
    handler = _RecordingHandler()
    service = FeedService(provider, _settings(), broadcaster, session_factory, [handler])

    await service.start()
    await _wait_until(lambda: len(handler.candles) == 1)

    assert service.latest_price(Symbol.XAUUSD) == ticks[-1]
    assert len(broadcaster.prices) == 3
    assert handler.candles[0].close == 101.0  # the closed minute-0 candle

    async with session_factory() as session:
        persisted = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1, limit=10)
    assert len(persisted) == 1

    await service.stop()


async def test_stream_failure_reconnects_with_backoff_and_recovers(session_factory, monkeypatch) -> None:
    fake_sleep = _FakeSleep()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    tick = _tick(100.0, datetime(2026, 1, 1, tzinfo=UTC))
    provider = _ScriptedProvider([None, None, [tick]])
    broadcaster = _RecordingBroadcaster()
    service = FeedService(provider, _settings(), broadcaster, session_factory, [])

    await service.start()
    await _wait_until(lambda: service.status == FeedStatus.MOCK and service.latest_price(Symbol.XAUUSD) is not None)

    # start() connects once; each of the two failed attempts reconnects
    # before retrying, so three connects total and two disconnects.
    assert provider.connect_count == 3
    assert provider.disconnect_count == 2
    assert fake_sleep.delays == [1.0, 2.0]  # backoff doubles each failure
    assert broadcaster.statuses == [FeedStatus.MOCK, FeedStatus.DISCONNECTED, FeedStatus.MOCK]
    assert service.latest_price(Symbol.XAUUSD) == tick

    await service.stop()


async def test_backoff_delay_is_capped_at_the_maximum(session_factory, monkeypatch) -> None:
    fake_sleep = _FakeSleep()
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    provider = _ScriptedProvider([None, None, None, None, None, None, []])
    broadcaster = _RecordingBroadcaster()
    service = FeedService(provider, _settings(), broadcaster, session_factory, [])

    await service.start()
    await _wait_until(lambda: len(fake_sleep.delays) == 6)

    assert fake_sleep.delays == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]


def _history_candle(close: float, open_time: datetime, symbol: Symbol = Symbol.XAUUSD) -> Candle:
    return Candle(
        symbol=symbol,
        timeframe=Timeframe.M15,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=close,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=0.0,
    )


async def test_backfill_persists_fetched_history_when_store_is_empty(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [_history_candle(100.0 + i, base + timedelta(minutes=15 * i)) for i in range(5)]
    provider = _HistoryProvider({(Symbol.XAUUSD, Timeframe.M15): candles})
    settings = Settings(symbols=[Symbol.XAUUSD], timeframes=[Timeframe.M15])
    service = FeedService(provider, settings, _RecordingBroadcaster(), session_factory, [])

    await service.backfill()

    async with session_factory() as session:
        stored = await CandleRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M15, limit=10)
    assert len(stored) == 5
    assert provider.fetch_calls == [(Symbol.XAUUSD, Timeframe.M15, 100)]


async def test_backfill_skips_fetch_when_already_sufficient(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        repository = CandleRepository(session)
        for i in range(100):
            await repository.save_many_if_missing([_history_candle(100.0 + i, base + timedelta(minutes=15 * i))])

    provider = _HistoryProvider({})  # would raise KeyError-shaped issues if actually called
    settings = Settings(symbols=[Symbol.XAUUSD], timeframes=[Timeframe.M15])
    service = FeedService(provider, settings, _RecordingBroadcaster(), session_factory, [])

    await service.backfill()

    assert provider.fetch_calls == []


async def test_backfill_propagates_an_unexpected_error_instead_of_swallowing_it(session_factory) -> None:
    # AttributeError stands in for a genuine coding bug — outside the
    # narrowed set of expected external-failure types (httpx.HTTPError,
    # RuntimeError, KeyError, ValueError, SQLAlchemyError), so it must not
    # be silently absorbed as if it were a routine backfill failure.
    provider = _HistoryProvider({(Symbol.XAUUSD, Timeframe.M15): AttributeError("simulated coding bug")})
    settings = Settings(symbols=[Symbol.XAUUSD], timeframes=[Timeframe.M15])
    service = FeedService(provider, settings, _RecordingBroadcaster(), session_factory, [])

    with pytest.raises(AttributeError):
        await service.backfill()


async def test_backfill_one_symbol_failing_does_not_abort_the_rest(session_factory) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    good_candles = [_history_candle(100.0, base, symbol=Symbol.EURUSD)]
    provider = _HistoryProvider(
        {
            (Symbol.XAUUSD, Timeframe.M15): RuntimeError("simulated fetch failure"),
            (Symbol.EURUSD, Timeframe.M15): good_candles,
        }
    )
    settings = Settings(symbols=[Symbol.XAUUSD, Symbol.EURUSD], timeframes=[Timeframe.M15])
    service = FeedService(provider, settings, _RecordingBroadcaster(), session_factory, [])

    await service.backfill()

    async with session_factory() as session:
        repository = CandleRepository(session)
        assert await repository.get_recent(Symbol.XAUUSD, Timeframe.M15, limit=10) == []
        assert len(await repository.get_recent(Symbol.EURUSD, Timeframe.M15, limit=10)) == 1

    await service.stop()
