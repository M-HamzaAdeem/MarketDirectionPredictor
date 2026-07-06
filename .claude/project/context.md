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
- `backend/app/storage/` — SQLAlchemy models + repositories (candles, append-only predictions). Not yet created — lands in Phase 1.
- `backend/app/features/` — indicator math + market structure detection. Lands in Phase 2.
- `backend/app/prediction/` — `PredictionStrategy` interface + rule-based v1 implementation. Lands in Phase 3.
- `backend/app/services/` — orchestration glue: aggregation, scheduling, feed lifecycle, WebSocket broadcast.
- `backend/app/api/routers/` — REST endpoints, one router per resource; `health.py` is the only one so far.
- `backend/app/main.py` — `create_app()` factory (no module-level side effects beyond the final `app = create_app()`), so tests can build isolated instances.
- `frontend/src/components/` — small, single-purpose components grouped by feature area (`dashboard/`, `chart/`, `history/`).
- `frontend/src/pages/`, `hooks/`, `services/`, `types/`, `store/` — added as each phase needs them; not all exist yet.
- `docs/architecture.md` — full architecture + phase plan; keep in sync when the design changes.

## Key libraries

- **Backend config:** `pydantic-settings` — single `Settings` class in `app/core/config.py`, cached via `get_settings()`. Env vars map case-insensitively to field names (no prefix); list fields (`cors_origins`, `symbols`, `timeframes`) accept comma-separated strings via a `field_validator`.
- **Backend data access:** SQLAlchemy (added Phase 1) — repositories own sessions; no ORM models leak past the repository layer.
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
