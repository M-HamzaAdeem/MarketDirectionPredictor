"""Recent closed candles per symbol/timeframe, read from SQLite.

Symbol and timeframe are typed path parameters (enums), not free text —
an invalid value is rejected by FastAPI with a 422 before this code runs.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.schemas.candle import CandleOut
from app.storage.database import get_session
from app.storage.repositories.candle_repository import CandleRepository

router = APIRouter(prefix="/candles", tags=["candles"])

_MAX_LIMIT = 500


@router.get("/{symbol}/{timeframe}", response_model=list[CandleOut])
async def get_candles(
    symbol: Symbol,
    timeframe: Timeframe,
    limit: int = Query(default=100, ge=1, le=_MAX_LIMIT),
    session: AsyncSession = Depends(get_session),
) -> list[CandleOut]:
    candles = await CandleRepository(session).get_recent(symbol, timeframe, limit=limit)
    return [
        CandleOut(
            open_time=candle.open_time,
            close_time=candle.close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        for candle in candles
    ]
