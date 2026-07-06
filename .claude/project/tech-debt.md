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
