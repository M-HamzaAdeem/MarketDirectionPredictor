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
| _(none yet — add rows as debt is accepted)_ | | | | | |
