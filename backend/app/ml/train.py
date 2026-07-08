"""Trains one RandomForestClassifier per (symbol, timeframe) pair on real
historical data and persists it for MLStrategy to load.

Usage:
    python -m app.ml.train [--symbol XAUUSD] [--timeframe 1h]

Defaults to every configured symbol x timeframe (15 models). Fetches
history directly via a bare `TwelveDataProvider` — same reasoning as
`app/backtesting/cli.py`: training must fail loudly on a real fetch
problem, not silently substitute the mock feed's much shorter synthetic
history. For each pair: builds (features, label) rows via
`build_training_examples`, splits them **chronologically** (never
shuffled — a random split would leak future rows into the training set),
fits a RandomForestClassifier, prints a holdout accuracy (`model.score()`,
a single batched call — fast regardless of tree count), and persists.

Deliberately does NOT also run a walk-forward backtest of the freshly-saved
model over the full fetched history: an earlier version of this script did
exactly that (`run_prediction_backtest(..., strategy=MLStrategy(...))`)
and it silently re-tested the model on the ~80% of candles it was JUST
trained on, alongside the true 20% holdout — producing a wildly inflated,
untrustworthy "walk-forward accuracy" (83.2%, against a genuine holdout
accuracy of 53.7% for the same run) rather than an honest one. It was also
slow regardless (`evaluate()` once per historical candle, individually,
not batched — minutes per pair). The `holdout_accuracy` printed below,
computed via `model.score()` on the chronologically-held-out slice only,
is the trustworthy number — see decisions.md for the full incident.
"""

import argparse
import asyncio
import logging
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier

from app.core.config import get_settings
from app.core.constants import Symbol, Timeframe
from app.feeds.twelve_data_provider import TwelveDataProvider
from app.ml.dataset import build_training_examples

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)

_HISTORY_COUNT = 5000  # Twelve Data's free-tier max per request, costing exactly 1 API credit regardless
_TRAIN_SPLIT_RATIO = 0.8
_MIN_TRAINING_EXAMPLES = 200

_N_ESTIMATORS = 200
_MAX_DEPTH = 6
_MIN_SAMPLES_LEAF = 20
_RANDOM_STATE = 42


async def main() -> None:
    args = _parse_args()
    settings = get_settings()
    if not settings.twelve_data_api_key:
        raise SystemExit("TWELVE_DATA_API_KEY is not set — training needs real historical data.")

    model_dir = Path(settings.ml_model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    symbols = [args.symbol] if args.symbol is not None else settings.symbols
    timeframes = [args.timeframe] if args.timeframe is not None else settings.timeframes

    provider = TwelveDataProvider(api_key=settings.twelve_data_api_key)
    try:
        for symbol in symbols:
            for timeframe in timeframes:
                await _train_one(provider, model_dir, symbol, timeframe)
    finally:
        await provider.disconnect()


async def _train_one(
    provider: TwelveDataProvider, model_dir: Path, symbol: Symbol, timeframe: Timeframe
) -> None:
    print(f"\n=== Training {symbol.value}/{timeframe.value} ===")
    candles = await provider.fetch_history(symbol, timeframe, _HISTORY_COUNT)

    features, labels = build_training_examples(symbol, timeframe, candles)
    if len(features) < _MIN_TRAINING_EXAMPLES:
        print(f"Skipping: only {len(features)} usable training examples (need >= {_MIN_TRAINING_EXAMPLES})")
        return

    split_index = int(len(features) * _TRAIN_SPLIT_RATIO)
    X_train, y_train = features[:split_index], labels[:split_index]
    X_test, y_test = features[split_index:], labels[split_index:]

    model = RandomForestClassifier(
        n_estimators=_N_ESTIMATORS,
        max_depth=_MAX_DEPTH,
        min_samples_leaf=_MIN_SAMPLES_LEAF,
        class_weight="balanced",
        random_state=_RANDOM_STATE,
    )
    model.fit(X_train, y_train)

    holdout_accuracy = model.score(X_test, y_test) if X_test else None
    print(f"Training examples: {len(X_train)}  Holdout examples: {len(X_test)}")
    print(f"Holdout accuracy: {holdout_accuracy:.1%}" if holdout_accuracy is not None else "Holdout accuracy: n/a")

    model_path = model_dir / f"{symbol.value}_{timeframe.value}.joblib"
    joblib.dump(model, model_path)
    print(f"Saved: {model_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", type=Symbol, choices=list(Symbol), default=None, help="Defaults to every configured symbol.")
    parser.add_argument(
        "--timeframe", type=Timeframe, choices=list(Timeframe), default=None, help="Defaults to every configured timeframe."
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
