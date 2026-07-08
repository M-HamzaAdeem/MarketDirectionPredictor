"""Read-only view of past backtest runs. There is no POST endpoint — a run
is only ever produced by the CLI (app/backtesting/cli.py), which needs
direct, unthrottled-by-the-request-cycle access to a real feed provider
and can take minutes to fetch enough history; triggering one from an HTTP
request would mean either blocking the request for that long or building
out background-job infrastructure this project doesn't have (YAGNI until
there's real demand for on-demand backtests from the UI).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.models import BacktestKind, BacktestRun
from app.core.constants import Symbol
from app.schemas.backtest import BacktestRunOut
from app.storage.database import get_session
from app.storage.repositories.backtest_run_repository import BacktestRunRepository

router = APIRouter(prefix="/backtests", tags=["backtests"])

_MAX_LIMIT = 100


@router.get("", response_model=list[BacktestRunOut])
async def get_backtest_runs(
    symbol: Symbol | None = None,
    kind: BacktestKind | None = None,
    limit: int = Query(default=20, ge=1, le=_MAX_LIMIT),
    session: AsyncSession = Depends(get_session),
) -> list[BacktestRunOut]:
    runs = await BacktestRunRepository(session).get_recent(symbol=symbol, kind=kind, limit=limit)
    return [_to_schema(run) for run in runs]


def _to_schema(run: BacktestRun) -> BacktestRunOut:
    return BacktestRunOut(
        id=run.id,
        kind=run.kind,
        symbol=run.symbol,
        timeframe=run.timeframe,
        range_start=run.range_start,
        range_end=run.range_end,
        summary=run.summary,
        run_at=run.run_at,
    )
