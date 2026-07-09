"""Candle persistence — the only place that translates between the domain
Candle dataclass and the CandleORM table. Reads always return domain
Candle objects; ORM rows never leak past this repository."""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.storage.models import CandleColumns, CandleORM

# Matches the unique index on CandleORM (ix_candles_symbol_timeframe_open_time).
_UNIQUE_CANDLE_COLUMNS = ("symbol", "timeframe", "open_time")


class CandleRepository:
    """`model` defaults to CandleORM (the Twelve Data pipeline's table);
    pass `model=TradingViewCandleORM` to operate on the fully separate
    TradingView table instead — see DataSource in core/constants.py. Both
    concrete classes share CandleColumns, so `type[CandleColumns]` is a
    type each genuinely satisfies (not a false subtype relationship).
    Every method below is otherwise identical regardless of which model is
    used."""

    def __init__(self, session: AsyncSession, model: type[CandleColumns] = CandleORM) -> None:
        self._session = session
        self._model = model

    async def save(self, candle: Candle) -> None:
        """Idempotent on (symbol, timeframe, open_time): if this exact
        candle boundary is already stored, this is a no-op rather than an
        IntegrityError. A live provider re-delivering the same boundary
        (e.g. a brief overlap around a reconnect/restart) is a real,
        observed occurrence, not a coding bug each time it happens — the
        caller (FeedService) still runs prediction/signal handlers
        afterward regardless, since those must react to every candle
        close whether or not this particular call was the one that
        persisted it."""
        stmt = sqlite_insert(self._model).values(
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
        await self._session.execute(stmt.on_conflict_do_nothing(index_elements=_UNIQUE_CANDLE_COLUMNS))
        await self._session.commit()

    async def save_many_if_missing(self, candles: list[Candle]) -> None:
        """Bulk-inserts candles, silently skipping any that already exist
        (same symbol/timeframe/open_time). For historical backfill, which
        may legitimately overlap with previously-backfilled or already
        live-ingested rows — this isn't hiding a real error, it's the
        intended idempotent-insert semantics."""
        if not candles:
            return

        stmt = sqlite_insert(self._model).values(
            [
                {
                    "symbol": candle.symbol.value,
                    "timeframe": candle.timeframe.value,
                    "open_time": candle.open_time,
                    "close_time": candle.close_time,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
                for candle in candles
            ]
        )
        await self._session.execute(stmt.on_conflict_do_nothing(index_elements=_UNIQUE_CANDLE_COLUMNS))
        await self._session.commit()

    async def get_recent(self, symbol: Symbol, timeframe: Timeframe, limit: int = 100) -> list[Candle]:
        stmt = (
            select(self._model)
            .where(self._model.symbol == symbol.value, self._model.timeframe == timeframe.value)
            .order_by(self._model.open_time.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = list(reversed(result.scalars().all()))
        return [_to_domain(row) for row in rows]

    async def get_latest(self, symbol: Symbol, timeframe: Timeframe) -> Candle | None:
        candles = await self.get_recent(symbol, timeframe, limit=1)
        return candles[0] if candles else None


def _to_domain(row: CandleColumns) -> Candle:
    return Candle(
        symbol=Symbol(row.symbol),
        timeframe=Timeframe(row.timeframe),
        open_time=row.open_time,
        close_time=row.close_time,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
    )
