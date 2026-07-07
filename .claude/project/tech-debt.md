# Technical debt register

Companion to [context.md](context.md) and the review gates in
[../rules/code-review.md](../rules/code-review.md).

This is the single place where **accepted** rule violations live. The `code-reviewer`
and `architect-reviewer` agents append here when a finding is consciously deferred
rather than fixed; reviewers consult it so known debt isn't re-reported as new.

## How to use

- A PR may **add** an entry when a Gate/standard violation is accepted for now — record
  enough that someone can fix it later without re-discovering the context.
- A PR that **touches** a file listed here should fix the entry (and remove it) or
  explain why it still stands.
- Keep entries specific: cite `file:line`, name the principle/anti-pattern, and give a
  concrete remediation.

## Register

| ID | Location (`file:line`) | Principle / anti-pattern | Why accepted (for now) | Planned remediation | Added |
| -- | ---------------------- | ------------------------ | ---------------------- | ------------------- | ----- |
| TD-2 | `backend/app/prediction/rule_based.py:88` (`_combine`) | Calibration gap — confidence = \|score\| / *available* weight measures signal agreement, not evidence volume, so a single available signal (e.g. structure alone on a brand-new symbol) always reads 100% or 0%, never in between | Documented as a known limitation in [docs/prediction-method.md](../../docs/prediction-method.md); the correct fix requires empirical tuning, not a guess, so it's deferred to backtesting rather than patched now | Revisit during Phase 9 backtesting: either scale confidence by evidence volume (e.g. weight present / total possible weight, multiplied into the agreement ratio) or replace the heuristic entirely with a fitted ML strategy behind `PredictionStrategy` | 2026-07-06 |
| TD-3 | `frontend/src/components/dashboard/PriceChart.tsx` | WCAG AA gap — the candlestick chart is a canvas element, opaque to screen readers, with no text alternative or `aria-label` summarizing what it shows | The adjacent `SignalHistoryTable`/`PredictionHistoryTable` cover the same underlying data in accessible tabular form, so the information isn't entirely unavailable — but the chart itself has no accessible description | Add a visually-hidden text summary (e.g. "Candlestick chart for {symbol} {timeframe}, {N} candles, current price {close}") or an `aria-label` on the chart container when this is prioritized | 2026-07-08 |
| TD-4 | `frontend/src/hooks/useCandles.ts`, `useSignalHistory.ts`, `usePredictionHistory.ts` | Stale data — these React Query hooks fetch once on mount with no refetch trigger tied to the live WebSocket. If a page loads before the first candle for the selected symbol/timeframe has closed, the chart/history stay empty until the user reloads or changes the selector (React Query's default refetch-on-window-refocus is the only other trigger) | Observed live during Phase 6 verification, not a regression — `useMarketSocket` already knows about every price tick and candle-adjacent event but doesn't invalidate these query keys | When this friction is worth fixing: invalidate the relevant `['candles', symbol, timeframe, ...]` / `['signals', 'history', symbol, ...]` query keys from `useMarketSocket`'s dispatch (e.g. via `queryClient.invalidateQueries` on a `price` message for the active symbol), or add a short `refetchInterval` | 2026-07-08 |
| TD-5 | `backend/pytest.ini:4` (`--cov-fail-under=80`) | Coverage gate is repo-total only, not per-file — `app/api/routers/health.py`, `prices.py`, `symbols.py`, `websocket.py`, `main.py` (all 0%) and `storage/database.py` (52%) are currently carried by the rest of the suite averaging to ~89%. A future PR could delete tests for well-covered code and still pass the gate as long as the total stays above 80% | These are thin, largely untested-by-design wiring modules pre-dating Phase 8 (routers are one-liners over already-tested services/repositories; `main.py`/`database.py` are composition roots exercised indirectly, not directly, by the integration tests) — adding direct tests or per-file `--cov-fail-under` for all of them wasn't in Phase 8's hardening scope | If per-file regressions in well-covered modules become a real concern, either add direct tests for the 0%-covered routers/composition roots or switch to `pytest-cov`'s per-module reporting with a stricter check in CI once one exists | 2026-07-09 |
