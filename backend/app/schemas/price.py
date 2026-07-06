from datetime import datetime

from pydantic import BaseModel

from app.core.constants import Symbol


class PriceOut(BaseModel):
    symbol: Symbol
    price: float
    timestamp: datetime
