from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers import signals
from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus
from app.storage.database import Base, get_session
from app.storage.models import TradingViewSignalORM
from app.storage.repositories.candle_repository import CandleRepository
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


def _bullish_setup_candles(timeframe: Timeframe) -> list[Candle]:
    # Same validated bullish sweep -> CHoCH -> POI/OTE -> untested target
    # fixture used in tests/unit/test_signal_builder.py and
    # tests/integration/test_signal_service.py.
    opens = [100, 100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118]
    closes = [100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118, 117]
    wicks = [0.3 + 0.02 * i for i in range(len(opens))]
    highs = [max(o, c) + w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows = [min(o, c) - w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows[9] = 89.0

    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=timeframe,
            open_time=base + timedelta(hours=i),
            close_time=base + timedelta(hours=i + 1),
            open=opens[i],
            high=highs[i],
            low=lows[i],
            close=closes[i],
            volume=10.0 + i,
        )
        for i in range(len(closes))
    ]


async def _seed_candles(session_factory: async_sessionmaker[AsyncSession], candles: list[Candle]) -> None:
    async with session_factory() as session:
        repository = CandleRepository(session)
        for candle in candles:
            await repository.save(candle)


async def test_get_latest_signal_returns_the_already_open_signal_without_recomputing(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    response = await api.client.get("/signals/XAUUSD/latest", params={"source": "twelve_data"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == saved.id

    async with api.session_factory() as session:
        all_signals = await SignalRepository(session).get_recent(Symbol.XAUUSD)
    assert len(all_signals) == 1  # nothing new was created


async def test_get_latest_signal_computes_and_persists_one_when_none_is_open(api: _ApiFixture) -> None:
    await _seed_candles(api.session_factory, _bullish_setup_candles(Timeframe.H4))
    await _seed_candles(api.session_factory, _bullish_setup_candles(Timeframe.H1))
    await _seed_candles(
        api.session_factory,
        [
            Candle(
                symbol=Symbol.XAUUSD,
                timeframe=Timeframe.M15,
                open_time=datetime(2026, 1, 2, tzinfo=UTC),
                close_time=datetime(2026, 1, 2, 0, 15, tzinfo=UTC),
                open=97.5,
                high=99.0,
                low=97.0,
                close=98.0,
                volume=1.0,
            )
        ],
    )

    response = await api.client.get("/signals/XAUUSD/latest", params={"source": "twelve_data"})

    assert response.status_code == 200
    body = response.json()
    assert body["direction"] == "bullish"
    assert body["status"] == "open"

    async with api.session_factory() as session:
        open_signals = await SignalRepository(session).get_open(Symbol.XAUUSD)
    assert len(open_signals) == 1
    assert open_signals[0].id == body["id"]


async def test_get_latest_signal_returns_404_when_no_setup_exists(api: _ApiFixture) -> None:
    response = await api.client.get("/signals/XAUUSD/latest")
    assert response.status_code == 404


async def test_get_open_signals_returns_a_persisted_open_signal_with_its_id(api: _ApiFixture) -> None:
    async with api.session_factory() as session:
        saved = await SignalRepository(session).save(_signal())

    response = await api.client.get("/signals/open", params={"source": "twelve_data"})

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

    response = await api.client.get("/signals/open", params={"symbol": "EURUSD", "source": "twelve_data"})

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

    response = await api.client.get("/signals/XAUUSD/history", params={"source": "twelve_data"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "win"
    assert body[0]["realized_rr"] == 3.0


async def test_get_signal_history_rejects_an_unknown_symbol(api: _ApiFixture) -> None:
    response = await api.client.get("/signals/BTCUSD/history")
    assert response.status_code == 422


async def test_source_defaults_to_tradingview_and_stays_isolated_from_twelve_data(api: _ApiFixture) -> None:
    # An open signal exists in the Twelve Data table only.
    async with api.session_factory() as session:
        await SignalRepository(session).save(_signal())

    default_open = await api.client.get("/signals/open")  # no ?source= at all
    assert default_open.json() == []  # must not see the Twelve Data signal via the default

    async with api.session_factory() as session:
        await SignalRepository(session, model=TradingViewSignalORM).save(_signal(entry=1.0, stop=0.9, target=1.3))

    default_open = await api.client.get("/signals/open")  # no ?source= -> tradingview
    twelve_data_open = await api.client.get("/signals/open", params={"source": "twelve_data"})

    assert len(default_open.json()) == 1
    assert default_open.json()[0]["entry"] == 1.0
    assert len(twelve_data_open.json()) == 1
    assert twelve_data_open.json()[0]["entry"] == 2350.0
