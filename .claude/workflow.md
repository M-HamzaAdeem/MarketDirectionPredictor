# Workflow & delegation

How to work in this repo. Stack-agnostic; project specifics: [project/context.md](project/context.md).

## The loop (every non-trivial change)
1. **Understand** — read the relevant code and `project/context.md`; restate the goal and constraints.
2. **Plan first** (non-trivial work) — outline approach + files to touch *before* editing. For a new module/service or a structural/layer change, get `architect-reviewer` input first.
3. **Implement** — follow [CLAUDE.md](../CLAUDE.md) and the file-type rules that auto-apply from [rules/](rules/).
4. **Self-check (Definition of Done)** — build + tests pass; **docs synced** (in-code + README/changelog); **files placed correctly** per `context.md`.
5. **Auto-review (required)** — delegate to `code-reviewer` (and `architect-reviewer` for new modules/structural change). Apply findings, or record accepted ones in `project/tech-debt.md`. **Enforced at commit:** changing source without a recorded review blocks Claude's commit; the reviewer agents record it automatically, and `[skip-review]` in the commit message bypasses it for trivial edits.
6. **Done** — the gates in [rules/code-review.md](rules/code-review.md) pass.

Trivial edits (typos, comments, formatting, config tweaks) may skip steps 2 and 5.

Commit messages follow [rules/commits.md](rules/commits.md) — Conventional Commits + imperative 50/72 style; `release-manager` turns the commit types into the changelog entry and version bump.

Record durable **decisions & learnings** — a non-obvious choice, a gotcha, an adopted convention — in [project/decisions.md](project/decisions.md), the project's committed memory. Not routine changes (git/changelog) and not accepted violations (those go in [project/tech-debt.md](project/tech-debt.md)).

## Delegate vs. do inline
- **Inline:** small, localized changes within the current context.
- **Delegate to a subagent when:** the task is a self-contained chunk needing deep focus or a different specialty; it benefits from an isolated context; or you need an independent review (code/architecture). Give the agent the file paths and the goal; one responsibility per delegation.
- When unsure, the main session handles it.

## Agent routing (task → agent)
*Adjust to this repo's agent roster — pack-specific agents (e.g. `csharp-developer`, `react-developer`) are present only when their pack is installed.*

| Task | Agent |
|---|---|
| Server API / language feature | `csharp-developer`, `dotnet-core-expert` |
| API contract / endpoint design | `api-designer` |
| SQL / queries / schema | `sql-pro`, `database-administrator` |
| React / Vue UI | `react-developer`, `vue-developer` |
| Cloud infra / IaC | `azure-infra-engineer` |
| CI/CD & deployment | `deployment-engineer`, `devops-engineer` |
| Containers | `docker-expert` |
| Scripting / automation | `powershell-7-expert` |
| Pre-merge code review | `code-reviewer` |
| Architecture / design review | `architect-reviewer` |
| Diagnose a failure | `debugger` |
| Performance bottleneck | `performance-engineer` |
| Security audit / hardening | `security-auditor`, `security-engineer` |
| Tests | `test-automator` |
| Documentation | `documentation-engineer` |
| Release notes / CHANGELOG | `release-manager` |

Pick the **most specific** match.

## Keeping the kit healthy
Run **`/claude-audit`** after changing agents/rules/`project/` docs (and a commit hook re-runs it before commits). See [README.md](README.md).
