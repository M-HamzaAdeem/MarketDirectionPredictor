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

### 2026-07-08 — websocket-hook-at-app-level: useMarketSocket moved from DashboardPage to App
- **Decision / learning:** Phase 7 added `react-router-dom` with a second route (`/settings`). `useMarketSocket()` moved from being called inside `DashboardPage` to being called once in `App.tsx`, above `<Routes>`, and `DashboardPage`/`SettingsPage` both render through the new `AppShell` layout component instead of duplicating header/nav/disclaimer markup.
- **Why:** A hook called inside a routed page unmounts (and its WebSocket connection closes) every time the user navigates away from that page, then has to reconnect and re-bootstrap the whole live store on the way back. Since the WebSocket feeds global state (`marketStore.ts`) that both the dashboard and any future page could use, it belongs above the router, not inside one specific page. Verified live in-browser: navigating Dashboard → Settings → Dashboard accumulated more predictions/candles across the round trip with zero reconnect, and zero console errors either direction.
- **Implications:** Any future page that needs live WebSocket-pushed state reads it straight from `marketStore.ts` — it must never call `useMarketSocket()` itself. If a page-specific WebSocket subscription is ever needed (e.g. a symbol-specific channel), extend the store/hook rather than instantiating a second socket connection.

### 2026-07-08 — Performance stats computed client-side, not a backend aggregation endpoint
- **Decision / learning:** `PerformanceStats` (win rate, average realized R:R, totals) is computed in the frontend (`utils/performanceStats.ts`) from the already-fetched `GET /signals/{symbol}/history` response, not via a dedicated backend `/signals/{symbol}/stats` endpoint.
- **Why:** The only consumer is the Symbol Detail view, which already fetches the full history for the table directly above the stats. A backend aggregation endpoint would duplicate that same query for no new capability yet — YAGNI. Win rate deliberately excludes `expired`/`open` signals from the denominator (an expired signal never resolved to a clear outcome, so it shouldn't count against or for the rate); average realized R:R is over WIN/LOSS only.
- **Implications:** If a future view needs aggregate stats *without* also wanting the full history list (e.g. a global stats widget across all 3 symbols, or paginated history where fetching everything client-side stops being practical), add a real backend aggregation endpoint then — don't keep stretching the client-side computation to cover a case it isn't shaped for.

### 2026-07-07 — broadcast_signal's id-is-None guard is a runtime check, not a type, by choice
- **Decision / learning:** `BroadcastService.broadcast_signal` raises `ValueError` if `signal.id is None` rather than requiring a separate "PersistedSignal" type with a non-optional `id`. Both call sites (`SignalService` after `save()`, `SignalTracker` via `dataclasses.replace()` on a `Signal` read from `get_open()`) already structurally guarantee an `id` — the guard only fires on a coding regression.
- **Why:** A type-level fix (splitting `Signal` into pre/post-persistence variants) is the cleaner long-term shape, but it ripples through both repositories and every `Signal` consumer for a single call site. That's speculative structuring for one guard — YAGNI.
- **Implications:** If a second "must be persisted before use" boundary appears elsewhere, introduce the split type then, not now.

### 2026-07-07 — Zustand selector gotcha: derived arrays/objects need useShallow
- **Decision / learning:** `SignalFeed.tsx` crashed the dashboard (blank page, `"The result of getSnapshot should be cached to avoid an infinite loop"`) using `useMarketStore(selectOpenSignals)` where `selectOpenSignals` does `Object.values(state.signals).filter(...).sort(...)` — a new array every call. Zustand v5's `useSyncExternalStore`-based subscription sees a "changed" snapshot on every render (new array reference) and loops. Fixed by wrapping the selector: `useMarketStore(useShallow(selectOpenSignals))` from `zustand/react/shallow`, which compares the array's *elements* instead of its reference.
- **Why:** This only bites *derived* selectors (filter/map/sort producing a new container). Selectors that just read a stored slice directly (`state.feedStatus`, `state.prices[symbol]`) are fine as-is, since Zustand's `set` only replaces that reference when the slice actually changes.
- **Implications:** Any new Zustand selector in `marketStore.ts` that filters/maps/sorts/derives a new array or object must be wrapped in `useShallow` at every call site (not just once) — the store can't enforce this for you. Plain slice reads don't need it.

### 2026-07-07 — react-query for REST bootstrap, zustand for WebSocket-pushed state
- **Decision / learning:** The frontend uses two different state tools for two different data shapes: `@tanstack/react-query` for one-shot REST fetches that seed initial state (`useSymbols`, `useOpenSignalsBootstrap`), and `zustand` (`store/marketStore.ts`) for everything the WebSocket pushes live (prices, predictions, signal open/resolve events).
- **Why:** `.claude/rules/frontend.md` calls for a data-fetching library over hand-rolled `useEffect` fetches for server state — react-query fits REST cleanly (cache, fetch-once-on-mount). But WebSocket-pushed updates aren't "server state" in that pull/cache sense; they're push events the UI must apply as they arrive, which is exactly what a lightweight global store is for. Bootstrapping open signals via react-query and then having `useMarketSocket` update the same `zustand` slots (keyed by signal `id`) keeps both tools doing the job they're actually good at, rather than forcing one to do both.
- **Implications:** New REST-fetched data that doesn't change live → add a react-query hook. New WebSocket message types → add a store slice + dispatch case in `useMarketSocket.ts`, not a react-query hook.

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
