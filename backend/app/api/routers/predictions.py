"""On-demand prediction: computes a fresh rule-based prediction from the
most recent closed candles, logs it (append-only, per PROJECT.md's "log
every prediction" rule), and returns it. A separate endpoint reads back
prediction history without recomputing.

Every call to .../latest logs a new row, even if called repeatedly in
quick succession — v1 has no scheduler to throttle this yet (Phase 4).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_prediction_engine
from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.base import Prediction
from app.prediction.engine import PredictionEngine
from app.schemas.prediction import PredictionOut
from app.storage.database import get_session
from app.storage.models import CandleORM
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.prediction_repository import PredictionRepository

router = APIRouter(prefix="/predictions", tags=["predictions"])

_MAX_HISTORY_LIMIT = 500
_CANDLE_WINDOW = 100


@router.get("/{symbol}/{timeframe}/latest", response_model=PredictionOut)
async def get_latest_prediction(
    symbol: Symbol,
    timeframe: Timeframe,
    engine: PredictionEngine = Depends(get_prediction_engine),
    session: AsyncSession = Depends(get_session),
) -> PredictionOut:
    candles = await CandleRepository(session).get_recent(symbol, timeframe, limit=_CANDLE_WINDOW)
    if not candles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No closed candles yet for {symbol.value}/{timeframe.value}",
        )

    prediction = engine.run(symbol, timeframe, [_to_domain_candle(candle) for candle in candles])
    await PredictionRepository(session).save(prediction)
    return _to_schema(prediction)


@router.get("/{symbol}/{timeframe}/history", response_model=list[PredictionOut])
async def get_prediction_history(
    symbol: Symbol,
    timeframe: Timeframe,
    limit: int = Query(default=100, ge=1, le=_MAX_HISTORY_LIMIT),
    session: AsyncSession = Depends(get_session),
) -> list[PredictionOut]:
    predictions = await PredictionRepository(session).get_recent(symbol, timeframe, limit=limit)
    return [
        PredictionOut(
            symbol=Symbol(row.symbol),
            timeframe=Timeframe(row.timeframe),
            direction=Direction(row.direction),
            confidence=row.confidence,
            reason=row.reason,
            price=row.price,
            timestamp=row.timestamp,
        )
        for row in predictions
    ]


def _to_domain_candle(candle: CandleORM) -> Candle:
    return Candle(
        symbol=Symbol(candle.symbol),
        timeframe=Timeframe(candle.timeframe),
        open_time=candle.open_time,
        close_time=candle.close_time,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


def _to_schema(prediction: Prediction) -> PredictionOut:
    return PredictionOut(
        symbol=prediction.symbol,
        timeframe=prediction.timeframe,
        direction=prediction.direction,
        confidence=prediction.confidence,
        reason=prediction.reason,
        price=prediction.price,
        timestamp=prediction.timestamp,
    )
