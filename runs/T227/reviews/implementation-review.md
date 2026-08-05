---

## Review — T227: Add pull and local backend/frontend redeployment action to AI Workspace chat

### Summary

The implementation delivers the full end-to-end redeployment flow described in the ticket: natural-language request → LLM proposal → confirmation card → background executor → polling-based progress → success/failure report. The security architecture is sound: host paths are never sent to the frontend, LLM-supplied branches are stripped, service names come only from server-side config, and all execution is allowlisted. Test coverage is broad (826 lines for the supervisor alone, plus proxy and frontend tests).

---

### Correctness vs. Ticket Requirements

| Requirement | Status | Notes |
|---|---|---|
| Resolve current/named project | ✅ | project_id from URL path; config whitelist enforces authorization |
| Resolve repo, branch, services | ✅ | From YAML config only |
| Structured action proposal | ✅ | Stored as pending action with UUID |
| Confirmation card with all required fields | ✅ | project, safe_identifier, branch, pull flag, components, dirty warning |
| Human confirmation before mutation | ✅ | No git/docker commands before confirm endpoint |
| Delegate to Supervisor | ✅ | Control API is a thin authenticated proxy |
| Pull configured branch (ff-only) | ✅ | `git pull --ff-only origin {default_branch}` |
| Rebuild/restart components | ✅ | `docker compose up -d --build {service}` per component |
| Progress reporting | ✅ | Polling every 2 s; PULLING, BUILDING_{component} stages visible |
| Success: revision + preview URL | ✅ | `deployed_sha`, `preview_url`, `result_message` |
| Failure: stage + log excerpt | ✅ | `error_stage`, `error_excerpt` (capped at 500 chars) |
| Concurrent deployment prevention | ✅ | Per-project non-blocking lock → 409 |
| Refuse unknown/unconfigured project | ✅ | Returns informational intent |
| Refuse dirty repo (allow_dirty=false) | ✅ | DIRTY_CHECK failure at execution time |
| Refuse wrong branch | ✅ | BRANCH_MISMATCH failure |
| No LLM-generated shell commands | ✅ | LLM branch param stripped; service names from config |
| Existing Workspace behavior unchanged | ✅ | All pre-existing capabilities pass through unchanged |
| Audit logging | ⚠️ | Python `logger.info` calls only; no persistent/structured audit record |
| VERIFYING stage | ⚠️ | Defined in frontend STAGE_LABELS but never set by backend |

---

### Issues Found

#### Minor — `_git_has_local_changes` does not check `returncode`

`services/supervisor/main.py:2910`

```python
def _git_has_local_changes(repo_path: str) -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], ...)
    return bool(result.stdout.strip())  # returncode not checked
```

If git returns a non-zero exit code (e.g. not a git repository), `result.stdout` is typically empty, so the function returns `False` — silently reporting "no dirty changes" when the real answer is "git failed." At proposal time errors are caught by `except Exception`, so the dirty warning is `None` (neutral). At execution time, the branch check catches git failures first. The bug is practically harmless today, but a future caller could be misled.

**Suggestion:** Check `result.returncode` and raise a clear exception on failure.

---

#### Minor — `_deployment_jobs` grows without bound

`services/supervisor/main.py:2888`

Jobs are written to `_deployment_jobs` on confirmation and never removed. In a long-running supervisor process, every deployment accumulates indefinitely. Under normal dev-factory usage this is not a crisis, but it's a slow memory leak.

**Suggestion:** Evict completed jobs older than a few hours in a cleanup pass or cap the registry size.

---

#### Minor — `_pending_workspace_actions` is never expired

Pending actions are removed on confirm but never on abandon. If a user sees a confirmation card and closes the tab, the entry stays in `_pending_workspace_actions` forever.

**Suggestion:** Add a TTL check at proposal time or a periodic sweep (consistent with any similar pattern already used for `_pending_workspace_issues`).

---

#### Minor — VERIFYING stage defined but not implemented

`apps/dashboard/src/components/ProjectWorkspacePanel.jsx:9`

```js
VERIFYING: 'Verifying…',
```

The label exists and the ticket lists VERIFYING as a suggested state, but the backend never sets `stage = "VERIFYING"`. `docker compose up -d --build` will propagate a non-zero exit code if the container fails to start, so a basic health signal is implicit, but the stage is dead UI code.

**Suggestion:** Either remove `VERIFYING` from STAGE_LABELS, or add a `docker compose ps --filter status=running` check after build and set the stage before it. (Not blocking — ticket says "suggested states".)

---

#### Observation — `_forward` in control_api now catches all 4xx

`services/control_api/routes/workspace.py`

The original code explicitly whitelisted 403/404/422 and >=500 for error propagation; any other 4xx (e.g. 400, 409) would fall through to `return resp.json()` and appear as a success response. The new code uses `>= 400` which is strictly more correct and required to surface the 409 concurrent-deployment response.

This is a behavior improvement, but it changes the response shape for any pre-existing code path that returned a non-whitelisted 4xx and expected the caller to receive a JSON body as a 200. No such case exists in the visible codebase, so this is safe.

---

#### Observation — No validation that `repository_path` is absolute

`services/supervisor/main.py:3421`

```python
repo_path = project_block["repository_path"]
```

A relative path in the YAML config would resolve against the supervisor's CWD. There is no validation at load or execution time. This requires a misconfigured server config to exploit, so the risk is low, but `Path(repo_path).is_absolute()` would be a cheap guard.

---

#### Observation — Audit trail is logging-only

The ticket requires: _"Record the request, confirmation, resolved action, executor result, and actor in the audit trail."_

The implementation logs key events via `logger.info` (chat, confirm, stage transitions, success/failure). This is consistent with how the rest of the supervisor records events. However, there is no structured/persistent audit record. If the system later needs audit queries, log grep is the only option. This is acceptable given the current architecture but is worth tracking for a future ticket.

---

### Code Quality

The implementation is well-structured: helpers are short, the pipeline in `_run_redeploy_job` is linear with clear checkpoints, error extraction is uniform. The `finally: lock.release()` pattern is correct. The test coverage is thorough (config, proposal, confirmation, all job failure modes, lock release on error/exception, polling endpoint, proxy behavior). No hardcoded secrets, no unsafe exec patterns.

---

### Scope Compliance

The implementation is tightly scoped to T227. No unrelated behavior is changed. The `_forward` consolidation in control_api is a minor side-effect improvement that does not introduce new behavior for unrelated routes.

---

### Verdict

All acceptance criteria are met. The issues above are minor robustness/hygiene concerns that do not compromise correctness, security, or the acceptance criteria. The implementation is safe to merge.

IMPLEMENTATION_APPROVED
