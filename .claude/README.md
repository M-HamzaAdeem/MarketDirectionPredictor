# `.claude/` — Claude Code configuration

Configures how Claude Code works in this repo. The layout is split into a
**portable template** (drop into any repo — backend or frontend) and a **project instance**
(`project/`, specific to this repo).

```
CLAUDE.md                     # PORTABLE — stack-agnostic engineering standards (stays at repo root)
.githooks/pre-commit          # PORTABLE — git pre-commit audit hook (enable: git config core.hooksPath .githooks)
.claude/
├── README.md                 # PORTABLE — this file
├── workflow.md               # PORTABLE — the working loop + agent routing
├── settings.json             # PORTABLE — shared permissions + commit-audit hook (committed)
├── settings.local.json       # personal config (gitignored)
├── agents/                   # PORTABLE — subagents (backend / frontend / infra / quality)
├── rules/                    # PORTABLE — stack rules auto-apply by file type
│   ├── code-review.md        #   core, always-on review checklist (stack-agnostic)
│   ├── commits.md            #   core, always-on commit conventions
│   ├── security.md           #   core, always-on web/app security
│   ├── dotnet.md             #   pack: dotnet — paths **/*.cs (C# conventions, async)
│   ├── controllers.md        #   pack: dotnet — paths **/Controllers/**
│   ├── repositories.md       #   pack: dotnet — paths **/*Repository.cs
│   ├── services.md           #   pack: dotnet — paths **/Services/**
│   ├── frontend.md           #   pack: frontend — paths **/*.{ts,tsx,vue,...}
│   └── testing.md            #   pack: dotnet — paths test files
├── commands/                 # PORTABLE — slash commands (/claude-audit, /kit-init)
├── scripts/                  # PORTABLE — kit utilities (claude-audit.py)
├── hooks/                    # PORTABLE — hook scripts (pre-commit-audit.sh, session-start.sh)
├── .kit-version              # PORTABLE — installed kit version (stamped by install.py)
├── .kit-packs                # PORTABLE — selected stack packs, or "all" (stamped by install.py)
└── project/                  # PROJECT-SPECIFIC — do NOT copy to other repos
    ├── context.md            #   profile: stack, layout, conventions, key libraries
    ├── tech-debt.md          #   accepted rule violations (register)
    ├── decisions.md          #   decisions & learnings (the team's committed project memory)
    └── …                     #   other repo-specific docs (refactor plans, ADRs)
```

## Reusing this in another project

1. From the kit repo, run `python install.py /path/to/your/project` (see the root
   README). The installer copies the portable files, stamps `.kit-version`, and **runs the
   kit's own audit** on the result — so a fresh install is consistent by construction.
2. In the new repo, run **`/kit-init`** once. It inspects the codebase (language,
   framework, layout, key libraries, test setup), writes `.claude/project/context.md`,
   and wires the git pre-commit audit hook. No manual editing of the template needed — the
   portable files use generic globs and defer project specifics to `context.md`.
3. **Pick your scope.** The kit ships every pack, so a full install (or a plain copy-paste of
   this folder) works in any stack — agents are inert until invoked and rules self-scope by
   file type. For a lean, stack-matched install, pass `python install.py --packs=…`, run
   `install.py prune`, or let `/kit-init` trim to the detected stack. Stack-specific files
   carry a `pack:` frontmatter tag (`dotnet`/`frontend`); untagged files are core and always
   kept. `install.py update` honors whatever selection is recorded in `.kit-packs`.

> The portable layer degrades gracefully: even before `context.md` exists, the generic
> rules and standards apply. **Stack rules fire by file type** — `dotnet.md` only on `.cs`,
> `frontend.md` only on `.ts/.tsx/.vue` — so the same kit works in a backend *or* frontend
> repo with nothing to edit.

## How the pieces load

| Location | When it loads | Notes |
|---|---|---|
| `CLAUDE.md` (repo root) | Every session | Always-on core standards. |
| `rules/*.md` **without** `paths` | Every session | e.g. `code-review.md`, `security.md`. |
| `rules/*.md` **with** `paths` | When Claude opens a matching file | e.g. `repositories.md`. |
| `project/context.md` | When referenced (or created on first run) | Project profile; read before project work. |
| `agents/**` | On delegation | Identity comes from the `name` frontmatter; subfolders are organization only. |
| `project/` docs | On demand | Read only when linked. |

## Maintaining the kit

Run **`/claude-audit`** (or `python .claude/scripts/claude-audit.py`) to check the kit's
consistency: broken links, agent/rule frontmatter, agent-name uniqueness, stale path
references, and project-name leakage into portable files. It's deterministic — no agent
needed for the mechanical checks; use the main session for judgment work (new agents, ADRs).

## Source control

- **Commit** everything here **except** `settings.local.json` (personal, gitignored).
- `project/` **is** committed in each repo (the team needs that project's context + docs); it's simply **not carried** to other repos.

## Conventions

- Agent/rule files: **kebab-case**. Agent identity = the `name` frontmatter field, not the filename or folder. Keep `name` values unique across `agents/`.
