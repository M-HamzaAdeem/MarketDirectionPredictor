from datetime import UTC, datetime
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers import backtests
from app.backtesting.models import BacktestKind, BacktestRun
from app.core.constants import Symbol, Timeframe
from app.storage.database import Base, get_session
from app.storage.repositories.backtest_run_repository import BacktestRunRepository


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
    app.include_router(backtests.router)
    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield _ApiFixture(client=async_client, session_factory=session_factory)

    await engine.dispose()


def _run(**overrides: object) -> BacktestRun:
    defaults: dict[str, object] = {
        "kind": BacktestKind.SIGNAL,
        "symbol": Symbol.XAUUSD,
        "timeframe": None,
        "range_start": datetime(2026, 1, 1, tzinfo=UTC),
        "range_end": datetime(2026, 2, 1, tzinfo=UTC),
        "summary": {"total_signals": 12, "wins": 7, "losses": 5, "win_rate": 0.5833},
        "run_at": datetime(2026, 2, 1, 12, tzinfo=UTC),
    }
    defaults.update(overrides)
    return BacktestRun(**defaults)  # type: ignore[arg-type]


async def test_get_backtest_runs_returns_a_persisted_run(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        saved = await BacktestRunRepository(session).save(_run())

    response = await api.client.get("/backtests")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == saved.id
    assert body[0]["kind"] == "signal"
    assert body[0]["symbol"] == "XAUUSD"
    assert body[0]["timeframe"] is None
    assert body[0]["summary"]["win_rate"] == 0.5833


async def test_get_backtest_runs_filters_by_symbol_and_kind(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        repository = BacktestRunRepository(session)
        await repository.save(_run(symbol=Symbol.XAUUSD, kind=BacktestKind.SIGNAL))
        await repository.save(_run(symbol=Symbol.EURUSD, kind=BacktestKind.SIGNAL))
        await repository.save(
            _run(symbol=Symbol.XAUUSD, kind=BacktestKind.PREDICTION, timeframe=Timeframe.M15, summary={"correct": 1})
        )

    response = await api.client.get("/backtests", params={"symbol": "XAUUSD", "kind": "prediction"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "XAUUSD"
    assert body[0]["kind"] == "prediction"
    assert body[0]["timeframe"] == "15m"


async def test_get_backtest_runs_orders_newest_first(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        repository = BacktestRunRepository(session)
        await repository.save(_run(run_at=datetime(2026, 1, 1, tzinfo=UTC)))
        await repository.save(_run(run_at=datetime(2026, 2, 1, tzinfo=UTC)))

    response = await api.client.get("/backtests")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["run_at"] > body[1]["run_at"]
