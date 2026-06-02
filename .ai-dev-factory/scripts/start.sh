#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# ── Port + URL resolution ────────────────────────────────────────────────────
#
# Sandbox runs allocate isolated ports and pretty URLs and inject
# them via the process env (API_PORT / WEB_PORT /
# AI_DEV_FACTORY_SUPERVISOR_PORT / AI_DEV_FACTORY_SUPERVISOR_URL /
# AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL / SANDBOX_API_URL /
# SANDBOX_WEB_URL). The main runtime normally reads its ports from
# ``deploy/.env`` or falls back to documented defaults.
#
# When both an injected value and a deploy/.env value exist, the
# **sandbox-injected value wins** — otherwise sourcing deploy/.env
# would silently downgrade the sandbox to the main runtime's
# 8080/3000/8090 ports and produce false-positive healthchecks
# against the main runtime.
#
# Implementation: snapshot inbound env, source deploy/.env, then
# restore the snapshot as the final answer.

__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"
__SB_SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-}"
__SB_API_URL="${SANDBOX_API_URL:-}"
__SB_WEB_URL="${SANDBOX_WEB_URL:-}"
__SB_SUPERVISOR_ALREADY_STARTED="${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-}"
__SB_SANDBOX_ID="${SANDBOX_ID:-}"

