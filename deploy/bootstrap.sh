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

echo "runtime root ready: ${RUNTIME_ROOT}"
