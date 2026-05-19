#!/usr/bin/env bash
# Initialize the runtime root directory structure.
# Safe to call multiple times — all mkdir -p.
set -euo pipefail

RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-/runtime}"

mkdir -p \
  "${RUNTIME_ROOT}/runs" \
  "${RUNTIME_ROOT}/worktrees" \
  "${RUNTIME_ROOT}/clones" \
  "${RUNTIME_ROOT}/logs" \
  "${RUNTIME_ROOT}/state" \
  "${RUNTIME_ROOT}/registry" \
  "${RUNTIME_ROOT}/.runtime"

# Best-effort migration: copy artifacts from old locations to canonical ones.
# Safe to run multiple times — never overwrites existing files.

# DB: from /app/.runtime/ (old Docker layout where DB lived in the repo root)
if [ -f "/app/.runtime/ai-dev-factory.sqlite" ] && [ ! -f "${RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite" ]; then
    echo "migrating: /app/.runtime/ai-dev-factory.sqlite → ${RUNTIME_ROOT}/.runtime/"
    cp "/app/.runtime/ai-dev-factory.sqlite" "${RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite"
fi

# workers.json: from runs/ to state/ (state files now live outside the ticket tree)
if [ -f "${RUNTIME_ROOT}/runs/workers.json" ] && [ ! -f "${RUNTIME_ROOT}/state/workers.json" ]; then
    echo "migrating: workers.json runs/ → state/"
    cp "${RUNTIME_ROOT}/runs/workers.json" "${RUNTIME_ROOT}/state/workers.json"
fi

# .issue-intake.json: from runs/ to state/
if [ -f "${RUNTIME_ROOT}/runs/.issue-intake.json" ] && [ ! -f "${RUNTIME_ROOT}/state/.issue-intake.json" ]; then
    echo "migrating: .issue-intake.json runs/ → state/"
    cp "${RUNTIME_ROOT}/runs/.issue-intake.json" "${RUNTIME_ROOT}/state/.issue-intake.json"
fi

echo "runtime root ready: ${RUNTIME_ROOT}"
