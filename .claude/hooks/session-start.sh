#!/bin/sh
# SessionStart hook — toolchain-agnostic environment bootstrap.
#
# The KIT provides the plumbing; the TOOLCHAIN specifics live in YOUR repo. This runs
# at the start of every Claude Code session and looks for a project setup script:
#
#   1. $KIT_SETUP_SCRIPT, if set, is the script to run (any path).
#   2. otherwise the first match of scripts/setup*.sh (e.g. scripts/setup.sh or
#      scripts/setup-dotnet.sh) is used.
#
# Use this in cloud/web containers that start without your toolchain (install the .NET
# SDK, restore packages, activate a venv, set PATH, …). Put those commands in your
# repo's setup script; this hook just finds and runs it.
#
# Safe by design: if there is no setup script it is a no-op, and a setup failure is
# warned but never fatal — a missing toolchain must not block the session from starting.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" 2>/dev/null || exit 0

SETUP=""
if [ -n "${KIT_SETUP_SCRIPT:-}" ] && [ -f "${KIT_SETUP_SCRIPT}" ]; then
  SETUP="${KIT_SETUP_SCRIPT}"
else
  for candidate in scripts/setup*.sh; do
    if [ -f "${candidate}" ]; then
      SETUP="${candidate}"
      break
    fi
  done
fi

if [ -z "${SETUP}" ]; then
  exit 0  # no project setup script — nothing to bootstrap
fi

echo "SessionStart: running project setup (${SETUP})…" >&2
if sh "${SETUP}"; then
  echo "SessionStart: setup complete." >&2
else
  echo "SessionStart: setup script exited non-zero — continuing anyway." >&2
fi
exit 0
