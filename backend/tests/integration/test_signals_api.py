from datetime import UTC, datetime
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers import signals
from app.core.constants import Direction, Symbol, Timeframe
from app.prediction.signal import Signal, SignalStatus
from app.storage.database import Base, get_session
from app.storage.repositories.signal_repository import SignalRepository


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
    app.include_router(signals.router)
    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield _ApiFixture(client=async_client, session_factory=session_factory)

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
        "reason": "test reason",
        "details": {"poi_type": "order_block"},
        "opened_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


async def test_get_open_signals_returns_a_persisted_open_signal_with_its_id(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    response = await api.client.get("/signals/open")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == saved.id
    assert body[0]["status"] == "open"
    assert body[0]["risk_reward"] == 3.0
    assert body[0]["details"] == {"poi_type": "order_block"}


async def test_get_open_signals_filters_by_symbol(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        repository = SignalRepository(session)
        await repository.save(_signal(symbol=Symbol.XAUUSD))
        await repository.save(_signal(symbol=Symbol.EURUSD))

    response = await api.client.get("/signals/open", params={"symbol": "EURUSD"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "EURUSD"


async def test_get_signal_history_includes_resolved_signals(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        saved = await SignalRepository(session).save(_signal())
    async with api.session_factory() as session:
        await SignalRepository(session).update_outcome(
            saved.id, SignalStatus.WIN, datetime(2026, 1, 1, 5, tzinfo=UTC), realized_rr=3.0
        )

    response = await api.client.get("/signals/XAUUSD/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "win"
    assert body[0]["realized_rr"] == 3.0


async def test_get_signal_history_rejects_an_unknown_symbol(api: _ApiFixture) -> None:
    response = await api.client.get("/signals/BTCUSD/history")
    assert response.status_code == 422
