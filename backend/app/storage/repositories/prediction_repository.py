"""Prediction persistence — append-only. Every prediction run is saved,
never overwritten, so history and (later) backtesting have a complete
record. The only place that translates between the domain Prediction
dataclass and the PredictionORM table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.prediction.base import Prediction
from app.storage.models import PredictionORM


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, prediction: Prediction) -> None:
        self._session.add(
            PredictionORM(
                symbol=prediction.symbol.value,
                timeframe=prediction.timeframe.value,
                direction=prediction.direction.value,
                confidence=prediction.confidence,
                reason=prediction.reason,
                price=prediction.price,
                timestamp=prediction.timestamp,
            )
        )
        await self._session.commit()

    async def get_recent(self, symbol: Symbol, timeframe: Timeframe, limit: int = 100) -> list[PredictionORM]:
        stmt = (
            select(PredictionORM)
            .where(PredictionORM.symbol == symbol.value, PredictionORM.timeframe == timeframe.value)
            .order_by(PredictionORM.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def get_latest(self, symbol: Symbol, timeframe: Timeframe) -> PredictionORM | None:
        predictions = await self.get_recent(symbol, timeframe, limit=1)
        return predictions[0] if predictions else None
