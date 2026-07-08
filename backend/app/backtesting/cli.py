"""CLI entry point for running a backtest against real historical data.

Usage:
    python -m app.backtesting.cli [--symbol XAUUSD] [--kind signal|prediction|both]

Deliberately does NOT offer a `--strategy ml` option to re-test a saved
MLStrategy model here, even though `run_prediction_backtest` accepts any
`PredictionStrategy`: doing so correctly requires evaluating only on
candles the model never trained on, and this CLI has no way to know where
a given saved model's train/test split boundary was. Running it over an
arbitrary freshly-refetched history range would silently test the model
partly (or mostly) on data it already memorized, producing an inflated,
untrustworthy accuracy — exactly the bug hit and removed from
`app/ml/train.py` (see decisions.md). `train.py`'s own holdout accuracy,
computed with a clean chronological split, is the trustworthy number for
judging a trained model — there is no shortcut through this CLI.

Fetches history directly via a bare `TwelveDataProvider` — deliberately
bypassing `app/feeds/factory.py`'s fallback-wrapped provider, since a
backtest must fail loudly on a real data-fetch problem (bad API key, rate
limit, network error), not silently substitute the mock feed's much
shorter synthetic history and produce a meaningless "backtest."

Prints a summary to stdout and persists it via BacktestRunRepository so it
can be reviewed later (GET /backtests) without re-running — a real,
rate-limited historical fetch that costs API credits and can take minutes.
"""

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.backtesting.models import BacktestKind, BacktestRun
from app.backtesting.prediction_backtest import PredictionBacktestSummary, run_prediction_backtest
from app.backtesting.signal_backtest import SignalBacktestSummary, run_signal_backtest
from app.core.config import get_settings
from app.core.constants import Symbol, Timeframe
from app.feeds.twelve_data_provider import TwelveDataProvider
from app.storage.database import get_session_factory, init_models
from app.storage.repositories.backtest_run_repository import BacktestRunRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
# Quiet third-party request/connection logging specifically: httpx logs
# full request URLs (including query params) at INFO, and this app's own
# WebSocket URL to Twelve Data still carries the API key in the query
# string (the one auth surface that has no header-based alternative — see
# twelve_data_provider.py). Keeping these at WARNING is defense-in-depth
# against a secret leaking into stdout/logs from a library we don't control.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)

_HISTORY_COUNT = 5000  # Twelve Data's free-tier max per request, costing exactly 1 API credit regardless


async def main() -> None:
    args = _parse_args()
    settings = get_settings()
    if not settings.twelve_data_api_key:
        raise SystemExit("TWELVE_DATA_API_KEY is not set — backtesting needs real historical data.")

    await init_models()
    session_factory = get_session_factory()
    provider = TwelveDataProvider(api_key=settings.twelve_data_api_key)
    symbols = [args.symbol] if args.symbol is not None else settings.symbols

    try:
        for symbol in symbols:
            if args.kind in ("signal", "both"):
                await _run_signal_backtest(provider, session_factory, symbol)
            if args.kind in ("prediction", "both"):
                for timeframe in settings.timeframes:
                    await _run_prediction_backtest(provider, session_factory, symbol, timeframe)
    finally:
        await provider.disconnect()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", type=Symbol, choices=list(Symbol), default=None, help="Defaults to every configured symbol.")
    parser.add_argument("--kind", choices=["signal", "prediction", "both"], default="both")
    return parser.parse_args()


async def _run_signal_backtest(
    provider: TwelveDataProvider, session_factory: async_sessionmaker[AsyncSession], symbol: Symbol
) -> None:
    print(f"\n=== Signal backtest: {symbol.value} ===")
    candles_4h = await provider.fetch_history(symbol, Timeframe.H4, _HISTORY_COUNT)
    candles_1h = await provider.fetch_history(symbol, Timeframe.H1, _HISTORY_COUNT)
    candles_15m = await provider.fetch_history(symbol, Timeframe.M15, _HISTORY_COUNT)

    summary = run_signal_backtest(symbol, candles_4h, candles_1h, candles_15m)
    _print_signal_summary(summary)
    await _persist(
        session_factory,
        BacktestRun(
            kind=BacktestKind.SIGNAL,
            symbol=symbol,
            timeframe=None,
            range_start=summary.range_start,
            range_end=summary.range_end,
            summary=_signal_summary_dict(summary),
            run_at=datetime.now(UTC),
        ),
    )


async def _run_prediction_backtest(
    provider: TwelveDataProvider,
    session_factory: async_sessionmaker[AsyncSession],
    symbol: Symbol,
    timeframe: Timeframe,
) -> None:
    print(f"\n=== Prediction backtest: {symbol.value}/{timeframe.value} ===")
    candles = await provider.fetch_history(symbol, timeframe, _HISTORY_COUNT)

    summary = run_prediction_backtest(symbol, timeframe, candles)
    _print_prediction_summary(summary)
    await _persist(
        session_factory,
        BacktestRun(
            kind=BacktestKind.PREDICTION,
            symbol=symbol,
            timeframe=timeframe,
            range_start=summary.range_start,
            range_end=summary.range_end,
            summary=_prediction_summary_dict(summary),
            run_at=datetime.now(UTC),
        ),
    )


async def _persist(session_factory: async_sessionmaker[AsyncSession], run: BacktestRun) -> None:
    async with session_factory() as session:
        await BacktestRunRepository(session).save(run)


def _signal_summary_dict(summary: SignalBacktestSummary) -> dict[str, Any]:
    return {
        "total_signals": summary.total_signals,
        "wins": summary.wins,
        "losses": summary.losses,
        "expired": summary.expired,
        "still_open": summary.still_open,
        "win_rate": summary.win_rate,
        "avg_realized_rr": summary.avg_realized_rr,
    }


def _prediction_summary_dict(summary: PredictionBacktestSummary) -> dict[str, Any]:
    return {
        "total_predictions": summary.total_predictions,
        "correct": summary.correct,
        "incorrect": summary.incorrect,
        "neutral_skipped": summary.neutral_skipped,
        "direction_accuracy": summary.direction_accuracy,
    }


def _print_signal_summary(summary: SignalBacktestSummary) -> None:
    print(f"Range: {summary.range_start} -> {summary.range_end}")
    print(f"Total signals: {summary.total_signals}")
    print(f"Wins: {summary.wins}  Losses: {summary.losses}  Expired: {summary.expired}  Open: {summary.still_open}")
    print(f"Win rate: {summary.win_rate:.1%}")
    print(f"Avg realized R:R: {summary.avg_realized_rr}")


def _print_prediction_summary(summary: PredictionBacktestSummary) -> None:
    print(f"Range: {summary.range_start} -> {summary.range_end}")
    print(f"Total predictions scored: {summary.correct + summary.incorrect} (skipped {summary.neutral_skipped} neutral)")
    print(f"Correct: {summary.correct}  Incorrect: {summary.incorrect}")
    print(f"Direction accuracy: {summary.direction_accuracy:.1%}")


if __name__ == "__main__":
    asyncio.run(main())
