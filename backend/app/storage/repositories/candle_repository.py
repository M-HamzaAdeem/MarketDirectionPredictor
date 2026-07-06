"""Candle persistence — the only place that translates between the domain
Candle dataclass and the CandleORM table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.storage.models import CandleORM


class CandleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, candle: Candle) -> None:
        self._session.add(
            CandleORM(
                symbol=candle.symbol.value,
                timeframe=candle.timeframe.value,
                open_time=candle.open_time,
                close_time=candle.close_time,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
        )
        await self._session.commit()

    async def get_recent(self, symbol: Symbol, timeframe: Timeframe, limit: int = 100) -> list[CandleORM]:
        stmt = (
            select(CandleORM)
            .where(CandleORM.symbol == symbol.value, CandleORM.timeframe == timeframe.value)
            .order_by(CandleORM.open_time.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def get_latest(self, symbol: Symbol, timeframe: Timeframe) -> CandleORM | None:
        candles = await self.get_recent(symbol, timeframe, limit=1)
        return candles[0] if candles else None
