from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.constants import Direction, Symbol, Timeframe
from app.prediction.signal import SignalStatus


class SignalOut(BaseModel):
    id: int
    symbol: Symbol
    entry_timeframe: Timeframe
    direction: Direction
    entry: float
    stop: float
    target: float
    risk_reward: float
    status: SignalStatus
    reason: str
    # Structured breakdown (poi_type, ote_low/high, swept_level,
    # volume_profile_poc, confirming_event) — see signal_builder.py's
    # _build_details. Lets the chart overlay OTE/POI/swept-level context
    # beyond the plain entry/stop/target lines.
    details: dict[str, Any]
    opened_at: datetime
    closed_at: datetime | None
    realized_rr: float | None
