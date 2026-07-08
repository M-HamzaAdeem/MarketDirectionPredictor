"""Domain type for an ICT-style trade signal: a concrete, gradable trade
setup with entry/stop/target. A minimum R:R is enforced by the signal
builder before this object is ever constructed — a Signal below the
project's R:R floor simply never exists.

Unlike Candle/Prediction (immutable, point-in-time facts, append-only),
a Signal has a genuine lifecycle — OPEN until price resolves it to
WIN/LOSS/EXPIRED — so it carries an `id` once persisted, so the tracker
that watches it forward in time can update the same row.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.core.constants import Direction, Symbol, Timeframe


class SignalStatus(str, Enum):
    OPEN = "open"
    WIN = "win"
    LOSS = "loss"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Signal:
    symbol: Symbol
    entry_timeframe: Timeframe
    direction: Direction
    entry: float
    stop: float
    target: float
    risk_reward: float
    reason: str
    details: dict[str, Any]
    opened_at: datetime
    # Wall-clock moment this row was actually inserted — distinct from
    # opened_at, which is the *candle's* close_time and can legitimately sit
    # hours before this (see decisions.md's stale-entry-tap entry: opened_at
    # is derived from historical market data, not from when the system
    # itself acted on it). Keeping both is what makes that class of "when
    # did this really happen" question answerable directly from the DB.
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: SignalStatus = SignalStatus.OPEN
    closed_at: datetime | None = None
    realized_rr: float | None = None
    id: int | None = None
