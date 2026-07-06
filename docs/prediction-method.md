# Prediction method (v1, rule-based)

## Overview

Version 1 uses a deterministic, rule-based scoring strategy
(`RuleBasedStrategy` in [`backend/app/prediction/rule_based.py`](../backend/app/prediction/rule_based.py))
— not a fitted ML model. It combines four signals from a `FeatureSet`
([`backend/app/features/feature_builder.py`](../backend/app/features/feature_builder.py))
into a weighted vote.

## Signals and weights

| Signal | Weight | Vote |
|---|---|---|
| Market structure (break of structure) | 2 | bullish/bearish/neutral, directly from `detect_break_of_structure` |
| Trend (SMA fast vs. slow crossover) | 1 | fast > slow → bullish, fast < slow → bearish, equal → neutral |
| RSI | 1 | RSI ≥ 60 → bullish, RSI ≤ 40 → bearish, else neutral |
| Momentum (price change over N candles) | 1 | positive → bullish, negative → bearish, zero → neutral |

Structure carries double weight because a confirmed break of structure is
the most concrete signal available; the others are corroborating context.

An indicator that isn't available yet (not enough candle history) is
excluded from the vote entirely — it doesn't count as neutral, and doesn't
drag confidence down just because a symbol/timeframe is new.

## Scoring

```
score      = sum(weight * vote) over every available signal
confidence = min(100, |score| / total_available_weight * 100)
direction  = BULLISH if score > 0, BEARISH if score < 0, else NEUTRAL
```

If no signal is available at all, the result is NEUTRAL at 0% confidence
with reason `"insufficient data"` — the system never guesses when it has
nothing to go on.

**Known limitation:** confidence measures *agreement among the signals
that are currently available*, not the strength of the underlying
evidence. On a brand-new symbol/timeframe where only structure has enough
history to compute, a single non-neutral structure vote reads 100%
confidence — there's nothing to disagree with it yet, even though only one
of four signals contributed. This is a real gap against the "never claims
certainty" posture below; it's deferred rather than fixed now (see
[tech-debt.md](../.claude/project/tech-debt.md)) because the right fix
(scale confidence by evidence *volume*, not just agreement) is exactly the
kind of thing Phase 9 backtesting should tune against real outcomes rather
than guess at.

## Why these numbers, and what to revisit

The weights, RSI thresholds (60/40), and indicator periods
([`backend/app/features/indicators.py`](../backend/app/features/indicators.py))
are initial, reasonable choices — not fit to any historical outcome yet.
Phase 9 (backtesting) is where these get evaluated against real results and
tuned, or replaced entirely by an ML strategy behind the same
`PredictionStrategy` interface.

## Safety

Every prediction produced by `GET /predictions/{symbol}/{timeframe}/latest`
is logged append-only via `PredictionRepository` before being returned —
nothing reaches the dashboard without a durable, auditable record, per
PROJECT.md's "log every prediction" rule. Confidence is always shown, but
see the known limitation above — a high number on a new symbol reflects
signal agreement, not necessarily strong evidence.
