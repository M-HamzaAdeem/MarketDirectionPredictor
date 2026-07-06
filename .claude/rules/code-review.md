---
description: Always-on code review checklist and quality gates (stack-agnostic)
---

# Code Review Checklist

Companion to [CLAUDE.md](../../CLAUDE.md). Reviewers and the `code-reviewer` /
`architect-reviewer` agents enforce this on every change. A PR is not approvable
while any **Gate** item fails.

> Universal gates are below. **Stack-specific gates** apply when editing that file type —
> e.g. .NET DB/async or frontend a11y/security — see the matching stack rule in
> `.claude/rules/` when one is installed. Project stack/helpers: [project/context.md](../project/context.md).

---

## 🚦 Gates (blocking)

- [ ] No new **Forbidden Anti-Pattern** (see CLAUDE.md): god class, magic strings, service locator, swallowed error, newing dependencies, dead/commented code.
- [ ] **No new third-party dependency** (package/framework) without a note in [context.md](../project/context.md) or [tech-debt.md](../project/tech-debt.md) recording why it's needed.
- [ ] Cyclomatic complexity **< 10** per method.
- [ ] Method **≤ ~50 lines**; class/module **≤ ~500 lines** (new/changed types).
- [ ] Inputs validated; access secured (authn/authz). Any public/anonymous endpoint states a one-line reason in code or [tech-debt.md](../project/tech-debt.md).
- [ ] No secrets in code; no internal error detail leaked to clients.
- [ ] Changed core logic has tests; coverage **≥ 80%** on changed code.
- [ ] **Docs synced** with the change: public API/behaviour changes have updated in-code docs in the stack's convention (XML docs / JSDoc / docstrings); new, changed, or removed endpoints are reflected in the API spec where one exists (e.g. OpenAPI/Swagger — see the relevant layer rule); config/env/setup changes reflected in README/usage docs; user-facing changes have a changelog/release-notes entry (`release-manager`).
- [ ] **Structure & placement**: new/moved files are in the correct folder per `.claude/project/context.md`; dead files removed when their code is removed; no stray files at the repo root; no build artifacts/temp/`.bak` committed; folder & naming conventions followed.
- [ ] **Stack-specific gates pass** for the files touched (see the matching rule).

---

## ✅ SOLID

- [ ] **SRP** — class/module has one reason to change; no mixed responsibilities.
- [ ] **OCP** — extension via new types, not edits to existing branch ladders.
- [ ] **LSP** — implementations honor the full interface contract.
- [ ] **ISP** — interfaces are small and role-specific.
- [ ] **DIP** — depends on abstractions via DI; nothing `new`ed that should be injected.

## ✅ Design & OOP

- [ ] Reuses a well-known pattern rather than reinventing; no new abstraction/interface/layer without a second concrete caller or a documented requirement.
- [ ] Composition preferred over inheritance.
- [ ] Encapsulation intact — no invariant-breaking public setters.
- [ ] Named constants/enums instead of magic values; no primitive obsession.

## ✅ KISS / DRY / YAGNI

- [ ] No speculative abstraction or unused extensibility — built only for the current requirement (YAGNI).
- [ ] No duplicated logic that should be shared.
- [ ] Nothing built "just in case."

## ✅ Cross-Cutting

- [ ] Validation, mapping, logging, and error handling use the project's configured stack ([project/context.md](../project/context.md)) — no ad-hoc substitutes.
- [ ] Structured logs only; no PII/secrets logged.
- [ ] Error handling: no empty catch; every catch either handles the error or rethrows with context (no catch-log-continue that hides failure); errors flow through the project's error-handling approach.

## ✅ Code Quality

- [ ] Meaningful names; small, focused functions; return early.
- [ ] Public APIs documented.
- [ ] No dead/commented-out code; no leftover `TODO` without a tracked item in [tech-debt.md](../project/tech-debt.md).
- [ ] One main type per file.

---

### Reviewer note
Findings must be **specific and actionable**: cite `file:line`, name the principle/anti-pattern, and give the concrete fix. Acknowledge good patterns too. Pre-existing violations touched by a PR should be fixed or added to [tech-debt.md](../project/tech-debt.md).
