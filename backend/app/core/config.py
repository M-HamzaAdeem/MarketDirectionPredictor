"""Application settings, sourced from environment variables / .env.

A single Settings object is the only place feed provider, symbols,
timeframes, and CORS origins are configured — nothing downstream hardcodes
these values, so swapping providers or adding a symbol is a config change.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import Symbol, Timeframe


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./data/market_predictor.db"
    feed_provider: str = "mock"
    # Only used by MockMarketDataProvider; a real feed always runs at 1.0
    # (actual market time). 60.0 = 1 real second per virtual minute, so a
    # 1H candle closes in ~60s and a 4H candle in ~4min — practical for
    # local dev/demo without waiting on real wall-clock hours.
    mock_time_acceleration: float = Field(default=60.0, gt=0)
    cors_origins: list[str] = ["http://localhost:5173"]
    symbols: list[Symbol] = [Symbol.XAUUSD, Symbol.EURUSD, Symbol.AUDUSD]
    timeframes: list[Timeframe] = [Timeframe.M1, Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4]

    @field_validator("cors_origins", "symbols", "timeframes", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
