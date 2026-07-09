from datetime import UTC, datetime
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers import candles
from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.storage.database import Base, get_session
from app.storage.models import TradingViewCandleORM
from app.storage.repositories.candle_repository import CandleRepository


class _ApiFixture(NamedTuple):
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]


@pytest.fixture
async def api(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(candles.router)
    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield _ApiFixture(client=async_client, session_factory=session_factory)

    await engine.dispose()


async def _seed_candle(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await CandleRepository(session).save(
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
                open=2350.0,
                high=2355.0,
                low=2348.0,
                close=2352.0,
                volume=0.0,
            )
        )


async def test_get_candles_returns_persisted_candles(api: _ApiFixture) -> None:
    await _seed_candle(api.session_factory)

    response = await api.client.get("/candles/XAUUSD/1m")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["open"] == 2350.0
    assert body[0]["close"] == 2352.0


async def test_get_candles_returns_empty_list_when_none_stored(api: _ApiFixture) -> None:
    response = await api.client.get("/candles/EURUSD/5m")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_candles_rejects_unknown_timeframe(api: _ApiFixture) -> None:
    response = await api.client.get("/candles/XAUUSD/2m")

    assert response.status_code == 422


async def test_get_candles_source_param_reads_the_tradingview_table_not_the_default(api: _ApiFixture) -> None:
    await _seed_candle(api.session_factory)  # only in the default (Twelve Data) table

    async with api.session_factory() as session:
        await CandleRepository(session, model=TradingViewCandleORM).save(
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M1,
                open_time=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
                close_time=datetime(2026, 1, 1, 11, 1, tzinfo=UTC),
                open=1.0,
                high=1.5,
                low=0.5,
                close=1.2,
                volume=0.0,
            )
        )

    default_response = await api.client.get("/candles/XAUUSD/1m")
    tradingview_response = await api.client.get("/candles/XAUUSD/1m", params={"source": "tradingview"})

    assert [c["close"] for c in default_response.json()] == [2352.0]
    assert [c["close"] for c in tradingview_response.json()] == [1.2]