# shellcheck source=/dev/null
[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
# AI_DEV_FACTORY_SUPERVISOR_URL is consumed by Docker containers (it
# must use host.docker.internal which is not resolvable from host
# shells). Host-side scripts probe a separate URL — see below.
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://host.docker.internal:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL="${__SB_SUPERVISOR_HEALTH_URL:-${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
# Pretty URLs: only set in sandbox mode (or when an operator manually
# sets them for the main runtime). When unset, the URL block below
# falls back to direct host:port for both display and probes.
SANDBOX_API_URL="${__SB_API_URL:-${SANDBOX_API_URL:-}}"
SANDBOX_WEB_URL="${__SB_WEB_URL:-${SANDBOX_WEB_URL:-}}"
AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED="${__SB_SUPERVISOR_ALREADY_STARTED:-${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-0}}"
SANDBOX_ID="${__SB_SANDBOX_ID:-${SANDBOX_ID:-}}"
export API_PORT WEB_PORT
export AI_DEV_FACTORY_SUPERVISOR_PORT AI_DEV_FACTORY_SUPERVISOR_URL
export AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL
export SANDBOX_API_URL SANDBOX_WEB_URL
export AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED
export SANDBOX_ID

unset __SB_API_PORT __SB_WEB_PORT
unset __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL __SB_SUPERVISOR_HEALTH_URL
unset __SB_API_URL __SB_WEB_URL __SB_SUPERVISOR_ALREADY_STARTED __SB_SANDBOX_ID

# Fail fast: named environment deploys require a non-empty SANDBOX_ID so
# docker-compose aliases (sandbox-<id>-api) match Traefik backend targets.
if [ -n "${COMPOSE_PROJECT_NAME:-}" ] && [ -z "${SANDBOX_ID:-}" ]; then
  echo "start: ERROR — SANDBOX_ID is not set for named environment (COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME})" >&2
  exit 1
fi

RUN_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
mkdir -p "$RUN_DIR"

# Write runtime compose env file so SANDBOX_ID is injected deterministically
# into compose interpolation rather than relying on shell-env inheritance.
printf 'SANDBOX_ID=%s\n' "${SANDBOX_ID}" > "${RUN_DIR}/.env.compose"
echo "start: compose env — SANDBOX_ID=${SANDBOX_ID:-<empty>}"
echo "start: compose env files — deploy/.env ${RUN_DIR}/.env.compose"

SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"

# ── Supervisor ───────────────────────────────────────────────────────────────
#
# Sandbox validation starts the supervisor in run_sandbox.py before
# invoking this script. Starting again here would bind the same port
# twice ([Errno 48] address already in use).

if [ "${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-0}" = "1" ]; then
  echo "start: supervisor already managed by sandbox worker, skipping startup"
elif [ -f "$SUPERVISOR_PID_FILE" ] && kill -0 "$(cat "$SUPERVISOR_PID_FILE")" 2>/dev/null; then
  echo "start: supervisor already running (PID $(cat "$SUPERVISOR_PID_FILE"))"
else
  if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    echo "start: ERROR — .venv not found, run bootstrap.sh first" >&2
    exit 1
  fi
  echo "start: starting supervisor on port ${AI_DEV_FACTORY_SUPERVISOR_PORT}..."
  bash "$PROJECT_ROOT/deploy/start_supervisor.sh" &
  SUPERVISOR_PID=$!
  echo "$SUPERVISOR_PID" > "$SUPERVISOR_PID_FILE"
  echo "start: supervisor started (PID $SUPERVISOR_PID)"
  sleep 2
fi

# ── Docker stack ─────────────────────────────────────────────────────────────

echo "start: starting Docker stack..."
if [ -f deploy/.env ]; then
  # Validate compose alias resolution before starting any container.
  # Failures here mean SANDBOX_ID was not propagated to compose interpolation.
  if [ -n "${SANDBOX_ID:-}" ]; then
    _cfg_output=$(docker compose \
      --env-file deploy/.env \
      --env-file "${RUN_DIR}/.env.compose" \
      config 2>&1) || true
    _project_name=$(printf '%s\n' "$_cfg_output" | grep '^name:' | head -1 | cut -d' ' -f2 || true)
    echo "start: compose config — effective project=${_project_name:-unknown}"
    _alias_hit=$(printf '%s\n' "$_cfg_output" | grep "sandbox-${SANDBOX_ID}-" || true)
    if [ -z "$_alias_hit" ]; then
      echo "start: ERROR — compose config alias mismatch: expected sandbox-${SANDBOX_ID}-* but got:" >&2
      printf '%s\n' "$_cfg_output" | grep "sandbox-" >&2 || echo "  (no sandbox- aliases in config output)" >&2
      exit 1
    fi
    echo "start: compose config alias ok — sandbox-${SANDBOX_ID}-*"
  fi
  docker compose \
    --env-file deploy/.env \
    --env-file "${RUN_DIR}/.env.compose" \
    up -d
else
  docker compose up -d
fi

# ── Runtime network attachment (compatibility fallback) ──────────────────────
#
# Ensures routed services (api, web) join the shared ingress network so
# Traefik can resolve their per-sandbox aliases by DNS.
#
# Modern compose files declare ai-dev-factory-runtime directly and containers
# are attached at compose-up time. This block is a safety net for older
# branches/worktrees where the declaration may be absent.

if [ -n "${SANDBOX_ID:-}" ]; then
  _RUNTIME_NETWORK="ai-dev-factory-runtime"
  _repaired=0

  if [ -f deploy/.env ]; then
    _compose_opts=(--env-file deploy/.env --env-file "${RUN_DIR}/.env.compose")
  else
    _compose_opts=(--env-file "${RUN_DIR}/.env.compose")
  fi

  for _svc in api web; do
    _alias="sandbox-${SANDBOX_ID}-${_svc}"
    _cid=$(docker compose "${_compose_opts[@]}" ps -q "$_svc" 2>/dev/null || true)
    _cid=$(printf '%s' "$_cid" | tr -d '[:space:]')
    if [ -z "$_cid" ]; then
      echo "start: network attach — ${_svc} container not found, skipping"
      continue
    fi
    _nets=$(docker inspect "$_cid" \
      --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true)
    if printf '%s\n' "$_nets" | grep -qF "$_RUNTIME_NETWORK"; then
      echo "start: network attach — ${_svc} already on ${_RUNTIME_NETWORK}"
    else
      echo "start: network attach — connecting ${_svc} to ${_RUNTIME_NETWORK} (legacy compose)"
      _conn_out=$(docker network connect \
        --alias "$_alias" "$_RUNTIME_NETWORK" "$_cid" 2>&1) || true
      if printf '%s\n' "$_conn_out" | grep -qiE "already exists|endpoint with name"; then
        echo "start: network attach — ${_svc} already connected (idempotent)"
      elif [ -n "$_conn_out" ]; then
        echo "start: ERROR — ${_svc} connect to ${_RUNTIME_NETWORK} failed: ${_conn_out}" >&2
        exit 1
      else
        echo "start: network attach — ${_svc} connected as ${_alias}"
        _repaired=1
      fi
    fi
  done

  if [ "$_repaired" = "1" ]; then
    echo "start: runtime network attachment repaired for legacy compose config"
  fi

  # Post-attach validation: confirm both services joined the runtime network.
  for _svc in api web; do
    _cid=$(docker compose "${_compose_opts[@]}" ps -q "$_svc" 2>/dev/null || true)
    _cid=$(printf '%s' "$_cid" | tr -d '[:space:]')
    [ -z "$_cid" ] && continue
    _nets=$(docker inspect "$_cid" \
      --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true)
    if ! printf '%s\n' "$_nets" | grep -qF "$_RUNTIME_NETWORK"; then
      echo "start: ERROR — ${_svc} not attached to ${_RUNTIME_NETWORK} after connect attempt" >&2
      echo "start:   container=${_cid} networks=[${_nets}]" >&2
      exit 1
    fi
  done
fi

# ── Resolved URLs ────────────────────────────────────────────────────────────
#
# Announce the URLs that the human operator (and healthcheck.sh)
# will actually probe. When the sandbox supplied pretty URLs, those
# are printed instead of ``localhost:<port>`` so the dashboard /
# CLI log matches the browser experience.

echo "start: done"
if [ -n "${SANDBOX_API_URL:-}" ]; then
  echo "start:   API        ${SANDBOX_API_URL}"
else
  echo "start:   API        http://localhost:${API_PORT}"
fi
if [ -n "${SANDBOX_WEB_URL:-}" ]; then
  echo "start:   web        ${SANDBOX_WEB_URL}"
else
  echo "start:   web        http://localhost:${WEB_PORT}"
fi
echo "start:   supervisor ${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL}"
if [ -n "${SANDBOX_ID:-}" ]; then
  echo "start:   sandbox    ${SANDBOX_ID}"
fi
