"""SQLAlchemy ORM models. Kept separate from the domain dataclasses in
app.feeds.base (Candle, Tick) so persistence concerns never leak into
aggregation/prediction logic."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class CandleORM(Base):
    __tablename__ = "candles"
    __table_args__ = (
        Index("ix_candles_symbol_timeframe_open_time", "symbol", "timeframe", "open_time", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str] = mapped_column(String(4))
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
