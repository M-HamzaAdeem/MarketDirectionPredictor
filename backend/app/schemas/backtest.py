from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.backtesting.models import BacktestKind
from app.core.constants import Symbol, Timeframe


class BacktestRunOut(BaseModel):
    id: int
    kind: BacktestKind
    symbol: Symbol
    timeframe: Timeframe | None
    range_start: datetime | None
    range_end: datetime | None
    # SignalBacktestSummary or PredictionBacktestSummary as a plain dict —
    # shape differs by `kind`, see app/backtesting/*_backtest.py.
    summary: dict[str, Any]
    run_at: datetime
