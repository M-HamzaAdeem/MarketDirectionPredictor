"""Signal persistence. Unlike Candle/Prediction (immutable point-in-time
facts, append-only), a Signal has a lifecycle: save() inserts it OPEN, and
update_outcome() is the one mutation this codebase performs on an existing
row, resolving it to WIN/LOSS/EXPIRED."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Direction, Symbol, Timeframe
from app.prediction.signal import Signal, SignalStatus
from app.storage.models import SignalORM


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, signal: Signal) -> Signal:
        row = SignalORM(
            symbol=signal.symbol.value,
            entry_timeframe=signal.entry_timeframe.value,
            direction=signal.direction.value,
            entry=signal.entry,
            stop=signal.stop,
            target=signal.target,
            risk_reward=signal.risk_reward,
            status=signal.status.value,
            reason=signal.reason,
            details=json.dumps(signal.details),
            opened_at=signal.opened_at,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)

    async def get_open(self, symbol: Symbol | None = None) -> list[Signal]:
        stmt = select(SignalORM).where(SignalORM.status == SignalStatus.OPEN.value)
        if symbol is not None:
            stmt = stmt.where(SignalORM.symbol == symbol.value)
        result = await self._session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]

    async def get_recent(self, symbol: Symbol, limit: int = 100) -> list[Signal]:
        stmt = (
            select(SignalORM)
            .where(SignalORM.symbol == symbol.value)
            .order_by(SignalORM.opened_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(reversed([_to_domain(row) for row in result.scalars().all()]))

    async def update_outcome(
        self, signal_id: int, status: SignalStatus, closed_at: datetime, realized_rr: float
    ) -> None:
        row = await self._session.get(SignalORM, signal_id)
        if row is None:
            return
        row.status = status.value
        row.closed_at = closed_at
        row.realized_rr = realized_rr
        await self._session.commit()


def _to_domain(row: SignalORM) -> Signal:
    return Signal(
        id=row.id,
        symbol=Symbol(row.symbol),
        entry_timeframe=Timeframe(row.entry_timeframe),
        direction=Direction(row.direction),
        entry=row.entry,
        stop=row.stop,
        target=row.target,
        risk_reward=row.risk_reward,
        reason=row.reason,
        details=json.loads(row.details),
        opened_at=row.opened_at,
        status=SignalStatus(row.status),
        closed_at=row.closed_at,
        realized_rr=row.realized_rr,
    )
