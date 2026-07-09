from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers import predictions
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
    app.include_router(predictions.router)
    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield _ApiFixture(client=async_client, session_factory=session_factory)

    await engine.dispose()


async def _seed_candles(session_factory: async_sessionmaker[AsyncSession], closes: list[float]) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with session_factory() as session:
        repository = CandleRepository(session)
        for i, close in enumerate(closes):
            await repository.save(
                Candle(
                    symbol=Symbol.XAUUSD,
                    timeframe=Timeframe.M1,
                    open_time=base + timedelta(minutes=i),
                    close_time=base + timedelta(minutes=i + 1),
                    open=close,
                    high=close + 0.5,
                    low=close - 0.5,
                    close=close,
                    volume=0.0,
                )
            )


async def test_latest_prediction_computes_and_logs_a_new_prediction(api: _ApiFixture) -> None:
    await _seed_candles(api.session_factory, [100.0 + i for i in range(5)])

    response = await api.client.get("/predictions/XAUUSD/1m/latest", params={"source": "twelve_data"})

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "XAUUSD"
    assert body["timeframe"] == "1m"
    assert body["direction"] in ("bullish", "bearish", "neutral")
    assert 0.0 <= body["confidence"] <= 100.0
    assert body["price"] == 104.0
    assert body["reason"]


async def test_latest_prediction_returns_404_when_no_candles_exist(api: _ApiFixture) -> None:
    response = await api.client.get("/predictions/EURUSD/5m/latest")
    assert response.status_code == 404


async def test_latest_prediction_is_readable_from_history_afterwards(api: _ApiFixture) -> None:
    await _seed_candles(api.session_factory, [100.0 + i for i in range(5)])

    latest_response = await api.client.get("/predictions/XAUUSD/1m/latest", params={"source": "twelve_data"})
    assert latest_response.status_code == 200

    history_response = await api.client.get("/predictions/XAUUSD/1m/history", params={"source": "twelve_data"})
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["price"] == latest_response.json()["price"]


async def test_history_endpoint_rejects_unknown_symbol(api: _ApiFixture) -> None:
    response = await api.client.get("/predictions/BTCUSD/1m/history")
    assert response.status_code == 422


async def test_repeated_calls_to_latest_append_rather_than_overwrite(api: _ApiFixture) -> None:
    await _seed_candles(api.session_factory, [100.0 + i for i in range(5)])

    await api.client.get("/predictions/XAUUSD/1m/latest", params={"source": "twelve_data"})
    await api.client.get("/predictions/XAUUSD/1m/latest", params={"source": "twelve_data"})

    history_response = await api.client.get("/predictions/XAUUSD/1m/history", params={"source": "twelve_data"})
    assert len(history_response.json()) == 2


async def test_source_defaults_to_tradingview_and_stays_isolated_from_twelve_data(api: _ApiFixture) -> None:
    # Only the Twelve Data table has candles -- the TradingView table is
    # empty, so its "latest" (including via the implicit default, no
    # ?source= at all) must 404 rather than silently borrowing the other
    # source's candles.
    await _seed_candles(api.session_factory, [100.0 + i for i in range(5)])

    no_tradingview_candles_yet = await api.client.get("/predictions/XAUUSD/1m/latest")  # no ?source= at all
    assert no_tradingview_candles_yet.status_code == 404

    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with api.session_factory() as session:
        repository = CandleRepository(session, model=TradingViewCandleORM)
        for i in range(5):
            await repository.save(
                Candle(
                    symbol=Symbol.XAUUSD,
                    timeframe=Timeframe.M1,
                    open_time=base + timedelta(minutes=i),
                    close_time=base + timedelta(minutes=i + 1),
                    open=1.0 + i,
                    high=1.5 + i,
                    low=0.5 + i,
                    close=1.0 + i,
                    volume=0.0,
                )
            )

    default_response = await api.client.get("/predictions/XAUUSD/1m/latest")  # no ?source= -> tradingview
    assert default_response.status_code == 200
    assert default_response.json()["price"] == 5.0  # TradingView's own candles, not Twelve Data's 104.0

    # Logged to the TradingView prediction table only -- Twelve Data's
    # history (still just the one entry seeded above) is unaffected.
    twelve_data_history = await api.client.get("/predictions/XAUUSD/1m/history", params={"source": "twelve_data"})
    default_history = await api.client.get("/predictions/XAUUSD/1m/history")  # no ?source= -> tradingview
    assert len(twelve_data_history.json()) == 0  # this test never called .../latest with source=twelve_data
    assert len(default_history.json()) == 1
