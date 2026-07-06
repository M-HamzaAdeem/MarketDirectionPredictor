# Slash commands

Each `*.md` file in this directory becomes a slash command. The filename (without
`.md`) is the command name. Nested subdirectories create namespaced commands.

- **Copy-in users** invoke a command as `/name`.
- **Plugin users** invoke it as `/ezd-claude-kit:name`.

This README is a format guide and keepfile — drop your own `*.md` commands beside it.

## Frontmatter

```markdown
---
description: Short summary shown in the command list.   # required
argument-hint: <issue-number>                           # optional — shown after the command name
allowed-tools: Bash(git status:*), Read, Edit           # optional — restrict tools for this command
model: claude-sonnet-4-6                                # optional — override the model for this command
---
```

| Field           | Required | Purpose                                                        |
| --------------- | -------- | -------------------------------------------------------------- |
| `description`   | yes      | One line shown in the `/` command picker.                      |
| `argument-hint` | no       | Hint text for expected arguments.                              |
| `allowed-tools` | no       | Whitelist of tools the command may use.                        |
| `model`         | no       | Pin a specific model for this command.                         |

## Body

The body is the prompt sent to Claude. You can interpolate:

- `$ARGUMENTS` — everything the user typed after the command.
- `$1`, `$2`, … — individual positional arguments.
- `!command` — run a shell command and inline its output (e.g. `!git diff --staged`).
- `@path/to/file` — inline the contents of a file.

## Example

`review-pr.md`:

```markdown
---
description: Review the staged diff for bugs and style issues.
argument-hint: [focus-area]
allowed-tools: Bash(git diff:*), Read
---

Review the following staged changes, focusing on $ARGUMENTS if provided.

Diff:
!git diff --staged
```
