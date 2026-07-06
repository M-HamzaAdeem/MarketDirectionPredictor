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
| TD-1 | `backend/app/services/feed_service.py:53-55` (`_persist`) | DIP — calls `get_session_factory()` directly instead of receiving it via constructor injection | Consistent with the `get_settings()`-direct-call pattern already used in routers; no test exists yet over the feed loop's write path, so the gap has no current cost | Inject the session factory into `FeedService.__init__` when the feed loop itself needs unit tests (expected around Phase 4, WebSocket broadcast work) | 2026-07-06 |
