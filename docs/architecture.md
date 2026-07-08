# Architecture

## Overview

A full-stack market direction predictor for XAUUSD, EURUSD, and AUDUSD across
1m/5m/15m timeframes. Version 1 predicts direction only — it never places
trades. See [PROJECT.md](../PROJECT.md) for the product spec this implements.

## Backend (FastAPI, Python)

- **`feeds`** — `MarketDataProvider` is the adapter interface for any tick
  source. V1 ships `MockMarketDataProvider` only; a TradingView or broker
  adapter can be added later as a new class behind the same interface,
  without touching aggregation, storage, or prediction code.
- **`storage`** — SQLAlchemy models and repositories over SQLite: candles and
  an append-only prediction log.
- **`features`** — indicator math (moving averages, RSI, ATR, momentum,
  volatility) and market structure detection (swing points, break of
  structure).
- **`prediction`** — `PredictionStrategy` is the interface for turning a
  feature set into a direction/confidence/reason. V1 is rule-based; an ML
  strategy (scikit-learn/XGBoost) can be added later behind the same
  interface.
- **`services`** — orchestration: candle aggregation from ticks, scheduled
  prediction runs, feed lifecycle/reconnect, WebSocket broadcast.
- **`api`** — REST routers for snapshots/history/config, plus a WebSocket
  endpoint for live deltas (price ticks, new predictions, feed status).
- **`core`** — `Settings` (env-driven config: active feed provider, symbols,
  timeframes, CORS origins), enums (`Symbol`, `Timeframe`, `Direction`,
  `FeedStatus`), logging, exceptions.

## Frontend (React + Vite + TypeScript + Tailwind)

- A WebSocket hook feeds a small store with live prices/predictions/feed
  status; REST is used for initial snapshots and paginated history.
- Charting via `lightweight-charts` (added when the chart page is built).
- A persistent disclaimer banner is always rendered — predictions are
  probabilistic, not guaranteed, and no trade is ever placed automatically.

## Data flow

```
MockMarketDataProvider (async tick generator)
  -> FeedService (normalize -> Tick)
  -> CandleAggregator (buffer into 1m/5m/15m candles)
     -> on candle close: CandleRepository (SQLite persist)
     -> FeatureBuilder (indicators + structure over recent window)
        -> PredictionEngine.strategy.predict(features) -> direction/confidence/reason
           -> PredictionRepository (append-only log)
  -> BroadcastService -> WebSocket
     -> frontend store -> dashboard components re-render
```

If the provider's tick stream ends or raises, `FeedService` reconnects with
capped exponential backoff, moving `status` to `disconnected` for the
duration and back once ticks resume — the dashboard reflects that instead
of silently showing a stale prediction as if it were live. `degraded`
remains reserved for a future heartbeat/stall detector (ticks still
arriving but abnormally slow) — a different failure mode from the
hard stream failure this handles today; see decisions.md.

## Phases

0. Scaffolding (this phase) — backend/frontend skeletons, health check, mock
   provider, build verified both sides.
1. Mock data pipeline — tick generation, candle aggregation, SQLite storage,
   read-only REST endpoints.
2. Indicators & market structure, unit-tested against fixtures.
3. Prediction engine v1 (rule-based), logged to an append-only table.
4. WebSocket live updates + scheduler.
5. Frontend dashboard MVP wired to the mock feed end-to-end.
6. Charting (`lightweight-charts`) & prediction history UI.
7. Settings/config surface — read-only for v1 (`GET /config`, a `/settings`
   page): `Settings` is loaded once at backend startup with no reload
   mechanism, and the ICT/prediction thresholds are plain module constants,
   not persisted config, so there's nothing to safely write back yet. Live
   editing needs two prerequisites first: a persisted, mutable config store
   (rather than module constants) for the strategy parameters, and either a
   `Settings` reload path or accepting that some fields (symbols, feed
   provider) always require a restart. Revisit once backtesting (Phase 9)
   creates real demand for adjusting thresholds without redeploying.
8. Hardening — reconnect/backoff (`FeedService` retries a failed/ended tick
   stream with capped exponential backoff, surfacing `FeedStatus.DISCONNECTED`
   for the duration; the frontend's WebSocket hook does the same on its
   side), a security headers pass (CSP, X-Content-Type-Options,
   X-Frame-Options, Referrer-Policy, HSTS on every response), a coverage
   gate (`pytest-cov`, `--cov-fail-under=80` wired into `pytest.ini` so a
   bare `pytest` run enforces it), docs sync.
9. Real feed adapter(s) + historical backfill (in progress), fallback
   chain, backtesting engine, ML prediction strategy. Auto-trading remains
   out of scope permanently, not just deferred.
   - **Part A (done):** `TwelveDataProvider` — real REST historical
     candles + real WebSocket live ticks for XAU/USD, EUR/USD, AUD/USD
     (TradingView has no public API for this per PROJECT.md; OANDA was
     considered but isn't available in the project owner's region).
     Selected via `FEED_PROVIDER=twelve_data` + `TWELVE_DATA_API_KEY`
     through `app/feeds/factory.py`. `FeedService.backfill()` fetches and
     persists missing historical candles for every configured
     symbol/timeframe before live streaming starts, so predictions/ICT
     signals don't need real hours/days of live candles to accumulate
     first — verified live end-to-end (see decisions.md). Forex/commodity
     data carries no real volume; `compute_volume_profile` was hardened to
     return `None` rather than a fabricated POC when volume is all zero.
   - **Part B (fallback chain done, backtesting engine next):**
     `FallbackMarketDataProvider` wraps `[TwelveDataProvider,
     MockMarketDataProvider]` whenever a real feed is selected — falls
     back to the mock feed immediately (inside the same `stream_ticks()`
     call, not waiting out `FeedService`'s own reconnect backoff) the
     moment the primary fails, surfaced via `FeedStatus` (`nominal_status`
     is now read live from the active provider, not cached); periodically
     retries the primary via a bounded fallback duration. Verified live:
     booting against the real Twelve Data account reports `feed_status:
     "live"`, confirming the wrapper delegates correctly when the primary
     is healthy. Backtesting engine still to do — reuses Part A's
     historical-fetch path to replay the existing `rule_based`/
     `signal_builder` strategies against real history.
   - **Part C (later):** ML prediction strategy (scikit-learn/XGBoost per
     PROJECT.md), informed by whatever the backtest turns up; plugs in
     behind the existing `PredictionStrategy` interface, no changes
     needed elsewhere.

## Safety rules

- No auto-trading and no broker execution integration, ever, in this
  version — there is no execution module to disable, none exists.
- Every prediction is logged append-only, for auditability and future
  backtesting.
- Mock data is always visibly labeled as mock (`FeedStatus.MOCK`) in the UI;
  it must never be presented as if it were live.
- On feed failure, the dashboard degrades visibly rather than showing a
  stale prediction as current.
- Prediction thresholds are named config constants, not magic numbers, and
  documented in `docs/prediction-method.md` (added in Phase 3) so the
  reasoning is auditable.
