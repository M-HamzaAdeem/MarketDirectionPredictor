"""Turns a `FeatureSet` into the fixed-size numeric vector the ML strategy
trains on and predicts from. The exact same transform is used at training
time (`app/ml/dataset.py`) and at inference time (`MLStrategy.evaluate`) —
any drift between the two would silently corrupt predictions.

Every value is relative/normalized, never a raw price level: `sma_fast`/
`sma_slow` are absolute prices that drift a great deal over a multi-month
or multi-year training window (XAUUSD alone moved from ~2350 to ~4100+
across the backtest's history), and tree-based models don't extrapolate
outside the numeric range they were trained on. A model that memorized
"price around 2350 = X" would be useless once price moves far outside
that range — the SMA *spread*, RSI, and normalized ATR/momentum/
volatility don't have this problem.
"""

from app.core.constants import Direction
from app.features.feature_builder import FeatureSet

_STRUCTURE_ENCODING: dict[Direction, float] = {
    Direction.BULLISH: 1.0,
    Direction.BEARISH: -1.0,
    Direction.NEUTRAL: 0.0,
}

FEATURE_NAMES = ["sma_spread_pct", "rsi", "atr_pct", "momentum_pct", "volatility_pct", "structure"]


def feature_vector(features: FeatureSet) -> list[float] | None:
    """Returns `None` if any required indicator isn't available yet (not
    enough candle history) — the caller must skip this row/prediction
    rather than feed a partial vector into the model."""
    if (
        features.sma_fast is None
        or features.sma_slow is None
        or features.rsi is None
        or features.atr is None
        or features.momentum is None
        or features.volatility is None
        or features.latest_close == 0
        or features.sma_slow == 0
    ):
        return None

    return [
        (features.sma_fast - features.sma_slow) / features.sma_slow,
        features.rsi,
        features.atr / features.latest_close,
        features.momentum / features.latest_close,
        features.volatility / features.latest_close,
        _STRUCTURE_ENCODING[features.structure],
    ]
