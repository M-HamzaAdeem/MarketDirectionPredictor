---
description: First-run setup for a freshly-installed kit — inspect this repo and generate .claude/project/context.md + tech-debt.md, wire the git audit hook, and verify.
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

Initialize this repository's project profile in one pass. The portable kit (CLAUDE.md,
rules, agents) is stack-agnostic and defers every project specific to
`.claude/project/context.md`; this command generates that file from the actual codebase
so no manual editing is needed. Do all of the following, then report.

## 1. Inspect the repository

Detect the stack and layout from real evidence — do not guess. Probe for:

- **Stack & build:** `*.sln`/`*.csproj` (.NET), `package.json` (Node — note the framework:
  React/Vue/Angular/Next), `pyproject.toml`/`requirements.txt`/`setup.cfg` (Python),
  `go.mod` (Go), `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (JVM), `Gemfile` (Ruby).
- **Solution & folder layout:** the top-level projects/packages and each one's
  responsibility (API/edge, application/services, domain, infrastructure, tests, UI).
- **Key libraries & canonical helpers:** mapping, validation, logging, error handling,
  data access, testing — name the specific library used for each cross-cutting concern so
  Claude reuses it instead of inventing a new one.
- **Conventions:** root namespace/module prefix, naming rules, anything that differs from
  the portable defaults in CLAUDE.md / the rules.
- **Build & run commands:** restore/build, test, lint/format, and run-locally commands.

Read the placeholder at `.claude/project/context.md` for the exact section structure to
fill. Use `Glob`/`Grep`/`Read` for inspection; you may run read-only `Bash` (e.g.
`git ls-files`, `dotnet --info`) but make no source changes outside `.claude/project/`.

## 2. Trim to the detected stack (packs)

The kit ships **every pack** so a copy-paste install works anywhere; now trim to what this
repo actually needs. Map the detected stack to packs:

- `*.sln`/`*.csproj` (.NET) → keep **`dotnet`**
- `package.json` with React/Vue, or `*.tsx`/`*.vue` files → keep **`frontend`**
- neither → keep neither (core only)

Pack-specific files carry a `pack:` line in their frontmatter. Find the pack-tagged files
under `.claude/rules/` and `.claude/agents/` (e.g. `grep -rl "^pack:" .claude/rules .claude/agents`),
read each one's `pack:` value, and **delete the files whose pack is not in the kept set**
(e.g. on a React repo, remove the `pack: dotnet` rules and agents). Then record the kept
packs in `.claude/.kit-packs` — space-separated (e.g. `frontend`), or `all` if you kept
everything. Tell the user which packs were kept and what was removed.

Skip this (leave the full kit in place) if you can't confidently determine the stack.

## 3. Generate the project profile

- **Rewrite [`.claude/project/context.md`](../project/context.md)** with the findings,
  following its existing headings. **Remove the `PLACEHOLDER — REPLACE THIS FILE` banner
  comment** at the top. Fill every section with concrete, verified facts; if something
  genuinely doesn't apply, say so briefly rather than leaving a bracketed placeholder.
- **Leave [`.claude/project/tech-debt.md`](../project/tech-debt.md) and
  [`decisions.md`](../project/decisions.md) as-is** if they're still the empty register/log;
  they ship ready to use. (Do not invent debt or decision entries.)
- Keep project-specific names OUT of the portable files — they belong only under
  `.claude/project/`. (The audit's leakage check enforces this.)

## 4. Wire the human-commit audit hook

If `.githooks/pre-commit` exists at the repo root, enable it so human commits are gated
by the same audit Claude runs:

```sh
git config core.hooksPath .githooks
```

Tell the user this was set (and that it points git at `.githooks/`). Skip with a note if
this isn't a git repo or `.githooks/pre-commit` is absent.

Then make sure line endings are protected: the hook and `*.sh` scripts must stay LF or
they break on Linux/macOS. The installer ships a `.gitattributes` for this, but if the
repo already had its own `.gitattributes` the installer skipped it — in that case, append
these rules if they're missing:

```
*.sh        text eol=lf
.githooks/* text eol=lf
*.py        text eol=lf
```

## 5. Verify

Run the consistency audit and confirm it passes:

```sh
python .claude/scripts/claude-audit.py
```

If it reports FAIL, fix the cause (usually a broken link or a project name that leaked
into a portable file) and re-run until it PASSES.

## 6. Report

Summarize: the detected stack & layout, **which packs were kept and what was trimmed**,
what you wrote to `context.md`, whether the git hook was wired, and the final audit RESULT.
Note anything you were unsure about so the user can refine `context.md`.
