# Project context

> Read this before any project work. Everything stack-specific lives here so the
> portable kit stays generic.

## Stack — framework & runtime

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, SQLite (v1), Pydantic v2 / pydantic-settings, pandas.
- **Frontend:** React 19, Vite, TypeScript (strict), Tailwind CSS v4 (via `@tailwindcss/vite`, no separate config file needed).
- **Monorepo:** `backend/` and `frontend/` are independent projects in the same repo — no shared package manager or build step between them.

## Solution & folder layout

- `backend/app/core/` — `Settings` (env-driven config), enums (`Symbol`, `Timeframe`, `Direction`, `FeedStatus`), logging, exceptions.
- `backend/app/feeds/` — `MarketDataProvider` adapter interface + implementations (`MockMarketDataProvider` in v1; TradingView/broker adapters later). Nothing outside this package should depend on a concrete provider.
- `backend/app/storage/` — `database.py` (lazy async engine/session factory via `get_engine()`/`get_session_factory()`, both `lru_cache`d — never construct the engine at import time), `models.py` (`CandleORM`, `PredictionORM` — the latter append-only, rows are never updated). `repositories/candle_repository.py` translates both ways — reads (`get_recent`/`get_latest`) return domain `Candle` objects, never `CandleORM`, since Phase 4 needed the domain type in two call sites (a router and `PredictionService`). `repositories/prediction_repository.py` only has one caller (the predictions router) so far, so its reads still return `PredictionORM` rows — apply the same domain-return refactor there if/when a second caller needs it (YAGNI: don't do it speculatively).
- `backend/app/features/` — `indicators.py` (SMA fast/slow, RSI, ATR, momentum, volatility — vectorized pandas functions, periods are named constants), `structure.py` (`SwingPoint`, `detect_swing_points`, `detect_break_of_structure`), `feature_builder.py` (`build_feature_set` — the only entry point `app/prediction/` should import from this package; combines indicators + structure into one `FeatureSet` from a window of closed candles).
- `backend/app/prediction/` — `base.py` (`Prediction`/`PredictionSignal` dataclasses + the `PredictionStrategy` ABC), `rule_based.py` (`RuleBasedStrategy` — v1 weighted-vote heuristic over structure/trend/RSI/momentum; see [docs/prediction-method.md](../../docs/prediction-method.md) for the scoring writeup), `engine.py` (`PredictionEngine` — builds features, calls the strategy, assembles a `Prediction`; persistence is the caller's job, not the engine's). An ML strategy lands here later behind the same `PredictionStrategy` interface.
- `backend/app/services/` — `candle_aggregator.py` (pure, no I/O — rolls ticks into per-timeframe OHLC `Candle`s), `feed_service.py` (owns the provider lifecycle; per tick: caches latest price + broadcasts a price message; per closed candle: persists it, then calls `PredictionService.on_candle_closed`), `connection_manager.py` (registry of live WebSocket clients; best-effort broadcast — drops a client whose `send_json` fails rather than failing the whole broadcast), `broadcast_service.py` (translates domain `Tick`/`Prediction`/`FeedStatus` into the `app/schemas/websocket_messages.py` wire types; the only thing that imports `ConnectionManager`), `prediction_service.py` (`on_candle_closed` — event-driven prediction scheduling: a new candle close *is* the schedule, no polling scheduler; see [[event-driven-prediction-scheduling]] in decisions.md).
- `backend/app/api/routers/` — REST endpoints, one router per resource: `health.py`, `symbols.py`, `prices.py` (latest tick per symbol, from `FeedService`'s in-memory cache), `candles.py` (recent closed candles from SQLite), `predictions.py` (`GET .../latest` computes a fresh prediction on demand from the most recent candles and logs it; `GET .../history` reads back already-logged predictions without recomputing), `websocket.py` (`/ws` — broadcast-only; sends the connecting client `FeedService.status` immediately on connect, then just drains incoming messages to keep the socket alive). Symbol/timeframe are typed enum path params everywhere, not free text.
- `backend/app/api/dependencies.py` — shared FastAPI dependency accessors: `get_feed_service` (reads `request.app.state.feed_service`), `get_prediction_engine` (`lru_cache`d — same lazy-construction pattern as `storage/database.py`, so it stays import-side-effect-free and overridable in tests; safe only because `RuleBasedStrategy`/`PredictionEngine` are stateless — move to `app.state` if a future strategy carries state).
- `backend/app/main.py` — `create_app()` factory; the mock feed is started/stopped via a FastAPI `lifespan` context manager, not `on_event` (deprecated). No module-level side effects beyond the final `app = create_app()`, so tests can build isolated instances.
- `backend/pytest.ini` — sets `pythonpath = .` (so `app.*` imports resolve regardless of invocation cwd) and `asyncio_mode = auto` (async `def test_...` functions run without a `@pytest.mark.asyncio` decorator on every one).
- `frontend/src/components/` — small, single-purpose components grouped by feature area (`dashboard/`, `chart/`, `history/`).
- `frontend/src/pages/`, `hooks/`, `services/`, `types/`, `store/` — added as each phase needs them; not all exist yet.
- `docs/architecture.md` — full architecture + phase plan; keep in sync when the design changes.

## Key libraries

- **Backend config:** `pydantic-settings` — single `Settings` class in `app/core/config.py`, cached via `get_settings()`. Env vars map case-insensitively to field names (no prefix); list fields (`cors_origins`, `symbols`, `timeframes`) accept comma-separated strings via a `field_validator`.
- **Backend numerics:** `pandas`/`numpy` for indicator math (`app/features/indicators.py`) — vectorized over Series, not manual loops. Indicator periods (RSI/ATR 14, SMA 10/30, momentum 10, volatility 20) are named module constants, not tuned yet; revisit once backtesting (Phase 9) can score them.
- **Backend data access:** SQLAlchemy 2.0 async engine + `aiosqlite` driver (`sqlite+aiosqlite:///...`) — kept async to match the rest of the backend's async-throughout convention; see [[async-sqlalchemy-decision]] in decisions.md. Repositories own sessions; no ORM models leak past the repository layer — routers/services only ever see the domain `Candle`/`Tick` dataclasses from `app.feeds.base`.
- **Backend testing:** pytest + pytest-asyncio + FastAPI `TestClient`/httpx.
- **Frontend styling:** Tailwind v4 utility classes directly in JSX; no CSS Modules/styled-components.
- **Frontend data fetching (planned):** a dedicated fetching layer in `services/apiClient.ts` + a WebSocket hook (`useMarketSocket`) — not a hand-rolled `useEffect` fetch per component.
- **Frontend charting (planned, Phase 6):** `lightweight-charts`.

## Conventions & namespaces

- **Backend:** modules import as `app.<package>.<module>`; async I/O throughout (no sync-over-async); enums (`Symbol`, `Timeframe`, `Direction`, `FeedStatus`) instead of magic strings anywhere a value is one of a fixed set.
- **Frontend:** camelCase functions/variables, PascalCase components/types, kebab-case CSS classes/ids; TypeScript `strict: true` is enabled in `tsconfig.app.json`.
- **Feed provider swap:** adding a new market data source means a new class implementing `MarketDataProvider` in `app/feeds/`, selected via `Settings.feed_provider` — never a branch ladder in calling code.
- **No auto-trading:** there is no execution/order-placement module in this codebase by design, not as a disabled feature. Do not add one without an explicit, separate decision from the project owner.

## Build & run

- **Backend install:** `cd backend && py -m venv .venv && ./.venv/Scripts/pip install -r requirements.txt`
- **Backend run:** `./.venv/Scripts/uvicorn app.main:app --reload` (serves `http://localhost:8000`, health check at `/health`)
- **Backend test:** `./.venv/Scripts/pytest` (test suite added starting Phase 1)
- **Frontend install:** `cd frontend && npm install`
- **Frontend run:** `npm run dev` (serves `http://localhost:5173`)
- **Frontend build:** `npm run build` (runs `tsc -b` then `vite build`)
- **Frontend lint:** `npm run lint` (oxlint)

## Related project docs

- Full architecture and phase plan: [docs/architecture.md](../../docs/architecture.md)
- Rule-based prediction scoring (v1): [docs/prediction-method.md](../../docs/prediction-method.md)
- Product spec: [PROJECT.md](../../PROJECT.md)
- Tracked technical debt: [tech-debt.md](tech-debt.md)
- Decisions & learnings (project memory): [decisions.md](decisions.md)
