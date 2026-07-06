# Skills

A skill is a directory under `skills/` containing a `SKILL.md` file plus any
supporting files (scripts, references, templates). Claude Code discovers skills
automatically and can invoke them when their `description` matches the task.

Layout:

```
skills/
└── my-skill/
    ├── SKILL.md          # required
    ├── helper.py         # optional supporting files
    └── reference.md      # optional
```

This README is a format guide and keepfile — create your own `skills/<name>/SKILL.md`
beside it.

## Frontmatter

```markdown
---
name: pdf-extract                            # optional — defaults to the directory name
description: Extract text and tables from PDFs.  # required — how Claude decides to use it
allowed-tools: Bash, Read, Write             # optional — restrict tools while the skill runs
disable-model-invocation: false              # optional — set true to require explicit invocation
---
```

| Field                      | Required | Purpose                                                      |
| -------------------------- | -------- | ------------------------------------------------------------ |
| `description`              | yes      | Tells Claude when to use the skill. Make it specific.        |
| `name`                     | no       | Identifier; defaults to the skill's directory name.          |
| `allowed-tools`            | no       | Tool allowlist active while the skill runs.                  |
| `disable-model-invocation` | no       | If `true`, Claude won't auto-invoke; user must call it.      |

## Body

The body is the skill's instructions — what to do, step by step. Reference supporting
files by relative path; Claude can read them when the skill runs.

## Example

`skills/changelog/SKILL.md`:

```markdown
---
name: changelog
description: Add an entry to CHANGELOG.md following Keep a Changelog format.
allowed-tools: Read, Edit
---

When asked to record a change:

1. Read `CHANGELOG.md`.
2. Find or create the `## [Unreleased]` section.
3. Add the change under the right subsection (Added / Changed / Fixed / Removed).
4. Keep entries terse and user-facing.
```
