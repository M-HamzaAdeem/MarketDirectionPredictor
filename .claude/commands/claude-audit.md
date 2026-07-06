---
description: Audit the .claude kit for consistency — broken links, frontmatter, agent-name uniqueness, and project-name leakage.
allowed-tools: Bash, Read, Edit
---

Run the consistency audit for the `.claude/` configuration kit:

```
python .claude/scripts/claude-audit.py
```

Then report a concise summary:
- State the overall **RESULT** (PASS / PASS with warnings / FAIL).
- For each section with issues, list the offending files/items verbatim.
- If there are **FAIL** items (broken links, invalid frontmatter, duplicate agent names), offer to fix them — do **not** edit anything until the user confirms.
- Treat **WARN** items (stale backtick refs, project-name leakage) as advisory; mention them but don't block.

Do not modify any files as part of the audit itself.
