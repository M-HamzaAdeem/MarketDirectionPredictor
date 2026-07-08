"""SQLAlchemy ORM models. Kept separate from the domain dataclasses in
app.feeds.base / app.prediction.base / app.prediction.signal (Candle,
Tick, Prediction, Signal) so persistence concerns never leak into
aggregation/prediction logic."""

from datetime import datetime

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base
from app.storage.types import UTCDateTime


class CandleORM(Base):
    __tablename__ = "candles"
    __table_args__ = (
        Index("ix_candles_symbol_timeframe_open_time", "symbol", "timeframe", "open_time", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str] = mapped_column(String(4))
    open_time: Mapped[datetime] = mapped_column(UTCDateTime)
    close_time: Mapped[datetime] = mapped_column(UTCDateTime)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class PredictionORM(Base):
    """Append-only prediction log — rows are never updated, only inserted,
    so history and future backtesting have a complete record."""

    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str] = mapped_column(String(4))
    direction: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(512))
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)


class SignalORM(Base):
    """Every generated ICT signal. Unlike CandleORM/PredictionORM (pure
    append-only logs), a signal row is updated once when it resolves
    (status/closed_at/realized_rr) — the one place this codebase mutates
    an existing row, because a signal genuinely has a lifecycle
    (open -> win/loss/expired), not a point-in-time fact."""

    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_symbol_status", "symbol", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16))
    entry_timeframe: Mapped[str] = mapped_column(String(4))
    direction: Mapped[str] = mapped_column(String(8))
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    risk_reward: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(8), default="open")  # must match SignalStatus.OPEN.value
    reason: Mapped[str] = mapped_column(String(512))
    details: Mapped[str] = mapped_column(Text)  # JSON-encoded structured breakdown
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    realized_rr: Mapped[float | None] = mapped_column(Float, nullable=True)


class BacktestRunORM(Base):
    """One CLI backtest invocation's result (app/backtesting/cli.py) —
    append-only, like CandleORM/PredictionORM: a run is a point-in-time
    fact about how a strategy performed over some historical range, never
    updated after being saved. `summary` is JSON-encoded, the same pattern
    as SignalORM.details, since its shape differs by `kind` (signal vs.
    prediction backtests report different stats)."""

    __tablename__ = "backtest_runs"
    __table_args__ = (Index("ix_backtest_runs_symbol_kind", "symbol", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    symbol: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str | None] = mapped_column(String(4), nullable=True)
    range_start: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    range_end: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    run_at: Mapped[datetime] = mapped_column(UTCDateTime)
