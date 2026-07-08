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
from app.storage.migrations import add_missing_columns


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
    # Base.metadata is only populated once every module defining an ORM
    # class has actually been imported somewhere in the process — this
    # import guarantees that regardless of what else has (or hasn't) been
    # imported yet, rather than relying on import order elsewhere in the
    # app to have already pulled models.py in as a side effect.
    from app.storage import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all only creates missing tables; this adds any column an
        # existing table is missing, so a model gaining a field never again
        # requires deleting the whole database — see app/storage/migrations.py.
        await add_missing_columns(conn, Base)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
