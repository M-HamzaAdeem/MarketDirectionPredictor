from datetime import datetime

from pydantic import BaseModel

from app.core.constants import Direction, Symbol, Timeframe
from app.prediction.signal import SignalStatus


class SignalOut(BaseModel):
    symbol: Symbol
    entry_timeframe: Timeframe
    direction: Direction
    entry: float
    stop: float
    target: float
    risk_reward: float
    status: SignalStatus
    reason: str
    opened_at: datetime
    closed_at: datetime | None
    realized_rr: float | None
