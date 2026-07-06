"""Computes and persists a fresh prediction whenever a candle closes, then
broadcasts it. Bridges FeedService's candle-close events to the Phase 3
prediction engine and the WebSocket broadcast layer — this is what makes
prediction scheduling event-driven (a new candle close) rather than a
fixed polling interval; see decisions.md.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.feeds.base import Candle
from app.prediction.engine import CANDLE_WINDOW, PredictionEngine
from app.services.broadcast_service import BroadcastService
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.prediction_repository import PredictionRepository


class PredictionService:
    def __init__(
        self,
        engine: PredictionEngine,
        broadcaster: BroadcastService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._engine = engine
        self._broadcaster = broadcaster
        self._session_factory = session_factory

    async def on_candle_closed(self, closed_candle: Candle) -> None:
        async with self._session_factory() as session:
            candles = await CandleRepository(session).get_recent(
                closed_candle.symbol, closed_candle.timeframe, limit=CANDLE_WINDOW
            )
            prediction = self._engine.run(closed_candle.symbol, closed_candle.timeframe, candles)
            await PredictionRepository(session).save(prediction)

        await self._broadcaster.broadcast_prediction(prediction)
