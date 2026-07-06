# Subagents

Each `*.md` file in this directory defines a subagent — a specialized assistant that
Claude Code can delegate focused tasks to, with its own system prompt and (optionally)
its own tool allowlist and model.

This README is a format guide and keepfile — drop your own `*.md` agents beside it.

## Frontmatter

```markdown
---
name: code-reviewer                                     # required — the agent's identifier
description: Reviews diffs for bugs and style issues.   # required — when to use this agent
tools: Read, Grep, Bash(git diff:*)                     # optional — restrict tools (defaults to all)
model: claude-sonnet-4-6                                # optional — override the model
---
```

| Field         | Required | Purpose                                                          |
| ------------- | -------- | ---------------------------------------------------------------- |
| `name`        | yes      | Unique identifier used to invoke/select the agent.              |
| `description` | yes      | Tells Claude when to delegate to this agent. Be specific.        |
| `tools`       | no       | Comma-separated tool allowlist. Omit to inherit all tools.       |
| `model`       | no       | Pin a specific model for this agent.                             |

## Body

Everything after the frontmatter is the agent's **system prompt**. Write it as
direct instructions to the agent: its role, how it should work, what it should
return, and any constraints.

## Example

`test-writer.md`:

```markdown
---
name: test-writer
description: Writes unit tests for a given module. Use when new code lacks coverage.
tools: Read, Write, Edit, Bash
---

You are a focused test author. Given a target module:

1. Read the module and its existing tests.
2. Identify uncovered branches and edge cases.
3. Write tests that match the project's existing testing conventions.
4. Run the test suite and report results.

Return a summary of what you added and the final test outcome.
```
