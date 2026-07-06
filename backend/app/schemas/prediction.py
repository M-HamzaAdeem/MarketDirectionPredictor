from datetime import datetime

from pydantic import BaseModel

from app.core.constants import Direction, Symbol, Timeframe


class PredictionOut(BaseModel):
    symbol: Symbol
    timeframe: Timeframe
    direction: Direction
    confidence: float
    reason: str
    price: float
    timestamp: datetime
