# Signal method (ICT/Smart Money Concepts pipeline)

## Overview

This is a second, stricter prediction path alongside the Phase 3 rule-based
`PredictionStrategy` (see [prediction-method.md](prediction-method.md)).
Where Phase 3 scores a direction/confidence for *every* candle close, this
pipeline only ever produces a **Signal** when a full, winning-caliber ICT
trade setup confirms — entry, stop, target, and a minimum 1.8 risk:reward,
all computed before the Signal exists. There is no partial output and no
fallback score: `build_signal()` returns `None` unless every stage below
confirms.

Every Signal is logged (`SignalRepository`, table `signals`) with its full
reasoning and, once resolved, its outcome (WIN/LOSS/EXPIRED) and realized
R:R — the "prediction + end result" record PROJECT.md requires. Trades
remain manual: nothing in this codebase places an order.

## Three-timeframe pipeline

| Timeframe | Job | Module |
|---|---|---|
| **4H** | Directional bias — the last confirmed CHoCH sets the prevailing trend | `_determine_bias` in `prediction/signal_builder.py` |
| **1H** | Setup formation — sweep, CHoCH/BOS, POI, OTE, volume-profile confluence | `_find_setup` in `prediction/signal_builder.py` |
| **15m** | Entry confirmation — has price actually tapped the entry zone? | `_check_entry` in `prediction/signal_builder.py` |

1m/5m candles still exist (raw data, useful for future charting) but
aren't load-bearing for signal generation.

`SignalService` (a `services/candle_close_handler.py` `CandleCloseHandler`)
triggers this pipeline whenever a **15m** candle closes — that's the
entry-confirmation timeframe, so it's the only timeframe close that can
newly complete a signal.

## Definitions

- **Weak vs. strong swing point** (`features/structure.py`): every swing
  high/low starts *weak* (untested, resting liquidity). It's derived —
  not stored — as "untouched by any sweep or structure break so far"
  (`weak_points()`).
- **Sweep** (`detect_sweeps`): a later candle's wick passes a weak level
  but its **close** stays on the near side — a liquidity grab/rejection,
  the "no close through it" trigger.
- **CHoCH vs. BOS** (`detect_structure_breaks`): a candle **closing**
  beyond a swing point, tracked against a running prevailing-trend state.
  A close against the trend is CHoCH (reversal trigger, becomes the new
  trend); a close with the trend is BOS (continuation).
- **Order Block** (`features/poi.py`): the last opposing-color candle
  before an impulsive move (range ≥ 1.5× ATR).
- **Fair Value Gap** (`features/poi.py`): the classic 3-candle imbalance.
- **OTE** (`features/fibonacci.py`): 70.5%–79% retracement of the impulse
  leg from the sweep to its extreme.
- **Fixed Range Volume Profile** (`features/volume_profile.py`): POC/Value
  Area computed over the same impulse-leg range, used to break ties when
  multiple POI candidates overlap the OTE zone (prefer the one nearest
  the POC).

## Assembly (`_find_setup`)

1. Confirm a 1H structure break matching the 4H bias (`confirming_break`).
2. Require a sweep of the opposing-kind swing point *before* that break
   (`confirming_sweep`) — no sweep, no setup. This is the "sweep + CHoCH"
   combination from PROJECT.md.
3. The impulse leg runs from the sweep candle's extreme to the highest
   high (bullish) / lowest low (bearish) reached since the break.
4. Collect Order Block / FVG candidates within the leg, matching bias
   direction, and intersect each with the OTE zone. **No overlap, no
   signal** — OTE and POI must actually agree, not just both exist.
5. If multiple overlaps exist, prefer the one closest to the volume
   profile's POC.
6. Stop = the swept extreme, offset by `0.25× ATR` (or a small
   price-ratio fallback if ATR isn't available yet).
7. Target = the nearest un-swept opposing weak point beyond the entry
   zone. **No un-swept opposing liquidity, no signal** — this pipeline
   never invents a fixed-R fallback target.
8. R:R = reward / risk from the entry-zone midpoint. **Below 1.8, no
   signal.**

## Outcome tracking (`services/signal_tracker.py`)

`SignalTracker` (also a `CandleCloseHandler`) checks every OPEN signal
against each new 15m candle for its symbol:

- Stop hit → LOSS, realized R:R = -1.0.
- Target hit → WIN, realized R:R = the signal's planned R:R (v1 has no
  partial-exit modeling).
- **Both hit in the same candle** (only possible at candle-level
  granularity) → scored LOSS — the conservative, worst-case read.
- Neither hit, and more than 5 days have passed since `opened_at` →
  EXPIRED, realized R:R = 0.0.
- Otherwise → stays OPEN.

## Why these numbers, and what to revisit

The impulse-ATR multiplier (1.5), stop buffer (0.25× ATR), OTE zone
(70.5%–79%), R:R floor (1.8), and expiry window (5 days) are deliberate,
documented choices — not fit to historical outcomes. Backtesting (Phase 9)
is where these get evaluated and tuned, or this whole heuristic pipeline
gets replaced by a fitted model behind the same conceptual contract
(features in, gradable Signal or nothing out).

## Practical note on testing

Mock ticks run at 1 real second per tick; a 4H candle takes 4 real hours
to close live. The pipeline is verified via the test suite (constructed
multi-timeframe candle fixtures run through the real detection code, not
hand-predicted), not by waiting for a live 4H/1H candle to form — that
would only be practical with a mock-clock acceleration feature, which
doesn't exist yet.
