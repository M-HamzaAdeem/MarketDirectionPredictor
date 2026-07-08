"""Read-only endpoints for ICT signals, plus one on-demand endpoint:
still-open signals, per-symbol history including resolved outcomes, and
.../latest — the only endpoint that can create a signal outside of
SignalService reacting to a live 15m candle close.

Unlike predictions (stateless — safe to recompute and log on every call),
a Signal has a real lifecycle: .../latest returns the already-open signal
for a symbol as-is if one exists, never recomputing or duplicating it;
only when none is open does it attempt to build one from whatever closed
candles already exist, reusing the exact same guard SignalService applies
live (an eligible-tap-candle filter so a resolved signal's own tap candle
can't immediately reopen it — see [[backtest-rapid-reopen-fix]] in
decisions.md). Nothing here can fabricate a signal build_signal()
wouldn't also produce live.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Symbol, Timeframe
from app.prediction.signal import Signal
from app.prediction.signal_builder import build_signal, eligible_entry_candles
from app.schemas.signal import SignalOut
from app.services.signal_service import CANDLE_WINDOW_1H, CANDLE_WINDOW_4H, CANDLE_WINDOW_15M
from app.storage.database import get_session
from app.storage.repositories.candle_repository import CandleRepository
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


@router.get("/{symbol}/latest", response_model=SignalOut)
async def get_latest_signal(
    symbol: Symbol,
    session: AsyncSession = Depends(get_session),
) -> SignalOut:
    # A GET that can write is a deliberate, pattern-consistent choice, not
    # an oversight — mirrors predictions.py's .../latest exactly. This one
    # is actually more idempotent than that one: the get_open guard below
    # means repeated calls only ever produce one row per symbol, whereas
    # predictions logs a fresh row every call.
    signal_repository = SignalRepository(session)

    open_signals = await signal_repository.get_open(symbol)
    if open_signals:
        return _to_schema(open_signals[0])

    candle_repository = CandleRepository(session)
    candles_4h = await candle_repository.get_recent(symbol, Timeframe.H4, limit=CANDLE_WINDOW_4H)
    candles_1h = await candle_repository.get_recent(symbol, Timeframe.H1, limit=CANDLE_WINDOW_1H)
    candles_15m = await candle_repository.get_recent(symbol, Timeframe.M15, limit=CANDLE_WINDOW_15M)

    most_recent = await signal_repository.get_recent(symbol, limit=1)
    last_opened_at = most_recent[0].opened_at if most_recent else None
    candles_15m = eligible_entry_candles(candles_15m, last_opened_at)

    signal = build_signal(symbol, candles_4h, candles_1h, candles_15m)
    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No open signal and no winning-caliber setup right now for {symbol.value}",
        )

    saved = await signal_repository.save(signal)
    return _to_schema(saved)


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
        id=signal.id,
        symbol=signal.symbol,
        entry_timeframe=signal.entry_timeframe,
        direction=signal.direction,
        entry=signal.entry,
        stop=signal.stop,
        target=signal.target,
        risk_reward=signal.risk_reward,
        status=signal.status,
        reason=signal.reason,
        details=signal.details,
        opened_at=signal.opened_at,
        closed_at=signal.closed_at,
        realized_rr=signal.realized_rr,
    )
