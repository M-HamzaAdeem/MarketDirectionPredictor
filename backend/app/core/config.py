"""Application settings, sourced from environment variables / .env.

A single Settings object is the only place feed provider, symbols,
timeframes, and CORS origins are configured — nothing downstream hardcodes
these values, so swapping providers or adding a symbol is a config change.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import Symbol, Timeframe


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./data/market_predictor.db"
    feed_provider: str = "mock"
    cors_origins: list[str] = ["http://localhost:5173"]
    symbols: list[Symbol] = [Symbol.XAUUSD, Symbol.EURUSD, Symbol.AUDUSD]
    timeframes: list[Timeframe] = [Timeframe.M1, Timeframe.M5, Timeframe.M15]

    @field_validator("cors_origins", "symbols", "timeframes", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
