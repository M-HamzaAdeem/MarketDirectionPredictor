from datetime import datetime

from pydantic import BaseModel


class CandleOut(BaseModel):
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
