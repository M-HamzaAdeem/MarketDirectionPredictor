from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.engine import PredictionEngine
from app.prediction.rule_based import RuleBasedStrategy
from app.services.prediction_service import PredictionService
from app.storage.database import Base
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.prediction_repository import PredictionRepository


class _RecordingBroadcaster:
    def __init__(self) -> None:
        self.predictions: list[object] = []

    async def broadcast_prediction(self, prediction: object) -> None:
        self.predictions.append(prediction)


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield factory
    await engine.dispose()


async def _seed_candles(session_factory, closes: list[float]) -> None:
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


async def test_on_candle_closed_persists_and_broadcasts_a_prediction(session_factory) -> None:
    await _seed_candles(session_factory, [100.0 + i for i in range(5)])
    broadcaster = _RecordingBroadcaster()
    service = PredictionService(PredictionEngine(RuleBasedStrategy()), broadcaster, session_factory)

    closed_candle = Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M1,
        open_time=datetime(2026, 1, 1, 10, 4, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, 10, 5, tzinfo=UTC),
        open=104.0,
        high=104.5,
        low=103.5,
        close=104.0,
        volume=0.0,
    )

    await service.on_candle_closed(closed_candle)

    assert len(broadcaster.predictions) == 1
    prediction = broadcaster.predictions[0]
    assert prediction.symbol == Symbol.XAUUSD
    assert prediction.timeframe == Timeframe.M1
    assert prediction.price == 104.0

    async with session_factory() as session:
        logged = await PredictionRepository(session).get_recent(Symbol.XAUUSD, Timeframe.M1)
    assert len(logged) == 1
