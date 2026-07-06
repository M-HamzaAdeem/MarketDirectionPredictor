#!/usr/bin/env python3
"""claude-audit.py — consistency audit for the .claude kit (portable, stack-agnostic).

FAIL (exit 1): broken links, invalid agent/rule frontmatter, duplicate agent names.
WARN (exit 0): stale backtick path refs, project-name leakage, context.md drift.

Cross-platform (Windows + Linux + macOS). Standard library only — no dependencies.

On a commit, --pre-commit and --hook additionally run the REVIEW GATE: if source files
changed since the last commit without a recorded code-review (.claude/.last-review), the
commit is BLOCKED for Claude (--hook) and WARNED for humans (--pre-commit). Reviewer agents
record the review with --record-review; [skip-review] in the commit message bypasses it.

Usage:
    python claude-audit.py [ROOT] [--pre-commit | --hook | --record-review]

    ROOT            Directory to audit (default: git toplevel, else CWD).
    (no flag)       Run the audit and print the full report. Exit 1 on FAIL, else 0.
    --pre-commit    Silent on PASS; on FAIL print guidance + report to stderr and
                    exit 2. Use from a git pre-commit hook (any non-zero blocks).
                    Also warns (does not block) on a pending review.
    --hook          Claude Code PreToolUse(Bash) gate. Reads the hook payload on
                    stdin, and runs the audit ONLY when the command is a `git commit`
                    (allowing every other Bash call through with exit 0). Hook
                    matchers filter on tool NAME only, so this command-level gate has
                    to live here, in the script — not in settings.json. Blocks the
                    commit (exit 2) on a structural FAIL or a pending review.
    --record-review Stamp .claude/.last-review with the current HEAD, then exit 0.
                    Reviewer agents call this when their review is complete.
"""

import argparse
import json
import os
import re
import subprocess
import sys

LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
BACKTICK_RE = re.compile(r"`(\.claude/[^`]+)`")
SLN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+\.sln", re.IGNORECASE)
EXT_RE = re.compile(r"\.(sln|csproj|cs|md|json|ya?ml|sh|txt)$", re.IGNORECASE)


