---
description: Git commit message conventions — always apply
---

# Commit message rules

Applies to every commit. Working loop: [workflow.md](../workflow.md). Release flow: [release-manager](../agents/infra/release-manager.md).

## Format — Conventional Commits

- Structure: `type(scope): summary`. `scope` is optional and lowercase; no trailing period on the summary.
- **Types:** `feat` (feature), `fix` (bug fix), `docs`, `style` (formatting only, no logic), `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **Breaking changes:** append `!` after the type/scope (e.g. `feat!:`) **and** add a `BREAKING CHANGE: <what changed + how to migrate>` footer.
- Reference issues/PRs in the footer: `Closes #123`, `Refs #123`. Keep any co-authorship / sign-off trailers the project already uses.

## Style

- **Imperative mood** in the summary — "add", not "added"/"adds". Summary ≤ ~50 chars.
- If the change isn't self-evident, add a blank line then a body explaining **why** (not how); wrap at ~72 chars.
- **One logical change per commit** — don't bundle unrelated edits. No noise commits (`wip`, `fixes`, `stuff`).

## Why it matters

The `type` drives the changelog section and the SemVer bump that [release-manager](../agents/infra/release-manager.md) derives: `feat` → **Added** / minor, `fix` → **Fixed** / patch, `BREAKING CHANGE` → major.

Examples:

- `feat(api): add cursor pagination to /orders`
- `fix(auth): reject expired refresh tokens`
- `docs: clarify install.py update flow`
