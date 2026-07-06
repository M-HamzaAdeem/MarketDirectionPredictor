---
description: Rules for application/business services
pack: dotnet
paths:
  - "**/Services/**/*.cs"
---

# Service rules (application layer)

Auto-applies when editing services. Full standards: [CLAUDE.md](../../CLAUDE.md). Project stack: [project/context.md](../project/context.md).

- **SRP:** one cohesive responsibility per service; split it when it mixes concerns or exceeds the size/complexity gates ([code-review.md](code-review.md)).
- Business logic belongs here — not in controllers, not in repositories.
- Depend on **abstractions** via DI; never `new` a dependency; no Service Locator.
- Reuse approved patterns (Repository/UoW, Factory, Strategy, Decorator, Options). Don't reinvent; don't introduce new frameworks (e.g. MediatR) without approval.
- Wrap mutations in the project's transaction handler; services share the scoped Unit of Work.
- Use the project's configured mapper, structured logger, and typed exceptions ([project/context.md](../project/context.md)); never log PII/secrets.
- Async end-to-end; propagate `CancellationToken`. `DbContext` is not thread-safe — no `Task.WhenAll` over a shared context; parallelize only with separate DI scopes.

Oversized services tracked for this project: [project/tech-debt.md](../project/tech-debt.md).

Applicable gates: [code-review.md](code-review.md).
