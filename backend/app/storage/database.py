"""Async SQLAlchemy engine/session setup, sourced from Settings.database_url.

Engine and session-factory construction is lazy (lru_cache) rather than a
module-level side effect, so importing this module never opens a database
connection — tests can override get_session() per-request without needing
to touch process-wide state.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(database_url: str) -> None:
    if "sqlite" not in database_url:
        return
    path_part = database_url.split("///", 1)[-1]
    if path_part and path_part != ":memory:":
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    _ensure_sqlite_dir(settings.database_url)
    return create_async_engine(settings.database_url)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def init_models() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
