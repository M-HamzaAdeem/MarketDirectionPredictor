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

    await service.stop()
