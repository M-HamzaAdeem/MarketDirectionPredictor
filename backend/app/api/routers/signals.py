"""Read-only endpoints for ICT signals: still-open signals and per-symbol
history including resolved outcomes. There is no POST endpoint — a signal
is only ever created by SignalService reacting to a live candle close;
either the pipeline found a real, winning-caliber setup, or it doesn't
exist. Nothing here can be used to fabricate one.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol
from app.prediction.signal import Signal
from app.schemas.signal import SignalOut
from app.storage.database import get_session
from app.storage.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])

_MAX_HISTORY_LIMIT = 500


@router.get("/open", response_model=list[SignalOut])
async def get_open_signals(
    symbol: Symbol | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[SignalOut]:
    signals = await SignalRepository(session).get_open(symbol)
    return [_to_schema(signal) for signal in signals]


@router.get("/{symbol}/history", response_model=list[SignalOut])
async def get_signal_history(
    symbol: Symbol,
    limit: int = Query(default=100, ge=1, le=_MAX_HISTORY_LIMIT),
    session: AsyncSession = Depends(get_session),
) -> list[SignalOut]:
    signals = await SignalRepository(session).get_recent(symbol, limit=limit)
    return [_to_schema(signal) for signal in signals]


def _to_schema(signal: Signal) -> SignalOut:
    return SignalOut(
        symbol=signal.symbol,
        entry_timeframe=signal.entry_timeframe,
        direction=signal.direction,
        entry=signal.entry,
        stop=signal.stop,
        target=signal.target,
        risk_reward=signal.risk_reward,
        status=signal.status,
        reason=signal.reason,
        opened_at=signal.opened_at,
        closed_at=signal.closed_at,
        realized_rr=signal.realized_rr,
    )
