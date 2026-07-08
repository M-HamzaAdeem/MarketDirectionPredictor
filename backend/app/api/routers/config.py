"""Read-only view of the effective configuration. There is no PATCH/PUT —
`Settings` is loaded once at process startup (`lru_cache`d) and the
strategy constants below are plain module constants, so nothing here can
actually be changed at runtime yet. This endpoint exists for transparency
(a trader should be able to see what R:R floor/OTE zone/etc. governed the
signals they're looking at), not configuration management.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.features.indicators import (
    DEFAULT_ATR_PERIOD,
    DEFAULT_MOMENTUM_PERIOD,
    DEFAULT_RSI_PERIOD,
    DEFAULT_SMA_FAST_PERIOD,
    DEFAULT_SMA_SLOW_PERIOD,
    DEFAULT_VOLATILITY_PERIOD,
)
from app.features.fibonacci import DEFAULT_OTE_DEEP_RATIO, DEFAULT_OTE_SHALLOW_RATIO
from app.features.poi import DEFAULT_IMPULSE_ATR_MULTIPLIER
from app.prediction.rule_based import RSI_BEARISH_THRESHOLD, RSI_BULLISH_THRESHOLD
from app.prediction.signal_builder import DEFAULT_STOP_ATR_BUFFER_MULTIPLIER, MIN_RISK_REWARD
from app.schemas.config import ConfigOut
from app.services.signal_tracker import DEFAULT_EXPIRY

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config(settings: Settings = Depends(get_settings)) -> ConfigOut:
    return ConfigOut(
        feed_provider=settings.feed_provider,
        mock_time_acceleration=settings.mock_time_acceleration,
        symbols=settings.symbols,
        timeframes=settings.timeframes,
        min_risk_reward=MIN_RISK_REWARD,
        ote_shallow_ratio=DEFAULT_OTE_SHALLOW_RATIO,
        ote_deep_ratio=DEFAULT_OTE_DEEP_RATIO,
        stop_atr_buffer_multiplier=DEFAULT_STOP_ATR_BUFFER_MULTIPLIER,
        impulse_atr_multiplier=DEFAULT_IMPULSE_ATR_MULTIPLIER,
        signal_expiry_days=DEFAULT_EXPIRY / timedelta(days=1),
        prediction_strategy=settings.prediction_strategy,
        rsi_bullish_threshold=RSI_BULLISH_THRESHOLD,
        rsi_bearish_threshold=RSI_BEARISH_THRESHOLD,
        sma_fast_period=DEFAULT_SMA_FAST_PERIOD,
        sma_slow_period=DEFAULT_SMA_SLOW_PERIOD,
        rsi_period=DEFAULT_RSI_PERIOD,
        atr_period=DEFAULT_ATR_PERIOD,
        momentum_period=DEFAULT_MOMENTUM_PERIOD,
        volatility_period=DEFAULT_VOLATILITY_PERIOD,
    )
