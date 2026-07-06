# Decisions & learnings

Companion to [context.md](context.md) and [tech-debt.md](tech-debt.md). This is the project's
durable **memory** — the *why* behind choices and the lessons learned — kept in git so the
whole team (and Claude) can rely on it later, not rediscover it.

## What belongs here

- A non-obvious **decision** with trade-offs (an approach chosen over alternatives, a library
  selected, a pattern adopted) — and *why*.
- A **learning / gotcha** that cost time and would otherwise be hit again.
- A convention adopted mid-project that isn't yet reflected in `context.md`.
- A **rejected** approach and the reason, so it isn't re-proposed.

## What doesn't

- Routine changes — those live in git history and the changelog.
- Accepted rule violations — those go in [tech-debt.md](tech-debt.md).
- Personal or cross-project facts — those belong in your own Claude Code memory, not this
  shared, committed file.

## How to use

Append a dated entry when a durable decision or learning emerges (the `architect-reviewer`
records accepted **design** decisions here too, mirroring how reviewers append to
`tech-debt.md`). Keep entries short and link the PR/issue/files. Newest first.

## Log

<!-- Template — copy for each entry:

### YYYY-MM-DD — <short title>
- **Decision / learning:** what was decided or learned.
- **Why:** the reasoning / trade-off.
- **Implications:** what to do (or avoid) going forward; links to PR/issue/files.
-->

### 2026-07-06 — async-sqlalchemy-decision: SQLAlchemy async engine + aiosqlite over sync SQLAlchemy
- **Decision / learning:** The Phase 1 storage layer (`backend/app/storage/database.py`) uses SQLAlchemy's async engine with the `aiosqlite` driver (`sqlite+aiosqlite:///...`), not the default synchronous SQLite driver.
- **Why:** The candle-ingestion loop (`FeedService._run`) is an `async for` over the tick stream; a sync DB call there would block the event loop on every candle close. Matches the "async I/O throughout, no sync-over-async" convention already set in Phase 0.
- **Implications:** Any future repository/table must go through the async engine (`get_engine()`/`get_session_factory()` in `storage/database.py`, both lazily constructed and `lru_cache`d — never build the engine at import time, or tests lose the ability to override `get_session()` per-request). `DATABASE_URL` must always carry the `+aiosqlite` (or future Postgres equivalent's async driver) suffix. If SQLite is later swapped for Postgres, use `asyncpg`, not `psycopg2`.
