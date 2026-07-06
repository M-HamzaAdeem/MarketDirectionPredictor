---
description: Rules for repositories, EF Core, and data access (Infrastructure layer)
pack: dotnet
paths:
  - "**/Repository/**/*.cs"
  - "**/*Repository.cs"
---

# Repository & EF Core rules (Infrastructure layer)

Auto-applies when editing data-access code. Full standards: [CLAUDE.md](../../CLAUDE.md).

- **`DbContext` lives only here** — never expose it above Infrastructure.
- All DB calls **async**; accept and propagate **`CancellationToken`** into EF calls.
- Reads use **`AsNoTracking()`**; use **`Select()`** projection to shape payloads.
- Prevent **N+1**; include related data deliberately.
- **`SaveChanges` only via the Unit of Work** — never per-repository.
- Minimize roundtrips; review LINQ for translation and efficiency.

**Forbidden:** DB calls in loops · `SaveChanges` in loops · synchronous DB calls · unnecessary `ToList()` · sharing a `DbContext` across parallel tasks · raw SQL unless unavoidable (then parameterized).

Applies to production data access — the `**/*Repository.cs` glob can also match test doubles, which are out of scope. Applicable gates: [code-review.md](code-review.md).
