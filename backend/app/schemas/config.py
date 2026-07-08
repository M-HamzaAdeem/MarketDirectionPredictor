from pydantic import BaseModel

from app.core.constants import Symbol, Timeframe


class ConfigOut(BaseModel):
    """A curated, read-only view of the effective configuration — both
    `Settings` fields and the strategy parameters that live as module
    constants in features/prediction (not env-configurable yet; there's no
    reload mechanism for them). Deliberately not a blanket dump of every
    `Settings` field, so a new setting isn't silently made public just by
    existing — see docs/architecture.md and decisions.md."""

    # Feed
    feed_provider: str
    mock_time_acceleration: float
    symbols: list[Symbol]
    timeframes: list[Timeframe]

    # ICT signal pipeline (see docs/signal-method.md)
    min_risk_reward: float
    ote_shallow_ratio: float
    ote_deep_ratio: float
    stop_atr_buffer_multiplier: float
    impulse_atr_multiplier: float
    signal_expiry_days: float

    # Direction prediction — which strategy is behind /predictions
    # (see docs/prediction-method.md and app/prediction/factory.py)
    prediction_strategy: str

    # Phase 3 rule-based prediction (see docs/prediction-method.md)
    rsi_bullish_threshold: float
    rsi_bearish_threshold: float
    sma_fast_period: int
    sma_slow_period: int
    rsi_period: int
    atr_period: int
    momentum_period: int
    volatility_period: int
