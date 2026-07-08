"""Backtest run persistence — append-only, like Candle/Prediction: a run
is saved once and never mutated afterward."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.models import BacktestKind, BacktestRun
from app.core.constants import Symbol, Timeframe
from app.storage.models import BacktestRunORM


class BacktestRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: BacktestRun) -> BacktestRun:
        row = BacktestRunORM(
            kind=run.kind.value,
            symbol=run.symbol.value,
            timeframe=run.timeframe.value if run.timeframe is not None else None,
            range_start=run.range_start,
            range_end=run.range_end,
            summary=json.dumps(run.summary),
            run_at=run.run_at,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)

    async def get_recent(
        self,
        symbol: Symbol | None = None,
        kind: BacktestKind | None = None,
        limit: int = 20,
    ) -> list[BacktestRun]:
        stmt = select(BacktestRunORM).order_by(BacktestRunORM.run_at.desc()).limit(limit)
        if symbol is not None:
            stmt = stmt.where(BacktestRunORM.symbol == symbol.value)
        if kind is not None:
            stmt = stmt.where(BacktestRunORM.kind == kind.value)
        result = await self._session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]


def _to_domain(row: BacktestRunORM) -> BacktestRun:
    return BacktestRun(
        id=row.id,
        kind=BacktestKind(row.kind),
        symbol=Symbol(row.symbol),
        timeframe=Timeframe(row.timeframe) if row.timeframe is not None else None,
        range_start=row.range_start,
        range_end=row.range_end,
        summary=json.loads(row.summary),
        run_at=row.run_at,
    )
