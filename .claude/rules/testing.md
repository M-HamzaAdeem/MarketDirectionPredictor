---
description: Test conventions
pack: dotnet
paths:
  - "**/*Tests.cs"
  - "**/*Test.cs"
  - "**/*.Tests/**/*.cs"
---

# Test rules

Extends [CLAUDE.md](../../CLAUDE.md) Testing Standards. Auto-applies when editing test code.

- Frameworks: **xUnit** + **Moq** (mock at interface boundaries).
- Test class name ends in `Test` or `Tests`; **mirror the source namespace/folder structure**.
- Test method names: **`MethodName_Scenario_ExpectedResult`**.
- Unit-test the application/service layer against mocked interfaces; integration-test repositories/controllers.
- Cover edge cases and failure paths, not just the happy path.
- Tests isolated and **deterministic** — no real clock, network, filesystem, `Thread.Sleep`, or randomness; order-independent and repeatable. Target **≥ 80% coverage** on changed service-layer code.

Applicable gates: [code-review.md](code-review.md).
