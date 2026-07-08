from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.storage.database import Base, init_models
from app.storage.migrations import add_missing_columns

# Base.metadata is only populated once every module defining an ORM class
# has been imported somewhere in the process. init_models() does this
# lazily itself, but the tests below call add_missing_columns() directly
# (not through init_models()), so this test file must not depend on some
# *other* test module happening to import models.py first.
from app.storage import models  # noqa: F401,E402


async def test_add_missing_columns_adds_a_column_missing_from_an_existing_table(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    async with engine.begin() as conn:
        # Simulate an older schema: hand-create the signals table missing
        # `created_at`, the way a pre-2026-07-08 database would look.
        await conn.execute(
            text(
                """
                CREATE TABLE signals (
                    id INTEGER PRIMARY KEY,
                    symbol VARCHAR(16),
                    entry_timeframe VARCHAR(4),
                    direction VARCHAR(8),
                    entry FLOAT,
                    stop FLOAT,
                    target FLOAT,
                    risk_reward FLOAT,
                    status VARCHAR(8),
                    reason VARCHAR(512),
                    details TEXT,
                    opened_at DATETIME,
                    closed_at DATETIME,
                    realized_rr FLOAT
                )
                """
            )
        )
        await conn.execute(
            text(
                "INSERT INTO signals "
                "(symbol, entry_timeframe, direction, entry, stop, target, risk_reward, status, reason, "
                "details, opened_at) "
                "VALUES ('XAUUSD', '15m', 'bullish', 100.0, 95.0, 110.0, 2.0, 'open', 'test', '{}', "
                "'2026-01-01 00:00:00')"
            )
        )

    async with engine.begin() as conn:
        await add_missing_columns(conn, Base)

    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT created_at FROM signals"))
        rows = result.fetchall()

    assert len(rows) == 1
    # The pre-existing row genuinely never had a value for this column —
    # NULL is the honest answer, not a fabricated backfilled timestamp.
    assert rows[0][0] is None

    await engine.dispose()


async def test_add_missing_columns_is_a_noop_against_a_freshly_created_schema(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await add_missing_columns(conn, Base)  # every column already exists — must not raise

    await engine.dispose()


async def test_init_models_runs_the_migration_check_without_error(tmp_path, monkeypatch) -> None:
    # init_models() reads Settings via get_engine()/get_settings(), both
    # process-wide lru_cache singletons — point them at a throwaway file
    # for this test rather than the real configured database.
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    from app.core.config import get_settings
    from app.storage.database import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    await init_models()
    await init_models()  # second run must also be a no-op, not an error

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
