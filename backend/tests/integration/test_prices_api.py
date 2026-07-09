from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_feed_service, get_tradingview_feed_service
from app.api.routers import prices
from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle, Tick
from app.storage.database import Base, get_session
from app.storage.models import TradingViewCandleORM
from app.storage.repositories.candle_repository import CandleRepository


class _FakeFeedService:
    """Only exposes what the prices router actually calls — a real
    FeedService owns a live provider connection this test has no need for."""

    def __init__(self, ticks: dict[Symbol, Tick]) -> None:
        self._ticks = ticks

    def latest_price(self, symbol: Symbol) -> Tick | None:
        return self._ticks.get(symbol)


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def _client(
    session_factory: async_sessionmaker[AsyncSession],
    ticks: dict[Symbol, Tick],
    tradingview_feed_service: _FakeFeedService | None = None,
) -> AsyncClient:
    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(prices.router)
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_feed_service] = lambda: _FakeFeedService(ticks)
    app.dependency_overrides[get_tradingview_feed_service] = lambda: tradingview_feed_service

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_1m_candle(session_factory: async_sessionmaker[AsyncSession], symbol: Symbol, close: float) -> None:
    async with session_factory() as session:
        await CandleRepository(session).save(
            Candle(
                symbol=symbol,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=0.0,
            )
        )


async def test_prefers_the_live_tick_over_the_candle_fallback(session_factory) -> None:
    await _seed_1m_candle(session_factory, Symbol.XAUUSD, close=2350.0)
    tick = Tick(symbol=Symbol.XAUUSD, price=2400.0, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC))

    async with _client(session_factory, {Symbol.XAUUSD: tick}) as client:
        response = await client.get("/prices")

    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "XAUUSD"
    assert body[0]["price"] == 2400.0


async def test_falls_back_to_the_latest_1m_candle_when_no_live_tick_yet(session_factory) -> None:
    # A pair like AUDUSD can have candles (from backfill or earlier ticks)
    # without ever having pushed a live tick yet this session.
    await _seed_1m_candle(session_factory, Symbol.AUDUSD, close=0.69109)

    async with _client(session_factory, {}) as client:
        response = await client.get("/prices")

    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "AUDUSD"
    assert body[0]["price"] == 0.69109


async def test_omits_a_symbol_with_neither_a_live_tick_nor_a_stored_candle(session_factory) -> None:
    async with _client(session_factory, {}) as client:
        response = await client.get("/prices")

    assert response.json() == []


async def test_source_tradingview_returns_503_when_the_pipeline_is_not_enabled(session_factory) -> None:
    async with _client(session_factory, {}, tradingview_feed_service=None) as client:
        response = await client.get("/prices", params={"source": "tradingview"})

    assert response.status_code == 503


async def test_source_tradingview_reads_its_own_live_tick_and_candle_table(session_factory) -> None:
    async with session_factory() as session:
        await CandleRepository(session, model=TradingViewCandleORM).save(
            Candle(
                symbol=Symbol.AUDUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
                open=0.69,
                high=0.69,
                low=0.69,
                close=0.69,
                volume=0.0,
            )
        )
    # Also seed the default (Twelve Data) table with a different price, to
    # prove the tradingview response isn't accidentally reading it instead.
    await _seed_1m_candle(session_factory, Symbol.AUDUSD, close=999.0)

    tradingview_service = _FakeFeedService({})
    async with _client(session_factory, {}, tradingview_feed_service=tradingview_service) as client:
        response = await client.get("/prices", params={"source": "tradingview"})

    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "AUDUSD"
    assert body[0]["price"] == 0.69
