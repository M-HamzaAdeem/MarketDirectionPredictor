"""Prediction persistence — append-only. Every prediction run is saved,
never overwritten, so history and (later) backtesting have a complete
record. The only place that translates between the domain Prediction
dataclass and the PredictionORM table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.prediction.base import Prediction
from app.storage.models import PredictionColumns, PredictionORM


class PredictionRepository:
    """`model` defaults to PredictionORM (the Twelve Data pipeline's
    table); pass `model=TradingViewPredictionORM` to operate on the fully
    separate TradingView table instead — see DataSource in core/constants.py.
    Both concrete classes share PredictionColumns, so `type[PredictionColumns]`
    is a type each genuinely satisfies (not a false subtype relationship)."""

    def __init__(self, session: AsyncSession, model: type[PredictionColumns] = PredictionORM) -> None:
        self._session = session
        self._model = model

    async def save(self, prediction: Prediction) -> None:
        self._session.add(
            self._model(
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

    async def get_recent(self, symbol: Symbol, timeframe: Timeframe, limit: int = 100) -> list[PredictionColumns]:
        stmt = (
            select(self._model)
            .where(self._model.symbol == symbol.value, self._model.timeframe == timeframe.value)
            .order_by(self._model.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def get_latest(self, symbol: Symbol, timeframe: Timeframe) -> PredictionColumns | None:
        predictions = await self.get_recent(symbol, timeframe, limit=1)
        return predictions[0] if predictions else None
