"""Domain enums shared across the backend.

Using enums instead of free-text strings keeps symbol/timeframe/direction
values validated at the API boundary and avoids magic strings elsewhere.
"""

from enum import Enum


class Symbol(str, Enum):
    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    AUDUSD = "AUDUSD"


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class FeedStatus(str, Enum):
    MOCK = "mock"
    LIVE = "live"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


class FeedProvider(str, Enum):
    MOCK = "mock"
    TWELVE_DATA = "twelve_data"


class DataSource(str, Enum):
    """Which independent pipeline a candle/prediction/signal/WS message
    belongs to — Twelve Data and TradingView run simultaneously, each with
    its own tables and handler pipeline; never mixed at the storage layer."""

    TWELVE_DATA = "twelve_data"
    TRADINGVIEW = "tradingview"


class PredictionStrategyKind(str, Enum):
    RULE_BASED = "rule_based"
    ML = "ml"
