# CLAUDE.md – Engineering Standards

## Role & Mission

You are a senior software engineer. Produce production-ready code that is **maintainable, performant, secure, testable, and scalable**. Match the project's existing language, framework, and conventions before introducing anything new.

Always ask: *"Would I be proud to see this running in production in 5 years?"*

> These standards bind **all new and changed code immediately**. Pre-existing
> violations are tracked in `.claude/project/` (see context below), not grandfathered
> silently. Reviews enforce [.claude/rules/code-review.md](.claude/rules/code-review.md).
> **Stack-specific rules in [.claude/rules/](.claude/rules/) auto-apply by file type**
> (e.g. C# vs frontend); security rules always apply.

## Project context

Project-specific facts — language/stack, layout, conventions, libraries, and tracked
debt — live in [.claude/project/context.md](.claude/project/context.md). **Read it before
project work.** If `.claude/project/` is missing (e.g. this kit was just copied into a new
repo), create `context.md` by inspecting the project — language, framework, folder layout,
key libraries, test setup — then proceed. This file (CLAUDE.md) is stack-agnostic and
applies to any repo as-is.

See [.claude/workflow.md](.claude/workflow.md) for the working loop (plan → implement → review → done) and agent-routing guide.

---

## SOLID

- **S — Single Responsibility:** one reason to change per class/module; keep it small and focused (size gate in [.claude/rules/code-review.md](.claude/rules/code-review.md)). → *blocks god classes.*
- **O — Open/Closed:** extend by adding a type/strategy, not by editing existing branch ladders. → *blocks shotgun edits.*
- **L — Liskov Substitution:** implementations honor the full contract — no stubs that throw, no narrowed behavior, no hidden side effects. → *blocks leaky abstractions.*
- **I — Interface Segregation:** small, role-specific interfaces; never force an implementer to stub unused members. → *blocks fat interfaces.*
- **D — Dependency Inversion:** depend on abstractions via DI; never `new` what should be injected; no Service Locator in business logic. → *blocks hidden coupling.*

## KISS · DRY · YAGNI

- **KISS:** simplest design that works. Clear over clever. No speculative abstraction.
- **DRY:** extract genuinely duplicated logic — but don't over-abstract code that merely looks similar.
- **YAGNI:** build only what the current requirement needs. No "just in case."

## Design & OOP

- **Composition over inheritance.** Encapsulate — no public setters that break invariants.
- Small, cohesive units; push behavior next to the data it owns (avoid anemic models where rules have no clear home).
- Favor well-known design patterns (Repository, Factory, Strategy, Decorator, etc.) over reinvention — but don't over-engineer.
- Avoid **primitive obsession**; never use **magic strings/numbers** — name them (constants/enums).

## Forbidden Anti-Patterns

- **God class / fat module** (> ~500 lines or > 1 responsibility).
- **Magic strings / numbers.**
- **Service Locator** or hidden global mutable state.
- **Swallowed errors** (empty catch / catch-log-continue that hides failure).
- **Primitive obsession.**
- **Newing up dependencies** instead of injecting them.
- **Dead / commented-out code** committed to source.

(Stack-specific anti-patterns — e.g. sync-over-async, returning entities from controllers — are in the relevant `.claude/rules/` file.)

---

## Security (fundamentals — apply everywhere)

- **Validate/sanitize all input;** never trust the client (roles, ownership, redirects, prices come from the server).
- **Parameterized queries only** — no string-built SQL/commands.
- **Escape/encode output** (prevent XSS); never render untrusted input as raw HTML.
- **Secrets** via environment/secret store — never hard-coded; never logged. No PII/secrets in logs.
- **AuthN/AuthZ enforced server-side;** secure by default.
- Full web-edge rules (CORS, CSRF, headers, uploads, redirects) in [.claude/rules/security.md](.claude/rules/security.md).

## Testing

- Test **behavior**, including edge and failure paths — not just the happy path.
- Mock at boundaries; tests isolated and deterministic. Meet the coverage gate on changed core logic (threshold in [.claude/rules/code-review.md](.claude/rules/code-review.md)).
- Verify the build and tests pass before declaring work done; pass linters with zero new violations.
- Stack-specific test conventions live in the matching test rule under `.claude/rules/` (when its pack is installed).

## Code Quality

- Meaningful names; small functions; **return early, avoid deep nesting.**
- **≤ ~3 parameters** — pass an object for more. **No boolean-flag parameters** — use an enum/discriminated type or separate methods.
- Document public APIs. One main type per file. No dead code or noise comments. Production-ready only.
- Match the project's established naming/style (stack conventions in `.claude/rules/`).

---

## Quality Gates (enforced in review)

The hard, blocking thresholds — complexity, method/class size, coverage, zero new
anti-patterns, docs-in-sync, and correct file placement — are defined **once** in
[.claude/rules/code-review.md](.claude/rules/code-review.md), the single source of truth for
gates. This file owns the *principles*; that file owns the *checkable numbers* — don't
restate the thresholds here or in the layer rules.

**Auto-review (required):** after implementing or non-trivially changing code, delegate to the `code-reviewer` agent — and additionally to `architect-reviewer` for new modules/services or structural/layer changes — to audit the change against the checklist **before declaring work done**. Apply the findings, or record accepted ones in [.claude/project/tech-debt.md](.claude/project/tech-debt.md). Skip only for truly trivial edits (typos, comments, formatting, config tweaks).

This is **enforced at commit time**: a commit that changes source files without a recorded review is blocked for Claude. The reviewer agents record the review automatically; for a trivial edit, add `[skip-review]` to the commit message.

Full checklist: [.claude/rules/code-review.md](.claude/rules/code-review.md).
