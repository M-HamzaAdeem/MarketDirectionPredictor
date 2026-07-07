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

### 2026-07-07 — SignalORM's in-place mutation is bounded to outcome fields only
- **Decision / learning:** `SignalORM` is the one table in this schema mutated after insert (`SignalRepository.update_outcome` overwrites `status`/`closed_at`/`realized_rr`) — every other table (`CandleORM`, `PredictionORM`) is append-only. This was reviewed and accepted: the plan fields set at OPEN (`entry`/`stop`/`target`/`reason`/`details`) are never touched by `update_outcome`, only the outcome fields transition, so "what did we predict and why" is never lost — only "did it resolve" changes in place.
- **Why:** A signal genuinely has a lifecycle (open → win/loss/expired); modeling that as an in-place status transition is simpler than an append-only events log, and there's no current requirement (partial exits, intermediate observations) that needs one.
- **Implications:** If Phase 9 backtesting or a future feature needs partial-exit modeling or a replay of intermediate price observations against a signal, migrate to a separate append-only `signal_outcome_events` table behind `SignalRepository` — the repository already fully encapsulates the mutation (`update_outcome` is the only call site), so this would be a contained, strangler-friendly change, not a rewrite. Don't build that table now (YAGNI) — this entry exists so the trigger condition is recorded instead of rediscovered.

### 2026-07-07 — CandleCloseHandler protocol: FeedService holds a handler list, not named params
- **Decision / learning:** Adding the ICT pipeline meant `FeedService` needed to notify two more things on every closed candle (`SignalTracker`, `SignalService`) on top of the existing `PredictionService` — three total. Rather than grow the constructor to a sixth/seventh named parameter, `FeedService` now takes `candle_close_handlers: list[CandleCloseHandler]`, where `CandleCloseHandler` (`app/services/candle_close_handler.py`) is a structural `Protocol` with one method, `on_candle_closed(candle) -> None`. `PredictionService`, `SignalTracker`, and `SignalService` all already matched this shape without any inheritance change (Python protocols are duck-typed).
- **Why:** Three concrete implementations wanting the same hook is the threshold this project already uses elsewhere for extracting a shared abstraction (see the `code-reviewer`'s standing rule: a second real caller justifies it). A fourth handler in the future is now a one-line addition to the list built in `main.py`'s `_lifespan` — `FeedService` itself never needs to change again for this reason.
- **Implications:** Any new "react to a candle close" feature should implement `CandleCloseHandler` and be added to the `candle_close_handlers` list in `main.py`, not given a new named constructor parameter on `FeedService`.

### 2026-07-07 — UTCDateTime column type: SQLite silently drops tzinfo on read-back
- **Decision / learning:** `SignalRepository` tests (`test_update_outcome_resolves_a_signal_to_win`, `test_get_recent_returns_ascending_order_by_opened_at`) failed comparing a round-tripped datetime against a constructed `tzinfo=UTC` one — SQLite's stdlib driver stores `DateTime(timezone=True)` values as naive strings and returns naive `datetime` objects, silently dropping tzinfo. This was a **pre-existing** bug affecting `CandleORM.open_time`/`close_time` and `PredictionORM.timestamp` too — it just hadn't surfaced because no earlier test compared a round-tripped datetime object directly against a tz-aware one (JSON-serialized timestamps and `.close`/`.price` field comparisons masked it). Fixed at the root with a `UTCDateTime` `TypeDecorator` (`backend/app/storage/types.py`) that rejects naive input on write and reattaches `tzinfo=UTC` on read; all `DateTime(timezone=True)` columns across `CandleORM`, `PredictionORM`, and `SignalORM` now use it.
- **Why:** The Signal outcome-tracker (next task) needs `datetime.now(UTC) - signal.opened_at` to compute expiry — a naive/aware mismatch there raises `TypeError` immediately, not just a wrong-but-silent value, so this had to be fixed before that work rather than deferred.
- **Implications:** Any new datetime column must use `UTCDateTime` from `app.storage.types`, never `DateTime(timezone=True)` directly. All datetimes in this codebase are UTC by convention (`datetime.now(UTC)`) — `UTCDateTime` enforces that at the write boundary rather than silently accepting naive datetimes that would corrupt comparisons later.

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
