"""Domain type for a persisted backtest run — the result of one CLI
invocation of run_signal_backtest or run_prediction_backtest, kept for
later review without re-running it (a real, rate-limited historical fetch
that costs real API credits and can take minutes)."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.constants import Symbol, Timeframe


class BacktestKind(str, Enum):
    SIGNAL = "signal"
    PREDICTION = "prediction"


@dataclass(frozen=True, slots=True)
class BacktestRun:
    kind: BacktestKind
    symbol: Symbol
    # Only meaningful for PREDICTION runs — a SIGNAL run spans all three
    # ICT timeframes (4H/1H/15m) at once, not a single one.
    timeframe: Timeframe | None
    range_start: datetime | None
    range_end: datetime | None
    summary: dict[str, Any]
    run_at: datetime
    id: int | None = None
