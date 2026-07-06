---
description: .NET / C# conventions, architecture, and async rules
pack: dotnet
paths:
  - "**/*.cs"
---

# .NET / C# rules

Auto-applies when editing C#. Extends [CLAUDE.md](../../CLAUDE.md). Project layer map, stack, and debt: [project/context.md](../project/context.md). Layer-specific detail lives in [controllers.md](controllers.md), [repositories.md](repositories.md), [services.md](services.md).

## Architecture
- Respect the project's layering and dependency direction (see `project/context.md`); never create circular dependencies.
- Thin controllers — no business logic. Use **DTOs** at boundaries; **never return entities** from controllers.
- `DbContext` / EF Core types stay in the data/Infrastructure layer.

## Naming & language
- **PascalCase:** types, methods, properties, constants, public members. **camelCase:** parameters, locals, lambda params.
- Prefix interfaces with `I`, private fields with `_`. Booleans read as `Is/Has/Can/Should`.
- **File-scoped namespaces.** **Nullable reference types on** (avoid the `!` null-forgiving operator). `record` types for immutable DTOs.
- Guard arguments with `ArgumentNullException.ThrowIfNull(...)`. Async methods suffixed `Async`. XML docs on public APIs. Dispose `IDisposable` with `using`. No abbreviations / Hungarian notation.

## Async & concurrency
- Async all the way; **no sync-over-async** (`.Result`, `.Wait()`, `.GetAwaiter().GetResult()`). **Never `async void`** except event handlers.
- Propagate `CancellationToken` end-to-end.
- `DbContext` is not thread-safe — **no `Task.WhenAll` over a shared context**; parallelize only with separate DI scopes.
- External calls: `IHttpClientFactory` (never `new HttpClient`); wrap in retry + timeout policies (Polly).

## Patterns & data
- Reuse the project's patterns — Repository + Unit of Work, Factory, Strategy, Decorator, Options. `SaveChanges` only via the Unit of Work. Don't introduce MediatR without approval.

Applicable gates: [code-review.md](code-review.md).
- Use the project's configured mapper / structured logger / typed exceptions (see `project/context.md`); never log PII/secrets.
