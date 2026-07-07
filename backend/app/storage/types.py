"""Custom SQLAlchemy column types shared across ORM models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Always round-trips as a UTC-aware datetime.

    SQLite has no native timestamp-with-timezone type; the stdlib sqlite3
    driver stores/reads DATETIME as naive strings, silently dropping
    tzinfo on the way back out. Every datetime in this codebase is UTC
    (Tick/Candle/Prediction/Signal all use datetime.now(UTC)), so this
    type enforces that on write (rejects naive input) and restores
    tzinfo=UTC on read, so comparisons against a fresh datetime.now(UTC)
    never raise "can't compare offset-naive and offset-aware datetimes".
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
