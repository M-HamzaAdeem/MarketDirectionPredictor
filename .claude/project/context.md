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
- `backend/app/storage/` — `database.py` (lazy async engine/session factory via `get_engine()`/`get_session_factory()`, both `lru_cache`d — never construct the engine at import time), `models.py` (`CandleORM`), `repositories/candle_repository.py` (the only place that translates between `CandleORM` and the domain `Candle` dataclass). Prediction repository lands in Phase 3.
- `backend/app/features/` — `indicators.py` (SMA fast/slow, RSI, ATR, momentum, volatility — vectorized pandas functions, periods are named constants), `structure.py` (`SwingPoint`, `detect_swing_points`, `detect_break_of_structure`), `feature_builder.py` (`build_feature_set` — the only entry point Phase 3's prediction engine should import from this package; combines indicators + structure into one `FeatureSet` from a window of closed candles).
- `backend/app/prediction/` — `PredictionStrategy` interface + rule-based v1 implementation. Lands in Phase 3.
- `backend/app/services/` — `candle_aggregator.py` (pure, no I/O — rolls ticks into per-timeframe OHLC `Candle`s; this is where aggregation-rule unit tests live), `feed_service.py` (thin orchestration: owns the provider lifecycle, routes ticks to the aggregator, persists closed candles, caches latest price in memory). WebSocket broadcast lands in Phase 4.
- `backend/app/api/routers/` — REST endpoints, one router per resource: `health.py`, `symbols.py`, `prices.py` (latest tick per symbol, from `FeedService`'s in-memory cache), `candles.py` (recent closed candles from SQLite; symbol/timeframe are typed enum path params, not free text).
- `backend/app/api/dependencies.py` — shared FastAPI dependency accessors (e.g. `get_feed_service`, which reads `request.app.state.feed_service`).
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
- Product spec: [PROJECT.md](../../PROJECT.md)
- Tracked technical debt: [tech-debt.md](tech-debt.md)
- Decisions & learnings (project memory): [decisions.md](decisions.md)