def repo_root():
    """Git top-level, or the current directory if not in a repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        top = out.stdout.strip()
        if out.returncode == 0 and top:
            return os.path.abspath(top)
    except OSError:
        pass
    return os.getcwd()


def command_from_hook_stdin():
    """Extract tool_input.command from a PreToolUse JSON payload on stdin.

    Returns the command string, or None if there is no payload / it doesn't parse /
    it carries no command. Never raises — a hook must fail open, not crash.
    """
    try:
        data = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if not data or not data.strip():
        return None
    try:
        payload = json.loads(data)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    cmd = tool_input.get("command")
    return cmd if isinstance(cmd, str) else None


# git global options that take a value, so the value token must be skipped when
# scanning for the subcommand (e.g. `git -c core.x=y commit`).
_GIT_OPTS_WITH_VALUE = {
    "-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
}


def looks_like_git_commit(command):
    """True if `command` invokes `git commit` in any of its simple sub-commands.

    Handles compound commands (split on && || ; | newline), env-var prefixes
    (`FOO=bar git commit`), a path to git (`/usr/bin/git`, `git.exe`), and git
    global options before the subcommand (`git -c k=v --no-pager commit`). Avoids
    false positives like `git log --grep commit`.
    """
    if not command:
        return False
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        tokens = segment.split()
        i = 0
        # Skip leading VAR=value environment assignments.
        while i < len(tokens) and "=" in tokens[i] and not tokens[i].startswith("-"):
            i += 1
        if i >= len(tokens):
            continue
        if os.path.basename(tokens[i]).lower() not in ("git", "git.exe"):
            continue
        i += 1
        # Skip git's global options (and any values they consume).
        while i < len(tokens):
            tok = tokens[i]
            if tok in _GIT_OPTS_WITH_VALUE:
                i += 2
            elif tok.startswith("-"):
                i += 1
            else:
                break
        if i < len(tokens) and tokens[i] == "commit":
            return True
    return False


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def md_files(root):
    """Every *.md under .claude/, plus CLAUDE.md at the root."""
    out = []
    claude_dir = os.path.join(root, ".claude")
    if os.path.isdir(claude_dir):
        for dirpath, dirnames, filenames in os.walk(claude_dir):
            dirnames.sort()
            for name in sorted(filenames):
                if name.endswith(".md"):
                    out.append(os.path.join(dirpath, name))
    claude_md = os.path.join(root, "CLAUDE.md")
    if os.path.isfile(claude_md):
        out.append(claude_md)
    return out


def find_under(root, subpath, predicate):
    """All files under root/subpath (recursively) matching predicate(name)."""
    base = os.path.join(root, *subpath.split("/"))
    out = []
    if os.path.isdir(base):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for name in sorted(filenames):
                if predicate(name):
                    out.append(os.path.join(dirpath, name))
    return out


def agent_files(root):
    return find_under(
        root, ".claude/agents", lambda n: n.endswith(".md") and n != "README.md"
    )


def rule_files(root):
    return find_under(
        root, ".claude/rules", lambda n: n.endswith(".md") and n != "README.md"
    )


def has_line(text, prefix):
    return any(line.startswith(prefix) for line in text.splitlines())


def first_line_is_fence(text):
    lines = text.splitlines()
    return bool(lines) and lines[0].strip() == "---"


def find_csproj(root, filename, maxdepth=3):
    """True if `filename` exists within `maxdepth` levels below root."""
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root) :].count(os.sep)
        if depth >= maxdepth:
            dirnames[:] = []
        if filename in filenames:
            return True
    return False


# --- Review gate ----------------------------------------------------------------
# The kit's workflow requires a code-review before code is committed. This enforces it:
# the reviewer agents stamp the reviewed commit into .claude/.last-review (via
# --record-review), and a commit that changes source files without a matching record is
# BLOCKED for Claude (--hook) and WARNED for humans (--pre-commit). [skip-review] in the
# commit message bypasses it (trivial edits); docs/config-only commits never trigger it.

REVIEW_MARKER = ".claude/.last-review"

_NON_SOURCE_EXT = (
    ".md", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".lock", ".txt",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
)
_NON_SOURCE_BASENAMES = {
    "license", "license.txt", "license.md", ".gitignore", ".gitattributes",
    ".editorconfig", ".dockerignore", ".kit-version",
}


def _git(root, git_args):
    """Run a git command in `root`; return (returncode, stdout). Never raises."""
    try:
        out = subprocess.run(["git"] + git_args, capture_output=True, text=True, cwd=root)
        return out.returncode, out.stdout
    except OSError:
        return 1, ""


def current_head(root):
    rc, out = _git(root, ["rev-parse", "HEAD"])
    head = out.strip()
    return head if rc == 0 and head else "ROOT"


def is_source_path(path):
    """True if `path` is code that warrants review (not docs, config, or .claude/)."""
    p = path.replace("\\", "/").lower()
    if p.startswith(".claude/"):
        return False
    base = p.rsplit("/", 1)[-1]
    if base in _NON_SOURCE_BASENAMES:
        return False
    if p.endswith(_NON_SOURCE_EXT):
        return False
    return True


def changed_source_files(root):
    """Source files changed since HEAD (staged + unstaged). None if undeterminable."""
    rc, out = _git(root, ["diff", "HEAD", "--name-only"])
    if rc != 0:  # e.g. no commits yet — fall back to the staged set
        rc, out = _git(root, ["diff", "--cached", "--name-only"])
        if rc != 0:
            return None
    return [f.strip() for f in out.splitlines() if f.strip() and is_source_path(f.strip())]


def read_review_marker(root):
    """The commit recorded as reviewed, or None if there is no marker."""
    path = os.path.join(root, ".claude", ".last-review")
    try:
        if not os.path.isfile(path):
            return None
        content = read(path).strip()
    except OSError:
        return None
    return content.splitlines()[0].strip() if content else None


def commit_message_has_skip(root, command):
    """True if a [skip-review] escape is present (commit command or COMMIT_EDITMSG)."""
    if command and "[skip-review]" in command:
        return True
    path = os.path.join(root, ".git", "COMMIT_EDITMSG")
    try:
        if os.path.isfile(path) and "[skip-review]" in read(path):
            return True
    except OSError:
        pass
    return False


def review_pending(root, command):
    """Guidance string if source changed without a recorded review; else None."""
    changed = changed_source_files(root)
    if not changed:  # None (unknown) or [] (no source) — nothing to enforce
        return None
    if commit_message_has_skip(root, command):
        return None
    if read_review_marker(root) == current_head(root):
        return None  # a review was recorded against the current state
    n = len(changed)
    preview = ", ".join(changed[:5]) + (" ..." if n > 5 else "")
    return (
        f"No code-review recorded for {n} changed source file(s) since the last commit "
        f"({preview}). Run the code-reviewer agent (workflow step 5), apply its findings, "
        "then commit - it records the review automatically. For a trivial edit, add "
        "[skip-review] to the commit message."
    )


def record_review(root):
    """Stamp .claude/.last-review with the current HEAD (called by reviewer agents)."""
    head = current_head(root)
    path = os.path.join(root, ".claude", ".last-review")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(head + "\n")
    print(f"  recorded review marker {REVIEW_MARKER} = {head}")


def run_audit(root):
    """Return (fail, warn, report_lines)."""
    fail = False
    warn = False
    out = [f"Auditing .claude kit at: {root}"]
    project_dir = os.path.join(root, ".claude", "project")
    project_exists = os.path.isdir(project_dir)
    mds = md_files(root)

    # 1. Broken markdown links -------------------------------------------- FAIL
    out += ["", "=== 1. Broken markdown links ==="]
    broken = []
    for f in mds:
        d = os.path.dirname(f)
        for link in LINK_RE.findall(read(f)):
            if link.startswith(("http", "#", "mailto")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            # project/ is the per-repo instance, created on first run. Don't fail
            # links into it until that instance exists.
            if ("/project/" in target or target.startswith("project/")) and not project_exists:
                continue
            if not os.path.exists(os.path.join(d, target)):
                broken.append(f"  BROKEN: {rel(root, f)} -> {link}")
    if broken:
        out += broken
        fail = True
    else:
        out.append("  ok")

    # 2. Stale backtick `.claude/...` path refs --------------------------- WARN
    out += ["", "=== 2. Stale backtick path references (`.claude/...`) ==="]
    stale = []
    for f in mds:
        for p in BACKTICK_RE.findall(read(f)):
            if not os.path.exists(os.path.join(root, p)):
                stale.append(f"  MISSING: {rel(root, f)} -> `{p}`")
    if stale:
        out += stale
        warn = True
    else:
        out.append("  ok")

    # 3. Agent frontmatter + precedence ----------------------------------- FAIL
    agents = agent_files(root)
    out += [
        "",
        "=== 3. Agent frontmatter (name + description required; tools/model optional) + precedence ===",
    ]
    issues = []
    for a in agents:
        text = read(a)
        if not first_line_is_fence(text):
            issues.append(f"  NO FRONTMATTER: {rel(root, a)}")
        for k in ("name", "description"):
            if not has_line(text, k + ":"):
                issues.append(f"  MISSING {k}: {rel(root, a)}")
        if "Project precedence" not in text:
            issues.append(f"  NO PRECEDENCE LINE: {rel(root, a)}")
    if issues:
        out += issues
        fail = True
    else:
        out.append(f"  ok ({len(agents)} agents)")

    # 4. Rule frontmatter ------------------------------------------------- FAIL
    rules = rule_files(root)
    out += ["", "=== 4. Rule frontmatter (description) ==="]
    issues = []
    for r in rules:
        text = read(r)
        if not first_line_is_fence(text):
            issues.append(f"  NO FRONTMATTER: {rel(root, r)}")
        if not has_line(text, "description:"):
            issues.append(f"  MISSING description: {rel(root, r)}")
    if issues:
        out += issues
        fail = True
    else:
        scoped = sum(1 for r in rules if has_line(read(r), "paths:"))
        always = len(rules) - scoped
        out.append(f"  ok ({len(rules)} rules: {always} always, {scoped} scoped)")

    # 5. Agent name uniqueness -------------------------------------------- FAIL
    out += ["", "=== 5. Agent name uniqueness ==="]
    name_lines = []
    for a in agents:
        name_lines += [
            line.rstrip() for line in read(a).splitlines() if line.startswith("name:")
        ]
    seen = {}
    for line in name_lines:
        seen[line] = seen.get(line, 0) + 1
    dupes = sorted(line for line, n in seen.items() if n > 1)
    if dupes:
        out.append("  DUPLICATE NAMES:")
        out += [f"    {d}" for d in dupes]
        fail = True
    else:
        out.append(f"  ok ({len(set(name_lines))} unique)")

    # 6. Project-name leakage into portable files ------------------------- WARN
    out += ["", "=== 6. Project-name leakage into portable files ==="]
    context_md = os.path.join(project_dir, "context.md")
    token = None
    if os.path.isfile(context_md):
        m = SLN_RE.search(read(context_md))
        if m:
            token = m.group()[:-4]  # strip .sln
    if token:
        word_re = re.compile(r"\b" + re.escape(token) + r"\b", re.IGNORECASE)
        portable = []
        for rel_path in ("CLAUDE.md", ".claude/README.md"):
            p = os.path.join(root, *rel_path.split("/"))
            if os.path.isfile(p):
                portable.append(p)
        for sub in (".claude/rules", ".claude/agents", ".claude/commands", ".claude/scripts"):
            portable += find_under(root, sub, lambda n: True)
        hits = [rel(root, p) for p in portable if word_re.search(read(p))]
        if hits:
            out.append(
                f"  Portable files mention project token '{token}' (should live only in .claude/project/):"
            )
            out += [f"    {h}" for h in hits]
            warn = True
        else:
            out.append(f"  ok (no '{token}' in portable files)")
    elif os.path.isfile(context_md):
        out.append("  skipped (no .sln token in context.md)")
    else:
        out.append("  skipped (.claude/project/context.md not present)")

    # 7. context.md references match the codebase ------------------------- WARN
    out += ["", "=== 7. context.md references match the codebase ==="]
    if os.path.isfile(context_md):
        ctx = read(context_md)
        m = SLN_RE.search(ctx)
        prefix = m.group()[:-4] if m else None
        if prefix:
            token_re = re.compile(re.escape(prefix) + r"\.[A-Za-z][A-Za-z0-9]+")
            projs = sorted(
                {t for t in token_re.findall(ctx) if not EXT_RE.search(t)}
            )
            missing = []
            for proj in projs:
                if os.path.isdir(os.path.join(root, proj)):
                    continue
                if find_csproj(root, proj + ".csproj", maxdepth=3):
                    continue
                missing.append(
                    f"  MISSING (referenced in context.md, not found in repo): {proj}"
                )
            if missing:
                out += missing
                warn = True
            else:
                out.append("  ok (referenced projects exist)")
        else:
            out.append("  skipped (no .sln token in context.md)")
    else:
        out.append("  skipped (.claude/project/context.md not present)")

    # Summary -----------------------------------------------------------------
    out += ["", "============================================"]
    if fail:
        out.append("RESULT: FAIL (structural issues above)")
    elif warn:
        out.append("RESULT: PASS with warnings (review above)")
    else:
        out.append("RESULT: PASS - kit is consistent")
    out.append("============================================")
    return fail, warn, out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="claude-audit.py")
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Directory to audit (default: git toplevel, else CWD).",
    )
    gate = parser.add_mutually_exclusive_group()
    gate.add_argument(
        "--pre-commit",
        action="store_true",
        help="Silent on PASS; on FAIL print guidance to stderr and exit 2.",
    )
    gate.add_argument(
        "--hook",
        action="store_true",
        help="PreToolUse(Bash) gate: read the hook payload on stdin and audit only "
        "git-commit commands. Allows every other Bash call through (exit 0).",
    )
    gate.add_argument(
        "--record-review",
        action="store_true",
        help="Stamp .claude/.last-review with the current HEAD, then exit. Reviewer "
        "agents call this when their review is complete.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Reviewer agents call this to record that a review happened, then we're done.
    if args.record_review:
        record_review(os.path.abspath(args.root) if args.root else repo_root())
        return 0

    # --hook self-gates to git commits: the matcher fires this on EVERY Bash call, so
    # we inspect the command and bail out (allow) unless it's an actual `git commit`.
    cmd = None
    if args.hook:
        cmd = command_from_hook_stdin()
        if not looks_like_git_commit(cmd):
            return 0

    root = os.path.abspath(args.root) if args.root else repo_root()
    try:
        os.chdir(root)
    except OSError:
        pass
    fail, _warn, report = run_audit(root)

    if args.pre_commit or args.hook:
        if fail:
            print("BLOCKED: the .claude kit audit FAILED - fix before committing.", file=sys.stderr)
            print("\n".join(report), file=sys.stderr)
            print("Run /claude-audit and resolve the FAIL items, then retry the commit.", file=sys.stderr)
            return 2  # exit 2 = block the tool call; stderr is fed back to Claude
        # Review gate: source changed without a recorded code-review.
        pending = review_pending(root, cmd)
        if pending:
            if args.hook:  # Claude's own commit — block it
                print("BLOCKED: " + pending, file=sys.stderr)
                return 2
            print("WARNING: " + pending, file=sys.stderr)  # human commit — warn, allow
        return 0

    print("\n".join(report))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
