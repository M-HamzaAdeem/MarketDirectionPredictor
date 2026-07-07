"""Domain type for an ICT-style trade signal: a concrete, gradable trade
setup with entry/stop/target. A minimum R:R is enforced by the signal
builder before this object is ever constructed — a Signal below the
project's R:R floor simply never exists.

Unlike Candle/Prediction (immutable, point-in-time facts, append-only),
a Signal has a genuine lifecycle — OPEN until price resolves it to
WIN/LOSS/EXPIRED — so it carries an `id` once persisted, so the tracker
that watches it forward in time can update the same row.
"""

from dataclasses import dataclass
from datetime import datetime
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
    status: SignalStatus = SignalStatus.OPEN
    closed_at: datetime | None = None
    realized_rr: float | None = None
    id: int | None = None
