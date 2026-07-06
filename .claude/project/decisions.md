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

### 2026-07-06 — TD-1 resolved: session factory now constructor-injected into FeedService/PredictionService
- **Decision / learning:** TD-1 (accepted in Phase 1) deferred injecting `get_session_factory()` into `FeedService.__init__`, on the grounds that no test yet existed over the feed loop's write path. Phase 4 added `PredictionService`, which repeated the exact same direct-call pattern — and the resulting integration test (`test_prediction_service.py`) had to `monkeypatch` the module-level `get_session_factory` to isolate it, which is exactly the cost TD-1 predicted, now materialized. Rather than defer a third time, both `FeedService` and `PredictionService` now take `session_factory: async_sessionmaker[AsyncSession]` as a constructor parameter; `main.py`'s `_lifespan` resolves `get_session_factory()` once and passes the same instance to both.
- **Why:** A real cost (a monkeypatch-based test working around a hidden dependency) beats an estimated one — fixing it now was cheaper than writing a second workaround and letting the register accumulate a third repetition of the same debt.
- **Implications:** Any new service that persists via a session needs its own `async_sessionmaker` constructor parameter, not a direct `get_session_factory()` call — that accessor should now only be called from `main.py`'s composition root (`_lifespan`) and from `storage/database.get_session` (the FastAPI dependency). TD-1 removed from tech-debt.md.

### 2026-07-06 — event-driven-prediction-scheduling: candle close drives prediction runs, not a polling scheduler
- **Decision / learning:** Phase 4 wires `FeedService` to call `PredictionService.on_candle_closed()` every time `CandleAggregator` closes a candle, rather than adding an APScheduler-style polling loop (PROJECT.md's stack list mentions APScheduler as an option, but doesn't require it).
- **Why:** A fresh prediction is only meaningful once a new candle has actually closed — polling on a fixed interval would either recompute against unchanged data (wasted work, and duplicate near-identical log rows) or need its own logic to detect "has a new candle closed since I last ran," which the tick stream already tells us for free. The tick stream is the natural schedule.
- **Implications:** There's still no throttling on the REST `GET /predictions/{symbol}/{timeframe}/latest` endpoint from Phase 3 — it computes+logs on every call regardless of candle state, so calling it repeatedly still produces duplicate log rows (a pre-existing, documented v1 behavior, now joined by the automatic candle-close predictions). If a real polling scheduler is ever needed (e.g. a future feed that doesn't emit a clean tick stream), add it as a new `services/` module behind the same `PredictionService.on_candle_closed`-style entry point — don't duplicate the prediction-triggering logic inside `FeedService`.

### 2026-07-06 — async-sqlalchemy-decision: SQLAlchemy async engine + aiosqlite over sync SQLAlchemy
- **Decision / learning:** The Phase 1 storage layer (`backend/app/storage/database.py`) uses SQLAlchemy's async engine with the `aiosqlite` driver (`sqlite+aiosqlite:///...`), not the default synchronous SQLite driver.
- **Why:** The candle-ingestion loop (`FeedService._run`) is an `async for` over the tick stream; a sync DB call there would block the event loop on every candle close. Matches the "async I/O throughout, no sync-over-async" convention already set in Phase 0.
- **Implications:** Any future repository/table must go through the async engine (`get_engine()`/`get_session_factory()` in `storage/database.py`, both lazily constructed and `lru_cache`d — never build the engine at import time, or tests lose the ability to override `get_session()` per-request). `DATABASE_URL` must always carry the `+aiosqlite` (or future Postgres equivalent's async driver) suffix. If SQLite is later swapped for Postgres, use `asyncpg`, not `psycopg2`.
