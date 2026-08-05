# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Conflict Resolver

## Mission

Resolve Git merge conflicts in the current ticket worktree by editing conflicted files in-place, preserving both the ticket intent and the latest main branch behavior.

## Tu dois

- lire le fichier `conflict/context.md` qui contient le ticket, le plan, les reviews, le diff PR, les fichiers en conflit et les derniers commits de main
- éditer chaque fichier en conflit pour supprimer les marqueurs de conflit (`<<<<<<<`, `=======`, `>>>>>>>`)
- résoudre chaque conflit de façon raisonnée en conservant l'intent du ticket ET le comportement de main
- écrire un résumé de chaque décision de résolution dans ton output (qui deviendra `conflict/resolution.md`)
- signaler toute incertitude ou limitation

## Tu ne dois pas

- choisir aveuglément `ours` ou `theirs` sans justification
- faire de reset de branche
- merger vers main
- ignorer les fichiers en conflit
- masquer les erreurs ou incertitudes
- modifier des fichiers hors scope de la résolution

## Sortie attendue

La sortie (stdout) doit être `conflict/resolution.md` contenant :
- liste des fichiers résolus avec la décision prise pour chaque conflit
- justification de chaque choix (ticket vs main)
- hypothèses faites si le conflit était ambigu
- limites connues

## Règles de sécurité

- ne jamais résoudre les conflits sur la branche `main`
- ne jamais faire de `git reset --hard`
- ne jamais auto-merger vers main
- ne pas supprimer du code fonctionnel des deux côtés sans justification explicite
- toujours préserver le comportement attendu du ticket en priorité

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# TASK

# Generic Conflict Resolver Task

Read `conflict/context.md` in the run directory. It contains the full ticket context, plan, reviews, PR diff, conflicted files (with conflict markers), and the latest commits on main.

Your task:
1. Edit every conflicted file in-place to remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
2. Resolve each conflict by preserving both the ticket intent and the latest main behavior where possible.
3. Do not blindly pick ours or theirs — reason through each conflict.
4. Write your output (stdout) as `conflict/resolution.md` summarising every conflict decision.

Safety rules:
- Do not reset the branch.
- Do not auto-merge to main.
- Do not blindly choose ours/theirs without justification.
- Preserve both ticket intent and latest main behavior when possible.

The ticket follows.


# Conflict Context — T227

Generated at: 2026-08-02T11:59:21Z

## Metadata

- pre_conflict_state: TEST_COMPLETE
- conflict_detected_at: 2026-08-01T23:19:39Z
- conflict_pr_number: 314
- conflicted_files (source): tests/test_conflict_resolver.py, tools/agent_runner/run_conflict_resolver.py
- skipped_runtime_noise: 0 path(s)

---

## Ticket

# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat

**Source**: GitHub Issue #311

## Description

## Objective

Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.

## User story

As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:

> Pull the latest changes and redeploy the backend and frontend of this project.

so that I can update the locally hosted test environment without connecting manually to the host machine.

## Expected interaction

Example request:

> Pull and redeploy the backend and frontend of Timizer.

The Workspace must:

1. resolve the current or explicitly named project;
2. resolve the configured repository, branch, backend service, and frontend service;
3. prepare a structured redeployment action;
4. show the exact target and operation for human confirmation;
5. delegate the approved action to the Supervisor;
6. pull the configured branch;
7. rebuild and restart the requested local components;
8. return execution status and useful logs to the conversation.

## Structured action

The LLM should produce a constrained action proposal similar to:

```json
{
  "action": "redeploy_project",
  "project_id": "timizer",
  "pull": true,
  "branch": "main",
  "components": ["backend", "frontend"]
}
```

The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.

## Project configuration

Each authorized project must define its local redeployment recipe outside the prompt, for example:

```yaml
projects:
  timizer:
    repository_path: /projects/timizer
    default_branch: main
    redeploy:
      backend:
        service: backend
      frontend:
        service: frontend
```

The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.

## Requirements

- Support natural-language requests targeting:
  - backend only;
  - frontend only;
  - backend and frontend.
- Use the active Workspace project when the request says “this project”.
- Allow an explicit project name only when it resolves to an authorized configured project.
- Use only server-side project configuration and allowlisted operations.
- Route every action through the Supervisor.
- Require human confirmation before running the pull or redeployment.
- The confirmation card must display:
  - project;
  - repository path or safe project identifier;
  - branch;
  - whether a pull will occur;
  - components to rebuild/restart;
  - whether local uncommitted changes were detected.
- Refuse execution when:
  - the project is unknown or not authorized;
  - no redeployment recipe exists;
  - the branch is not allowed;
  - the repository has unsafe local changes according to the configured policy;
  - another deployment for the same project is already running.
- Do not use an unrestricted LLM-generated shell command.
- Stream or periodically return progress for pull, build, restart, and health verification.
- Return concise success or failure output with useful log excerpts.
- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.

## Suggested execution states

- `PROPOSED`
- `AWAITING_CONFIRMATION`
- `PULLING`
- `BUILDING`
- `RESTARTING`
- `VERIFYING`
- `SUCCEEDED`
- `FAILED`

## Acceptance criteria

- From a project Workspace, “pull and redeploy this project” resolves to that project.
- The user can request backend only, frontend only, or both.
- No repository mutation or service restart occurs before confirmation.
- The Supervisor executes only the configured redeployment recipe.
- The selected branch is pulled using the configured safe strategy.
- Backend and frontend services are rebuilt/restarted according to the requested components.
- Concurrent redeployment of the same project is prevented.
- Pull, build, restart, and health-check progress is visible from the chat.
- Success returns the deployed revision and local/preview URL when configured.
- Failure returns the failed stage and actionable log excerpts.
- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
- Existing Workspace conversations and non-mutating chat behavior continue to work.

## Out of scope

- Production or cloud deployment.
- Arbitrary remote shell access.
- Allowing the LLM to compose unrestricted commands.
- Rollback management.
- Multi-host deployment orchestration.

---

## Plan

## Objective

Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by Docker Compose service rebuilds for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow, with the deployment running in a background job so the Supervisor remains responsive.

## Included

### 1. New config file — `services/supervisor/workspace_projects.yml`

Schema per project (loaded at execution time via env var `WORKSPACE_PROJECTS_CONFIG`):

```yaml
projects:
  <project_id>:
    display_name: "Human-readable name"     # optional, shown in confirmation card
    repository_path: /host/path/to/repo
    default_branch: main
    allow_dirty: false         # false → reject if local uncommitted changes exist
    redeploy:
      backend:
        service: backend       # docker compose service name
      frontend:
        service: frontend
    preview_url: http://localhost:3000       # optional, returned on success
```

`_load_workspace_projects_config() -> dict` reads this file; returns `{}` on missing file. Called at each proposal and execution — never cached between requests.

---

### 2. `services/supervisor/main.py`

#### a. New module-level state

```python
# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
_workspace_redeploy_locks: dict[str, threading.Lock] = {}
_workspace_redeploy_locks_mutex = threading.Lock()

# Background deployment job registry
_deployment_jobs: dict[str, dict] = {}        # keyed by deployment_id (UUID)
_deployment_jobs_lock = threading.Lock()
```

#### b. `_get_redeploy_lock(project_id: str) -> threading.Lock`

Follows the existing `_get_analysis_lock` pattern (lazy creation, `_workspace_redeploy_locks_mutex` guards the dict).

#### c. `_load_workspace_projects_config() -> dict`

Reads `WORKSPACE_PROJECTS_CONFIG` env var (default: path relative to supervisor package). Returns `{}` on `FileNotFoundError`. Parses YAML; returns `{}` on parse error (logged as warning).

#### d. `_git_has_local_changes(repo_path: str) -> bool`

Runs `subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, timeout=10, capture_output=True, text=True)`. Returns `True` if stdout is non-empty. Raises on repo-not-found (non-existent path or non-git directory).

#### e. `_WORKSPACE_CAPABILITIES` — add entry

```python
"redeploy_project": {
    "description": "Pull the latest code and rebuild/restart selected services",
    "confirmation_required": True,
},
```

#### f. `_WORKSPACE_SYSTEM_PROMPT` — extend ALLOWED_CAPABILITIES

```
- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
  The branch is always the project's configured default branch (do not include a branch param).
  Params: pull (bool, default true), components (array, values: "backend", "frontend").
  proposed_action format: {"capability": "redeploy_project", "description": "...",
    "params": {"pull": true, "components": ["backend", "frontend"]}}
```

Update the RESPONSE FORMAT comment to document the optional `params` key.

#### g. `workspace_chat()` — proposal-time validation for `redeploy_project`

After the existing capability allowlist check, when `capability == "redeploy_project"`:

1. Load config via `_load_workspace_projects_config()`. If `project_id` not in config or `redeploy` key absent → set `intent = "informational"`, include explanation in `reply`, return with no `proposed_action`.
2. Extract `params` from LLM response:
   - `components`: must be a non-empty subset of configured `redeploy` keys for the project. Reject unknown components with `intent = "informational"`.
   - `pull`: default `True`. Accept only bool.
   - Do **not** accept a `branch` param from the LLM — the branch is always resolved from config.
3. Run `_git_has_local_changes(project_block["repository_path"])` informatively → `has_dirty_warning: bool`. On error (path missing, not a repo), set `has_dirty_warning = None`.
4. Store in `_pending_workspace_actions[action_id]` under `_workspace_lock`:

   ```python
   {
     "project_id": project_id,        # resolved configured key
     "capability": "redeploy_project",
     "description": <LLM description>,
     "params": {"pull": bool, "components": [...]},  # validated
     "has_dirty_warning": bool | None,              # informational only
     "created_at": <iso timestamp>,
   }
   ```

   **Not stored**: `repo_path`, branch, service names, preview URL — all re-derived from config at execution time.

5. Add to `result["proposed_action"]`:

   ```json
   {
     "capability": "redeploy_project",
     "description": "...",
     "action_id": "...",
     "project_id": "timizer",
     "safe_identifier": "timizer",        // project_id or display_name — never the host path
     "configured_branch": "main",         // from config, display only
     "pull": true,
     "components": ["backend", "frontend"],
     "has_dirty_warning": false
   }
   ```

#### h. `workspace_action_confirm()` — background-job branch for `redeploy_project`

After retrieving and validating the action (existing checks: action exists, project matches, capability allowlisted), add a special path for `redeploy_project` **before** calling `_execute_workspace_capability`:

1. Extract `components` and `pull` from `action["params"]`.
2. Attempt `lock = _get_redeploy_lock(project_id); acquired = lock.acquire(blocking=False)`.
3. If `not acquired` → return `JSONResponse(status_code=409, content={"detail": "deployment already running for project"})` without removing action from pending.
4. Generate `deployment_id = str(uuid4())`.
5. Under `_deployment_jobs_lock`, initialize:

   ```python
   _deployment_jobs[deployment_id] = {
     "deployment_id": deployment_id,
     "project_id": project_id,
     "status": "RUNNING",
     "stage": None,
     "started_at": <iso>,
     "completed_at": None,
     "result_message": None,
     "deployed_sha": None,
     "preview_url": None,
     "error_stage": None,
     "error_excerpt": None,
   }
   ```

6. Remove action from `_pending_workspace_actions` under `_workspace_lock`.
7. Spawn: `threading.Thread(target=_run_redeploy_job, args=(deployment_id, project_id, components, pull, lock), daemon=True).start()`.
8. Return immediately: `{"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}`.

#### i. `_run_redeploy_job(deployment_id, project_id, components, pull, lock)` — new function

Runs in a daemon thread. Holds `lock` on entry; must release it unconditionally in `finally`.

**Top-level exception boundary**: the entire function body is wrapped in a `try / except Exception as exc` block with a `finally` that releases `lock`. Any uncaught exception writes `status="FAILED"`, `completed_at` (utc iso), `error_stage="INTERNAL_ERROR"`, `error_excerpt=str(exc)[:500]` to the job under `_deployment_jobs_lock`, and logs the full traceback server-side via `logger.exception`.

**Invariant**: when the thread exits (normally or via any exception), the job record must have `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` must be set.

All sensitive execution values resolved from config at the start of this function:

```python
config = _load_workspace_projects_config()
project_block = config.get("projects", {}).get(project_id)
```

If `project_block` is None (config changed since proposal) → update job to FAILED (`error_stage="CONFIG_MISSING"`, `completed_at` set), return.

Resolve:
- `repo_path = project_block["repository_path"]`
- `default_branch = project_block["default_branch"]`
- `allow_dirty = project_block.get("allow_dirty", False)`
- `service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}`
- `preview_url = project_block.get("preview_url")`

If `repo_path` does not exist on disk → FAILED, `error_stage="PATH_NOT_FOUND"`, `completed_at` set. Return.

Validate that each component in `components` exists in `service_map`; FAILED, `error_stage="INVALID_COMPONENT"`, `completed_at` set. Return.

**Branch check (before any Git/Docker command):**
1. Run `git branch --show-current` in `repo_path` (timeout=10).
2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
3. `subprocess.TimeoutExpired` → FAILED, `error_stage="BRANCH_CHECK_TIMEOUT"`, `error_excerpt="git branch --show-current timed out"`, `completed_at` set. Return.
4. Non-zero returncode → FAILED, `error_stage="BRANCH_CHECK"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.
5. If current branch ≠ `default_branch` → FAILED, `error_stage="BRANCH_MISMATCH"`, `error_excerpt=f"current branch '{current}' differs from configured branch '{default_branch}'"`, `completed_at` set. Return.

**Fresh dirty check (before any Git/Docker command):**
1. Call `_git_has_local_changes(repo_path)`.
2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
3. `subprocess.TimeoutExpired` → FAILED, `error_stage="DIRTY_CHECK_TIMEOUT"`, `completed_at` set. Return.
4. If True and `allow_dirty` is False → FAILED, `error_stage="DIRTY_CHECK"`, `error_excerpt="uncommitted changes detected"`, `completed_at` set. Return.

**Execution sequence:**

For each stage, update `_deployment_jobs[deployment_id]["stage"]` under `_deployment_jobs_lock` before running the command.

- If `pull` is True:
  - Update stage → `"PULLING"`.
  - `subprocess.run(["git", "pull", "--ff-only", "origin", default_branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`.
  - `subprocess.TimeoutExpired` → FAILED, `error_stage="PULLING"`, `error_excerpt="git pull timed out after 120 s"`, `completed_at` set. Return.
  - `FileNotFoundError` → FAILED, `error_stage="PULLING"`, `error_excerpt="git executable not found"`, `completed_at` set. Return.
  - Non-zero returncode → FAILED, `error_stage="PULLING"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.

- For each `component` in `components` (in order; first failure stops the loop):
  - `service = service_map[component]`.
  - Update stage → `f"BUILDING_{component}"`.
  - `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`.
  - `subprocess.TimeoutExpired` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker compose timed out after 300 s"`, `completed_at` set. Return.
  - `FileNotFoundError` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker executable not found"`, `completed_at` set. Return.
  - Non-zero returncode → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.

- Get deployed SHA: `subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10, ...)`. Failure here is non-fatal: use `deployed_sha = None`.

- Update job to SUCCEEDED: `deployed_sha`, `preview_url`, `result_message`, `completed_at`.

Log each stage to `logger.info("redeploy %s: stage=%s", project_id, stage)`.

`finally` block: `lock.release()`. Always executes on success, failure, timeout, and unexpected exception.

#### j. New Supervisor endpoint — `GET /workspace/projects/{project_id}/deployments/{deployment_id}`

Returns current job state for polling:

- 200: full `_deployment_jobs[deployment_id]` dict, when `_deployment_jobs[deployment_id]["project_id"] == project_id`.
- 404: `deployment_id` not found, or `project_id` mismatch.

---

### 3. `services/control_api/routes/workspace.py`

#### a. New polling proxy route

Add:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

This route must:
- use the existing project-resolution dependency to validate `project_id`;
- forward to the Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
- preserve the Supervisor HTTP status code and JSON response body verbatim;
- return 404 for an unknown deployment or project mismatch (pass through Supervisor 404).

#### b. Propagate all Supervisor error statuses (≥ 400)

Update the workspace proxy forwarding helper so that **any** Supervisor response with `status_code >= 400` is returned with the original HTTP status. This currently applies to:

- `409 Conflict` (concurrent deployment already running);
- `404 Not Found` (unknown deployment, unknown action);
- any other 4xx or 5xx from the Supervisor.

The forwarded response must carry the same `status_code` and the same JSON body as the Supervisor response. It must not be silently collapsed to HTTP 200 with a `detail` field.

---

### 4. `apps/dashboard/src/api/workspace.js`

Add:

```js
export const getDeploymentStatus = (projectId, deploymentId) =>
  api.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`);
```

The URL targets the Control API route added in §3a.

---

### 5. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

#### Extend `ActionConfirmCard`

When `message.proposedAction?.capability === 'redeploy_project'`, render additional rows below the description:

- **Project**: `message.proposedAction.safe_identifier`
- **Branch**: `message.proposedAction.configured_branch`
- **Pull**: Yes / No from `message.proposedAction.pull`
- **Components**: comma-joined `message.proposedAction.components`
- **Local changes**: warning badge when `message.proposedAction.has_dirty_warning === true`

Do **not** display any host path. Use `safe_identifier` only.

No changes to the Confirm button or the existing `confirmWorkspaceAction` API call.

#### Background deployment polling in `handleConfirmAction`

When the confirm response includes `deployment_id` (i.e. `res.data.deployment_id`):

1. Update message state to `{ confirmed: false, deploymentId: res.data.deployment_id, deploymentStage: 'RUNNING' }`.
2. Start a polling loop (`setTimeout` chain, interval ~2 s) calling `getDeploymentStatus(projectId, deploymentId)`.
3. On each poll: update `deploymentStage` in message state.
4. On `status === 'SUCCEEDED'`: set `confirmed: true`, `confirmResult` to success message including SHA and preview URL. Stop polling.
5. On `status === 'FAILED'`: set `confirmError` to `${data.error_stage}: ${data.error_excerpt}`. Stop polling.
6. On HTTP 4xx or 5xx from the polling request: stop polling, display error.
7. Cap polling at 15 minutes; if exceeded, display "Deployment timed out — check supervisor logs."

#### Render deployment progress in `ActionConfirmCard`

When `message.deploymentId` is set and `message.confirmed` is false and no `confirmError`:
- Show spinner with current stage label (e.g. "PULLING…", "BUILDING backend…").
- Stage labels displayed: PULLING, BUILDING_backend, BUILDING_frontend, VERIFYING, SUCCEEDED, FAILED.

---

### 6. `tests/supervisor/test_workspace_redeploy.py` (new file)

#### Config and helpers

- `test_load_config_missing` — missing file → `{}`.
- `test_load_config_valid` — valid YAML → parsed correctly.
- `test_git_has_local_changes_clean` — empty porcelain → False.
- `test_git_has_local_changes_dirty` — non-empty porcelain → True.
- `test_git_has_local_changes_not_a_repo` — nonexistent path → raises.

#### Proposal-time validation

- `test_chat_unknown_project_returns_informational` — project not in config → intent=informational, no proposed_action.
- `test_chat_unknown_component_rejected` — LLM requests component not in config → intent=informational.
- `test_chat_branch_param_ignored` — LLM provides branch → stripped, configured branch used instead.
- `test_chat_has_dirty_warning_propagated` — dirty repo → `has_dirty_warning=True` in proposed_action.

#### Confirmation and lock

- `test_confirm_starts_background_job` — confirm returns `{ok: true, deployment_id: ..., status: "RUNNING"}` immediately.
- `test_confirm_concurrent_returns_409` — lock held → HTTP 409.
- `test_confirm_unknown_action_id_returns_404` — forged action_id → 404.

#### Background job execution

- `test_job_branch_mismatch_rejected` — current branch ≠ configured → FAILED (status set, completed_at set), no git pull or compose called.
- `test_job_dirty_between_proposal_and_confirm` — repo clean at proposal, dirty at execution → FAILED (status set, completed_at set).
- `test_job_pull_failure_stops_early` — git pull fails → FAILED PULLING (status set, completed_at set), no compose called.
- `test_job_first_component_failure_stops_loop` — backend compose fails → FAILED (status set, completed_at set), frontend compose not called.
- `test_job_backend_only` — components=["backend"] → compose called once for backend service only.
- `test_job_frontend_only` — components=["frontend"] → compose called once for frontend service only.
- `test_job_success_returns_sha_and_url` — full success → status=SUCCEEDED, deployed_sha present, preview_url present, completed_at set.
- `test_job_lock_released_after_failure` — command failure → lock released (can acquire again immediately), status=FAILED, completed_at set.
- `test_job_lock_released_after_exception` — unexpected exception in thread → lock released, status=FAILED, completed_at set, error_stage="INTERNAL_ERROR".
- `test_job_git_timeout` — git pull exceeds timeout → FAILED PULLING, lock released, status=FAILED, completed_at set.
- `test_job_compose_timeout` — docker compose exceeds timeout → FAILED BUILDING, lock released, status=FAILED, completed_at set.
- `test_job_git_not_found` — git executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
- `test_job_docker_not_found` — docker executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
- `test_job_path_not_exist` — configured path missing → FAILED PATH_NOT_FOUND, no subprocess called, lock released, completed_at set.
- `test_job_config_reloaded_at_execution` — stale repo_path in pending action not used; fresh config applied.
- `test_job_stale_service_name_ignored` — tampered service name not executed; service from config used.
- `test_job_config_missing_at_execution` — project removed from config between proposal and execution → FAILED CONFIG_MISSING, lock released, completed_at set.
- `test_job_terminal_state_always_set` — simulate unexpected exception → status=FAILED, completed_at set, error_stage="INTERNAL_ERROR", lock released.

#### Supervisor status polling endpoint

- `test_get_deployment_status_running` — job in RUNNING state → 200 with stage.
- `test_get_deployment_status_succeeded` — completed job → 200 with sha, preview_url.
- `test_get_deployment_status_project_mismatch` — wrong project_id → 404.
- `test_get_deployment_status_unknown` — unknown deployment_id → 404.

---

### 7. `tests/control_api/test_workspace_redeploy_proxy.py` (new file)

#### Control API proxy correctness

- `test_proxy_polling_200` — Supervisor returns 200 with job state → Control API returns 200 with unchanged body.
- `test_proxy_supervisor_409_becomes_control_api_409` — Supervisor returns 409 → Control API returns 409 (not 200 with detail).
- `test_proxy_supervisor_404_becomes_control_api_404` — Supervisor returns 404 → Control API returns 404.
- `test_proxy_unknown_project_returns_404` — project_id fails the existing project-resolution dependency → 404 before forwarding.

---

### 8. Frontend tests (`apps/dashboard/src/components/ProjectWorkspacePanel.test.jsx` or similar)

- `test_confirm_card_renders_redeploy_fields` — renders safe_identifier, configured_branch, pull, components.
- `test_confirm_card_shows_dirty_warning` — `has_dirty_warning=true` → warning badge visible.
- `test_confirm_card_no_host_path_displayed` — no element contains the literal `repository_path` value.
- `test_confirm_submits_only_action_id` — Confirm click sends only `action_id` to `confirmWorkspaceAction`; no path/branch/service override.
- `test_polling_shows_stage` — mock polling returns BUILDING_backend → spinner text updated.
- `test_polling_stops_on_succeeded` — SUCCEEDED state → confirmed bubble shown, no further fetch.
- `test_polling_stops_on_failed` — FAILED state → error shown, no further fetch.
- `test_polling_stops_on_http_error` — polling returns 4xx → error displayed, no further fetch.

---

### 9. `services/supervisor/workspace_projects.example.yml` (new file)

An example/documentation config with the full schema annotated; never loaded by tests.

---

## Excluded

- SSE or WebSocket streaming of deployment progress (polling via new GET endpoint is sufficient).
- Rollback on failure.
- Production or cloud deployment.
- Multi-host orchestration.
- Arbitrary remote shell access or LLM-composed commands.
- Hot-reload of `workspace_projects.yml` without Supervisor restart.
- Allowing the LLM or frontend to select a branch other than the configured default branch.
- Deployment cancellation or timeout-triggered abort.
- Redeploying a project other than the active workspace project via the chat context.

## Acceptance criteria

- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe. Requesting an unconfigured project returns `intent=informational` with a refusal explanation and no `proposed_action`.
- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested Docker Compose services being rebuilt/restarted.
- No `git pull`, `git branch`, or `docker compose` command runs before the user clicks Confirm.
- The confirmation card displays: safe project identifier (not the host path), configured branch, pull flag, selected components, and a dirty-repo warning when applicable.
- At execution time, the background job re-reads `workspace_projects.yml` and derives `repo_path`, `default_branch`, service names, `allow_dirty`, and `preview_url` from config — values from the pending action or frontend are never used for command construction.
- The background job reads the current Git branch at execution time; if it differs from `default_branch`, the job fails with a branch-mismatch message before any Git or Docker command.
- The background job re-checks `git status --porcelain` at execution time; if dirty and `allow_dirty: false`, the job fails before any Git or Docker command.
- `workspace_action_confirm()` returns HTTP 409 when a deployment for the same project is already running; this 409 is preserved through the Control API proxy and reaches the dashboard as HTTP 409.
- The in-memory per-project lock is always released in a `finally` block, regardless of success, failure, timeout, or unexpected exception.
- `workspace_action_confirm()` returns within one second with `{ok: true, deployment_id: ..., status: "RUNNING"}`; the Supervisor remains responsive during deployment.
- When `_run_redeploy_job` exits (normally or via any exception), the deployment job record has `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` is always set. A job must never remain permanently in `"RUNNING"` after the thread exits.
- `subprocess.TimeoutExpired`, `FileNotFoundError`, missing/invalid configuration, missing repository path, non-Git repository, and unexpected exceptions each produce `status="FAILED"`, `completed_at` set, `error_stage` set to an appropriate label, and `error_excerpt` bounded to 500 characters.
- The frontend polls `GET /projects/{project_id}/workspace/deployments/{deployment_id}` on the Control API and updates the chat bubble with the current stage, deployed SHA and preview URL on success, or failed stage and log excerpt on failure.
- The Control API polling route validates `project_id` with the existing project-resolution dependency and forwards the Supervisor response status and body unchanged.
- Control API tests confirm: Supervisor 409 → Control API 409; Supervisor 404 → Control API 404; Supervisor 200 → Control API 200 with unchanged body.
- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
- On failure, the chat bubble shows the failed stage and the first 500 characters of the relevant stderr or error message.
- Frontend polling stops immediately when the response carries `status: "FAILED"`, `status: "SUCCEEDED"`, or an HTTP error; no further fetches are made after a terminal state.
- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
- All test cases in `test_workspace_redeploy.py` and `test_workspace_redeploy_proxy.py` pass.
- No frontend test can construct or submit an arbitrary `repo_path`, branch, service name, or shell command via the confirmation card.

---

## Reviews

### plan-review-01.md

# PLAN_FIX_REQUIRED

## Summary

The plan is well structured and keeps redeployment behind the AI Workspace confirmation flow, but it requires additional safety, execution, and test coverage before implementation.

## Required fixes

### 1. Re-check repository state at confirmation time

The dirty-working-tree check performed while proposing the action is only informational. The Supervisor must run `git status --porcelain` again after the user confirms and immediately before any Git or Docker command.

Do not rely on the stored `has_dirty` value as the final safety check.

### 2. Enforce a strict branch policy

The redeployment must not accept an arbitrary branch generated by the LLM.

For the initial implementation:

- Use the project `default_branch` from `workspace_projects.yml`.
- Read the current branch with `git branch --show-current` at execution time.
- Refuse redeployment when the current branch does not match the configured branch, unless a controlled checkout policy is explicitly designed.
- Run the pull only after this validation, using fast-forward-only semantics.
- Never merge a requested remote branch into an unrelated current local branch.

### 3. Do not block the Supervisor request for the full deployment duration

A Git pull and two Docker builds may take many minutes. The preferred architecture is to start a background deployment job and return a deployment identifier and running status immediately.

The plan must define:

- deployment job creation;
- running/succeeded/failed status;
- status retrieval from the workspace;
- storage of the final message, deployed revision, preview URL, and failed stage.

If synchronous execution is intentionally retained for this demo ticket, explicitly document the limitation and prove that other Supervisor requests remain serviceable during execution.

### 4. Improve redeployment locking and conflict response

- Document that the in-memory project lock is valid only for a single Supervisor process/worker.
- Ensure the lock is always released in `finally`, including unexpected exceptions and timeouts.
- Return HTTP `409 Conflict` when another deployment is already running for the project, not HTTP 500.
- Avoid using user-controlled values as lock keys; use the resolved configured project id.

### 5. Resolve all sensitive execution values from Supervisor configuration

At confirmation time, reload `workspace_projects.yml` and resolve from `project_id`:

- repository path;
- configured/default branch;
- allowed components;
- Docker Compose service names;
- dirty-repository policy;
- preview URL.

Do not trust or execute `repo_path`, service names, branch names, or commands received from the frontend, the LLM response, or stale pending-action metadata.

The pending action should contain only safe identifiers and approved business parameters.

### 6. Add missing backend and frontend tests

Backend tests must also cover:

- repository becomes dirty between proposal and confirmation;
- current branch differs from configured branch;
- unapproved branch is rejected;
- repository path does not exist;
- configured path is not a Git repository;
- Git timeout;
- Docker Compose timeout;
- lock release after command failure, timeout, and unexpected exception;
- failure of the first component prevents later components from starting;
- concurrent deployment returns HTTP 409;
- execution reloads configuration and ignores stale/tampered path or service values.

Frontend tests must cover:

- confirmation card renders project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
- the full sensitive host path is not displayed when a safe identifier is available;
- Confirm submits only the pending `action_id` through the existing API;
- no executable path, command, branch, or service override is submitted from editable client data.

## Preserved requirements

- No Git or Docker command runs before explicit user confirmation.
- Commands are constructed by trusted Supervisor code only.
- Components remain limited to configured backend/frontend recipes.
- Functional development still goes through GitHub issues and the AI Dev Factory pipeline.
- Existing workspace capabilities must continue working without regression.

## Decision

PLAN_FIX_REQUIRED

### plan-review-02.md

# PLAN_FIX_REQUIRED

## Review

Plan review 02 for T227.

## Summary

The regenerated plan resolves the first review's repository, branch, configuration, asynchronous execution, locking, and test-coverage requirements. Three integration and failure-state corrections remain required before implementation.

## Required fixes

### 1. Add the deployment-status proxy to the Control API

The dashboard calls:

```text
GET /api/projects/{project_id}/workspace/deployments/{deployment_id}
```

and the Supervisor exposes:

```text
GET /workspace/projects/{project_id}/deployments/{deployment_id}
```

The regenerated plan must modify `services/control_api/routes/workspace.py` to add:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

This route must validate the project through the existing dependency and forward the GET request to the Supervisor while preserving its response status and JSON body.

Without this proxy, frontend polling will return 404.

### 2. Preserve HTTP 409 responses through the Control API

The current Control API forwarding helper explicitly raises only for selected 4xx statuses and for 5xx responses. A Supervisor `409 Conflict` may therefore be returned by the Control API as HTTP 200 with a `detail` body.

The plan must update the workspace proxy so every Supervisor response with `status_code >= 400` is propagated with the original status, including:

- 409 when another deployment is already running;
- 404 for an unknown deployment;
- other validation or execution errors.

Add a test proving that a Supervisor 409 remains a Control API 409.

### 3. Guarantee a terminal job state on timeouts and exceptions

Releasing the per-project lock in `finally` is necessary but insufficient. If `_run_redeploy_job` raises, the daemon thread may terminate while the job remains permanently `RUNNING`.

The regenerated plan must define a top-level exception boundary around the complete background job and ensure all non-success paths write a terminal job state:

- `status = "FAILED"`;
- `completed_at` set;
- `error_stage` set to the active stage or a safe internal stage;
- `error_excerpt` set to a sanitized, bounded message;
- lock released in `finally`.

Handle at least:

- `subprocess.TimeoutExpired`;
- `FileNotFoundError`;
- missing or invalid configuration;
- missing repository path or non-Git repository;
- unexpected exceptions.

Add tests verifying both the released lock and the persisted `FAILED` state for timeout and unexpected-exception paths.

## Preserved requirements

The next plan must preserve all corrections already integrated from plan review 01:

- fresh dirty check after confirmation;
- configured-branch enforcement;
- no LLM/frontend-controlled executable branch, path, service, or command;
- background deployment job and polling;
- safe project identifier in the confirmation card;
- HTTP 409 for concurrent deployment;
- unconditional lock release;
- backend and frontend security/concurrency tests.

## Decision

PLAN_FIX_REQUIRED

---

## Fixes

### plan-fix-01.md

# Plan fix 01

## Ticket

T227 — Add pull and local backend/frontend redeployment action to AI Workspace

## Source review

`runs/T227/reviews/plan-review-01.md`

## Decision

PLAN_FIX_REQUIRED

## Required plan corrections

### 1. Re-check the repository state at execution time

The dirty-working-tree value collected while the action is proposed is informational only.

After confirmation and immediately before any Git or Docker command, the Supervisor must run `git status --porcelain` again and apply the configured dirty-repository policy to the fresh result.

The regenerated plan must not use a stored `has_dirty` value as the final safety decision.

### 2. Enforce the Supervisor-configured branch

The LLM and frontend must not select an arbitrary executable branch.

For this initial implementation:

- resolve the branch from the project's `default_branch` in `workspace_projects.yml`;
- read the current branch at execution time with `git branch --show-current`;
- refuse execution when the current branch differs from the configured branch;
- use fast-forward-only pull semantics only after the branch check succeeds;
- never merge a requested remote branch into a different current local branch.

The pending action may display the resolved branch but must not treat an LLM-provided or frontend-provided branch as authoritative.

### 3. Avoid blocking the Supervisor during a long deployment

Git pull and Docker builds can take several minutes. Regenerate the plan around a background deployment job that returns immediately with a deployment identifier and a running status.

Define:

- job creation;
- deployment identifier;
- running, succeeded, and failed states;
- status retrieval or polling from the Workspace;
- persisted or safely retained progress;
- final deployed revision;
- preview URL;
- failed stage and sanitized log excerpt.

If synchronous execution is intentionally kept for a limited demo, the plan must explicitly document the limitation and include a design/test proving that other Supervisor requests remain serviceable while deployment runs.

### 4. Strengthen locking and conflict handling

The regenerated plan must:

- use the resolved configured project id as the lock key;
- document that an in-memory lock protects only one Supervisor process/worker;
- release the lock in `finally` after success, command failure, timeout, cancellation, or unexpected exception;
- return HTTP `409 Conflict` when a deployment is already running for the project, not HTTP 500.

### 5. Resolve all sensitive execution values from current Supervisor configuration

At confirmation/execution time, reload `workspace_projects.yml` and resolve from the safe configured `project_id`:

- repository path;
- default/configured branch;
- allowed components;
- Docker Compose service names;
- dirty-repository policy;
- preview URL.

Do not trust or execute paths, branches, service names, commands, or endpoints originating from:

- the frontend;
- the LLM response;
- stale pending-action metadata.

The pending action must contain only safe identifiers and approved business parameters. The frontend confirmation card may display a safe repository identifier, not necessarily the full sensitive host path.

### 6. Complete backend and frontend test coverage

Add backend tests for:

- repository becoming dirty between proposal and confirmation;
- current branch differing from the configured branch;
- rejection of an unapproved branch;
- missing repository path;
- configured path that is not a Git repository;
- Git timeout;
- Docker Compose timeout;
- lock release after command failure, timeout, and unexpected exception;
- first-component failure preventing later components from starting;
- concurrent deployment returning HTTP 409;
- configuration being reloaded at execution;
- stale or tampered paths and service values being ignored.

Add frontend tests for:

- rendering project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
- not displaying the full host path when a safe identifier exists;
- Confirm submitting only the pending `action_id`;
- no executable path, command, branch, or service override being submitted from editable client data.

## Requirements that must remain preserved

- No Git or Docker command runs before explicit confirmation.
- Commands are constructed only by trusted Supervisor code.
- Components remain limited to configured backend/frontend recipes.
- The operation remains local; production/cloud deployment is out of scope.
- Existing Workspace capabilities and informational chat behavior remain unchanged.
- Functional development continues through GitHub issues and the AI Dev Factory pipeline.

## Expected output

Regenerate `runs/T227/plan.md` to incorporate every correction above. Do not implement application code during the plan-fix step.

### plan-fix-02.md

# Plan fix 02

## Ticket

T227 — Add pull and local backend/frontend redeployment action to AI Workspace

## Source review

`runs/T227/reviews/plan-review-02.md`

## Decision

PLAN_FIX_REQUIRED

## Required plan corrections

### 1. Add the Control API polling route

Modify `services/control_api/routes/workspace.py` to expose:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

The route must:

- use the existing project-resolution dependency;
- forward to Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
- preserve the Supervisor HTTP status and JSON response;
- return 404 for an unknown deployment or project mismatch.

Update `apps/dashboard/src/api/workspace.js` to call this Control API route consistently.

### 2. Propagate every Supervisor error status, including 409

Update the workspace proxy forwarding logic so any Supervisor response with `status_code >= 400` is returned or raised with the original HTTP status.

In particular, concurrent redeployment must remain:

```text
409 Conflict
```

from Supervisor through Control API to the dashboard. It must not become HTTP 200 with a `detail` field.

Add Control API tests for:

- Supervisor 409 → Control API 409;
- Supervisor 404 → Control API 404;
- successful polling response → Control API 200 with unchanged job state.

### 3. Persist FAILED for every background-job failure

Wrap the complete `_run_redeploy_job` body with a top-level exception boundary.

For every timeout, configuration failure, filesystem/Git error, missing executable, or unexpected exception, update the deployment job under `_deployment_jobs_lock` with:

```python
{
    "status": "FAILED",
    "completed_at": <utc timestamp>,
    "error_stage": <current or safe failure stage>,
    "error_excerpt": <sanitized message, maximum 500 characters>,
}
```

Requirements:

- never leave a terminated job in `RUNNING`;
- handle `subprocess.TimeoutExpired` explicitly;
- handle `FileNotFoundError` explicitly;
- handle invalid/missing project configuration;
- handle missing or non-Git repository paths;
- catch unexpected exceptions, log the full server-side exception, and expose only a sanitized bounded excerpt;
- release the project lock unconditionally in `finally`.

Add tests proving that:

- Git timeout produces `FAILED` and releases the lock;
- Docker timeout produces `FAILED` and releases the lock;
- unexpected exception produces `FAILED` and releases the lock;
- missing executable produces `FAILED`;
- frontend polling stops on each resulting `FAILED` response.

## Requirements to preserve

Do not regress the corrections already present in the current plan:

- execution-time configuration reload;
- configured branch only;
- execution-time branch and dirty checks;
- safe pending-action metadata;
- background job returning immediately;
- per-project conflict locking;
- no host paths in the UI;
- frontend submits only the opaque `action_id`;
- existing capability behavior remains unchanged.

## Expected output

Regenerate `runs/T227/plan.md` with these corrections. Do not implement source code as part of the plan-fix step.

---

## PR Diff (PR #314)

```diff
diff --git a/apps/dashboard/node_modules/.vite/vitest/results.json b/apps/dashboard/node_modules/.vite/vitest/results.json
index aa0e26f9..79a64e88 100644
--- a/apps/dashboard/node_modules/.vite/vitest/results.json
+++ b/apps/dashboard/node_modules/.vite/vitest/results.json
@@ -1 +1 @@
-{"version":"1.6.1","results":[[":tests/ProjectRulesPanel.test.jsx",{"duration":147,"failed":false}],[":tests/TicketDetailPage.test.jsx",{"duration":169,"failed":false}]]}
\ No newline at end of file
+{"version":"1.6.1","results":[[":tests/ticketWorkflowStatus.test.js",{"duration":5,"failed":false}],[":tests/api.test.js",{"duration":8,"failed":false}],[":tests/usePolling.test.js",{"duration":13,"failed":false}],[":tests/BatchDependencyGraph.test.jsx",{"duration":16,"failed":false}],[":tests/RuntimeStatusPanel.test.jsx",{"duration":77,"failed":false}],[":tests/DaemonActivityFeed.test.jsx",{"duration":34,"failed":true}],[":tests/ProjectSidebar.test.jsx",{"duration":97,"failed":false}],[":tests/ProjectWorkspacePanel.test.jsx",{"duration":399,"failed":false}],[":tests/TicketWorkflowTimeline.test.jsx",{"duration":80,"failed":false}],[":tests/ProjectRulesPanel.test.jsx",{"duration":145,"failed":false}],[":tests/TicketIntelligencePanel.test.jsx",{"duration":240,"failed":false}],[":tests/TicketOperationsPanel.test.jsx",{"duration":182,"failed":false}],[":tests/BatchesPage.test.jsx",{"duration":162,"failed":false}],[":tests/TicketDiagnosticsPanel.test.jsx",{"duration":130,"failed":false}],[":tests/BatchAnalysisSummaryPanel.test.jsx",{"duration":67,"failed":false}],[":tests/ProjectDashboardPage.test.jsx",{"duration":0,"failed":false}],[":tests/TicketList.test.jsx",{"duration":107,"failed":false}],[":tests/BatchDetailPage.test.jsx",{"duration":182,"failed":false}],[":tests/TicketRuleEvaluationPanel.test.jsx",{"duration":1605,"failed":false}],[":tests/DaemonPage.test.jsx",{"duration":166,"failed":false}],[":tests/T187TicketBoard.test.jsx",{"duration":192,"failed":false}],[":tests/ProjectRouting.test.jsx",{"duration":77,"failed":false}],[":tests/TicketDetail.test.jsx",{"duration":278,"failed":false}],[":tests/TicketDetailPage.test.jsx",{"duration":221,"failed":false}],[":tests/RuntimeDashboardPage.test.jsx",{"duration":4138,"failed":true}],[":tests/QuotaAlertBanner.test.jsx",{"duration":40,"failed":false}]]}
\ No newline at end of file
diff --git a/apps/dashboard/src/api/workspace.js b/apps/dashboard/src/api/workspace.js
index c88b4d52..4199d0b2 100644
--- a/apps/dashboard/src/api/workspace.js
+++ b/apps/dashboard/src/api/workspace.js
@@ -17,3 +17,6 @@ export const confirmWorkspaceIssue = (projectId, draftId) =>
   client.post(`/projects/${projectId}/workspace/issues/confirm`, {
     draft_id: draftId,
   })
+
+export const getDeploymentStatus = (projectId, deploymentId) =>
+  client.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`)
diff --git a/apps/dashboard/src/components/ProjectWorkspacePanel.jsx b/apps/dashboard/src/components/ProjectWorkspacePanel.jsx
index a4e5ee74..dcd0978d 100644
--- a/apps/dashboard/src/components/ProjectWorkspacePanel.jsx
+++ b/apps/dashboard/src/components/ProjectWorkspacePanel.jsx
@@ -1,8 +1,33 @@
 import { useState, useEffect, useRef } from 'react'
-import { postWorkspaceMessage, confirmWorkspaceAction, confirmWorkspaceIssue } from '../api/workspace'
+import { postWorkspaceMessage, confirmWorkspaceAction, confirmWorkspaceIssue, getDeploymentStatus } from '../api/workspace'
+
+const STAGE_LABELS = {
+  PULLING: 'Pulling…',
+  BUILDING_backend: 'Building backend…',
+  BUILDING_frontend: 'Building frontend…',
+  VERIFYING: 'Verifying…',
+  SUCCEEDED: 'Succeeded',
+  FAILED: 'Failed',
+}
 
 function ActionConfirmCard({ message, onConfirm, loading }) {
   if (!message.proposedAction) return null
+
+  const isRedeploy = message.proposedAction.capability === 'redeploy_project'
+
+  // Deployment in progress (background job running)
+  if (message.deploymentId && !message.confirmed && !message.confirmError) {
+    const stageLabel = STAGE_LABELS[message.deploymentStage] || `${message.deploymentStage}…`
+    return (
+      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
+        <p className="font-medium text-yellow-800 flex items-center gap-1">
+          <span className="inline-block w-3 h-3 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin" />
+          {stageLabel}
+        </p>
+      </div>
+    )
+  }
+
   if (message.confirmed) {
     return (
       <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
@@ -10,10 +35,39 @@ function ActionConfirmCard({ message, onConfirm, loading }) {
       </div>
     )
   }
+
   return (
     <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
       <p className="font-medium text-yellow-800">Proposed action:</p>
       <p className="text-yellow-700 mt-0.5">{message.proposedAction.description}</p>
+      {isRedeploy && (
+        <table className="mt-1 w-full text-yellow-700 text-xs border-collapse">
+          <tbody>
+            <tr>
+              <td className="pr-2 font-medium">Project</td>
+              <td>{message.proposedAction.safe_identifier}</td>
+            </tr>
+            <tr>
+              <td className="pr-2 font-medium">Branch</td>
+              <td>{message.proposedAction.configured_branch}</td>
+            </tr>
+            <tr>
+              <td className="pr-2 font-medium">Pull</td>
+              <td>{message.proposedAction.pull ? 'Yes' : 'No'}</td>
+            </tr>
+            <tr>
+              <td className="pr-2 font-medium">Components</td>
+              <td>{(message.proposedAction.components || []).join(', ')}</td>
+            </tr>
+            {message.proposedAction.has_dirty_warning === true && (
+              <tr>
+                <td className="pr-2 font-medium">Local changes</td>
+                <td className="text-orange-600 font-semibold">⚠ Uncommitted changes detected</td>
+              </tr>
+            )}
+          </tbody>
+        </table>
+      )}
       {message.confirmError && (
         <p className="text-red-600 mt-1">{message.confirmError}</p>
       )}
@@ -127,6 +181,73 @@ export default function ProjectWorkspacePanel({ projectId, isOpen, onClose }) {
     setLoading(true)
     try {
       const res = await confirmWorkspaceAction(projectId, actionId)
+      const deploymentId = res.data.deployment_id
+      if (deploymentId) {
+        setMessages(prev =>
+          prev.map(m =>
+            m.id === msg.id
+              ? { ...m, deploymentId, deploymentStage: 'RUNNING' }
+              : m
+          )
+        )
+        setLoading(false)
+
+        const deadline = Date.now() + 15 * 60 * 1000
+        const poll = async () => {
+          if (Date.now() > deadline) {
+            setMessages(prev =>
+              prev.map(m =>
+                m.id === msg.id
+                  ? { ...m, confirmError: 'Deployment timed out — check supervisor logs.' }
+                  : m
+              )
+            )
+            return
+          }
+          try {
+            const statusRes = await getDeploymentStatus(projectId, deploymentId)
+            const data = statusRes.data
+            setMessages(prev =>
+              prev.map(m =>
+                m.id === msg.id
+                  ? { ...m, deploymentStage: data.stage || data.status }
+                  : m
+              )
+            )
+            if (data.status === 'SUCCEEDED') {
+              const sha = data.deployed_sha ? ` (sha: ${data.deployed_sha})` : ''
+              const url = data.preview_url ? ` — ${data.preview_url}` : ''
+              setMessages(prev =>
+                prev.map(m =>
+                  m.id === msg.id
+                    ? { ...m, confirmed: true, confirmResult: `Deployed successfully${sha}${url}` }
+                    : m
+                )
+              )
+            } else if (data.status === 'FAILED') {
+              setMessages(prev =>
+                prev.map(m =>
+                  m.id === msg.id
+                    ? { ...m, confirmError: `${data.error_stage}: ${data.error_excerpt}` }
+                    : m
+                )
+              )
+            } else {
+              setTimeout(poll, 2000)
+            }
+          } catch (err) {
+            setMessages(prev =>
+              prev.map(m =>
+                m.id === msg.id
+                  ? { ...m, confirmError: err.response?.data?.detail || err.message }
+                  : m
+              )
+            )
+          }
+        }
+        setTimeout(poll, 2000)
+        return
+      }
       setMessages(prev =>
         prev.map(m =>
           m.id === msg.id
diff --git a/apps/dashboard/tests/ProjectWorkspacePanel.test.jsx b/apps/dashboard/tests/ProjectWorkspacePanel.test.jsx
new file mode 100644
index 00000000..92bc192e
--- /dev/null
+++ b/apps/dashboard/tests/ProjectWorkspacePanel.test.jsx
@@ -0,0 +1,223 @@
+import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
+import ProjectWorkspacePanel from '../src/components/ProjectWorkspacePanel'
+import * as workspaceApi from '../src/api/workspace'
+
+vi.mock('../src/api/workspace')
+
+beforeAll(() => {
+  window.HTMLElement.prototype.scrollIntoView = vi.fn()
+})
+
+const REPO_PATH = '/host/secret/path/to/repo'
+
+const _redeployAction = (overrides = {}) => ({
+  capability: 'redeploy_project',
+  description: 'Pull and redeploy backend and frontend',
+  action_id: 'action-abc',
+  project_id: 'my-project',
+  safe_identifier: 'My Project',
+  configured_branch: 'main',
+  pull: true,
+  components: ['backend', 'frontend'],
+  has_dirty_warning: false,
+  ...overrides,
+})
+
+function renderPanel(projectId = 'my-project') {
+  return render(<ProjectWorkspacePanel projectId={projectId} isOpen onClose={() => {}} />)
+}
+
+function _mockChat(proposed_action = null, intent = 'informational') {
+  workspaceApi.postWorkspaceMessage.mockResolvedValue({
+    data: {
+      reply: 'Sure, I will redeploy.',
+      intent: proposed_action ? 'actionable' : intent,
+      proposed_action,
+      issue_draft: null,
+      confirmation_required: !!proposed_action,
+    },
+  })
+}
+
+async function _submitMessage(text = 'redeploy this project') {
+  const input = screen.getByRole('textbox')
+  fireEvent.change(input, { target: { value: text } })
+  fireEvent.submit(input.closest('form'))
+}
+
+describe('ProjectWorkspacePanel — redeploy confirmation card', () => {
+  beforeEach(() => {
+    vi.clearAllMocks()
+  })
+
+  it('renders safe_identifier, configured_branch, pull, and components', async () => {
+    _mockChat(_redeployAction())
+    renderPanel()
+    await _submitMessage()
+
+    await screen.findByText(/My Project/)
+    expect(screen.getByText('main')).toBeInTheDocument()
+    expect(screen.getByText('Yes')).toBeInTheDocument()
+    expect(screen.getByText('backend, frontend')).toBeInTheDocument()
+  })
+
+  it('shows dirty warning badge when has_dirty_warning is true', async () => {
+    _mockChat(_redeployAction({ has_dirty_warning: true }))
+    renderPanel()
+    await _submitMessage()
+
+    await screen.findByText(/uncommitted changes/i)
+  })
+
+  it('does not display the host repository path', async () => {
+    _mockChat(_redeployAction({ safe_identifier: 'My Project' }))
+    renderPanel()
+    await _submitMessage()
+
+    await screen.findByText(/My Project/)
+    expect(screen.queryByText(REPO_PATH)).toBeNull()
+    expect(document.body.textContent).not.toContain(REPO_PATH)
+  })
+
+  it('confirm click sends only action_id to confirmWorkspaceAction', async () => {
+    _mockChat(_redeployAction())
+    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
+      data: { ok: true, result: 'Done.' },
+    })
+    renderPanel()
+    await _submitMessage()
+
+    const confirmBtn = await screen.findByText('Confirm')
+    fireEvent.click(confirmBtn)
+
+    await waitFor(() =>
+      expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalledWith(
+        'my-project',
+        'action-abc',
+      )
+    )
+    const callArgs = workspaceApi.confirmWorkspaceAction.mock.calls[0]
+    expect(callArgs.length).toBe(2)
+    expect(callArgs[1]).toBe('action-abc')
+  })
+})
+
+describe('ProjectWorkspacePanel — deployment polling', () => {
+  beforeEach(() => {
+    vi.clearAllMocks()
+    vi.useFakeTimers({ shouldAdvanceTime: true })
+  })
+
+  afterEach(() => {
+    vi.useRealTimers()
+  })
+
+  it('shows current stage spinner while deployment runs', async () => {
+    _mockChat(_redeployAction())
+    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
+      data: { ok: true, deployment_id: 'dep-1', status: 'RUNNING' },
+    })
+    workspaceApi.getDeploymentStatus.mockResolvedValue({
+      data: { status: 'RUNNING', stage: 'BUILDING_backend' },
+    })
+
+    renderPanel()
+    await act(async () => { await _submitMessage() })
+    const confirmBtn = await screen.findByText('Confirm')
+    await act(async () => { fireEvent.click(confirmBtn) })
+
+    await waitFor(() =>
+      expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled()
+    )
+    await act(async () => { vi.advanceTimersByTime(2500) })
+
+    await waitFor(() =>
+      expect(workspaceApi.getDeploymentStatus).toHaveBeenCalledWith('my-project', 'dep-1')
+    )
+    await screen.findByText(/Building backend/i)
+  })
+
+  it('shows success bubble and stops polling on SUCCEEDED', async () => {
+    _mockChat(_redeployAction())
+    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
+      data: { ok: true, deployment_id: 'dep-2', status: 'RUNNING' },
+    })
+    workspaceApi.getDeploymentStatus.mockResolvedValue({
+      data: {
+        status: 'SUCCEEDED',
+        stage: 'SUCCEEDED',
+        deployed_sha: 'abc1234',
+        preview_url: 'http://localhost:3000',
+      },
+    })
+
+    renderPanel()
+    await act(async () => { await _submitMessage() })
+    const confirmBtn = await screen.findByText('Confirm')
+    await act(async () => { fireEvent.click(confirmBtn) })
+
+    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
+    await act(async () => { vi.advanceTimersByTime(2500) })
+
+    await screen.findByText(/Deployed successfully/i)
+    await screen.findByText(/abc1234/)
+
+    const callCountAfterSuccess = workspaceApi.getDeploymentStatus.mock.calls.length
+    await act(async () => { vi.advanceTimersByTime(5000) })
+    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterSuccess)
+  })
+
+  it('shows error and stops polling on FAILED', async () => {
+    _mockChat(_redeployAction())
+    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
+      data: { ok: true, deployment_id: 'dep-3', status: 'RUNNING' },
+    })
+    workspaceApi.getDeploymentStatus.mockResolvedValue({
+      data: {
+        status: 'FAILED',
+        error_stage: 'PULLING',
+        error_excerpt: 'fatal: could not read remote',
+      },
+    })
+
+    renderPanel()
+    await act(async () => { await _submitMessage() })
+    const confirmBtn = await screen.findByText('Confirm')
+    await act(async () => { fireEvent.click(confirmBtn) })
+
+    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
+    await act(async () => { vi.advanceTimersByTime(2500) })
+
+    await screen.findByText(/PULLING/)
+    await screen.findByText(/could not read remote/)
+
+    const callCountAfterFailure = workspaceApi.getDeploymentStatus.mock.calls.length
+    await act(async () => { vi.advanceTimersByTime(5000) })
+    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterFailure)
+  })
+
+  it('shows error and stops polling on HTTP error from polling', async () => {
+    _mockChat(_redeployAction())
+    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
+      data: { ok: true, deployment_id: 'dep-4', status: 'RUNNING' },
+    })
+    workspaceApi.getDeploymentStatus.mockRejectedValue({
+      response: { data: { detail: 'Supervisor unreachable' } },
+      message: 'Network Error',
+    })
+
+    renderPanel()
+    await act(async () => { await _submitMessage() })
+    const confirmBtn = await screen.findByText('Confirm')
+    await act(async () => { fireEvent.click(confirmBtn) })
+
+    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
+    await act(async () => { vi.advanceTimersByTime(2500) })
+
+    await screen.findByText(/Supervisor unreachable/)
+
+    const callCountAfterError = workspaceApi.getDeploymentStatus.mock.calls.length
+    await act(async () => { vi.advanceTimersByTime(5000) })
+    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterError)
+  })
+})
diff --git a/runs/T227/daemon.lock b/runs/T227/daemon.lock
new file mode 100644
index 00000000..5a3ce662
--- /dev/null
+++ b/runs/T227/daemon.lock
@@ -0,0 +1 @@
+{"pid": 86751, "created_at": "2026-08-01T23:08:52Z"}
\ No newline at end of file
diff --git a/runs/T227/fixes/context-20260801T172417Z.md b/runs/T227/fixes/context-20260801T172417Z.md
new file mode 100644
index 00000000..74e37e19
--- /dev/null
+++ b/runs/T227/fixes/context-20260801T172417Z.md
@@ -0,0 +1,385 @@
+## Artifact-only instruction (mandatory)
+
+Your response will be written verbatim to `runs/T227/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+Openings such as "The plan has been rewritten…", "This plan now
+covers…", "Plan rewritten as…", "Key points covered…", "The
+document now…" make the output invalid.
+
+---
+
+## Output précédent
+
+Now I have everything I need. Let me write the plan.
+
+## Objective
+
+Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by a `docker compose up --build` for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow.
+
+## Included
+
+### 1. New config file — `supervisor/workspace_projects.yml`
+
+Schema per project:
+```yaml
+projects:
+  <project_id>:
+    repository_path: /host/path/to/repo
+    default_branch: main
+    allow_dirty: false         # reject if local uncommitted changes exist
+    redeploy:
+      backend:
+        service: backend       # docker compose service name
+      frontend:
+        service: frontend
+    preview_url: http://localhost:3000   # optional, returned on success
+```
+
+Loaded once at capability execution time via `_load_workspace_projects_config()`. No hot-reload required.
+
+---
+
+### 2. `supervisor/main.py`
+
+**a. New constants / state:**
+- `_WORKSPACE_REDEPLOY_LOCKS: dict[str, threading.Lock]` — per-project lock, created lazily via `_get_redeploy_lock(project_id)`.
+
+**b. New helper functions:**
+- `_load_workspace_projects_config() -> dict` — reads `supervisor/workspace_projects.yml` (path resolvable via env var `WORKSPACE_PROJECTS_CONFIG`); returns `{}` on missing file.
+- `_git_has_local_changes(repo_path: str) -> bool` — runs `git status --porcelain` (subprocess, timeout=10); returns True if output is non-empty.
+- `_resolve_redeploy_project(project_id, config) -> dict | None` — looks up the project in the loaded config, returns the project block or None if not found.
+
+**c. `_WORKSPACE_CAPABILITIES`:** add entry:
+```python
+"redeploy_project": {
+    "description": "Pull the latest code and rebuild/restart selected services",
+    "confirmation_required": True,
+},
+```
+
+**d. `_WORKSPACE_SYSTEM_PROMPT`:** extend ALLOWED_CAPABILITIES block:
+```
+- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
+  Params: pull (bool, default true), branch (string, default configured branch),
+  components (array, allowed values: "backend", "frontend").
+  proposed_action format: {"capability": "redeploy_project", "description": "...",
+    "params": {"pull": true, "branch": "main", "components": ["backend", "frontend"]}}
+```
+
+Also update the RESPONSE FORMAT comment to document the optional `params` key.
+
+**e. `workspace_chat()` endpoint — after capability allowlist check, for `redeploy_project`:**
+1. Load project config; reject with `intent=informational` + explanation if project not in config or config missing redeploy recipes.
+2. Extract and validate `params`:
+   - `components`: must be a non-empty subset of configured services for that project; reject unknowns.
+   - `pull`: default `True`.
+   - `branch`: default `project_block["default_branch"]`.
+3. Check local changes: run `_git_has_local_changes(repo_path)` and store result as `has_dirty` in pending action metadata.
+4. Store full metadata in `_pending_workspace_actions[action_id]`:
+   ```python
+   {
+     "project_id": project_id,
+     "capability": "redeploy_project",
+     "description": ...,
+     "params": {"pull": True, "branch": "main", "components": ["backend", "frontend"]},
+     "repo_path": "/host/path/to/repo",
+     "has_dirty": False,
+     "created_at": ...,
+   }
+   ```
+5. Add `repo_path`, `has_dirty`, `params` to `result["proposed_action"]` so the frontend can render the rich confirmation card.
+
+**f. `workspace_action_confirm()` endpoint:**
+- Pass `action["params"]`, `action["repo_path"]`, `action["has_dirty"]` to `_execute_workspace_capability`.
+
+**g. `_execute_workspace_capability(project_id, capability, params=None, repo_path=None, has_dirty=None)`:**
+Add `elif capability == "redeploy_project":` branch:
+1. Re-load config; re-validate project and components (defense-in-depth).
+2. Reject if `has_dirty` is True and `allow_dirty` is False for the project.
+3. Acquire `_get_redeploy_lock(project_id).acquire(blocking=False)`; return `(False, "deployment already running for this project")` if already locked.
+4. Inside try/finally (release lock in finally):
+   - If `params["pull"]` is True: run `subprocess.run(["git", "pull", "--ff-only", "origin", branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`. On non-zero returncode return `(False, f"PULLING failed: {stderr[:500]}")`.
+   - For each component in `params["components"]`, in order: run `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`. On non-zero returncode return `(False, f"BUILDING {component} failed: {stderr[:500]}")`.
+   - After all components succeed: get deployed revision with `git rev-parse --short HEAD`.
+   - Return `(True, f"Deployed revision {sha}. Services restarted: {components}. {preview_url or ''}")`.
+5. Log each stage to `logger.info(...)` with project_id and action_id.
+
+---
+
+### 3. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`
+
+**Extend `ActionConfirmCard`** — when `message.proposedAction.capability === 'redeploy_project'`, render additional details below the description:
+- Project: `message.proposedAction.project_id` (the workspace project_id)
+- Repository: `message.proposedAction.repo_path` (or a safe short identifier)
+- Branch: `message.proposedAction.params.branch`
+- Pull: yes/no from `message.proposedAction.params.pull`
+- Components: comma-joined list from `message.proposedAction.params.components`
+- Local changes: warning badge if `message.proposedAction.has_dirty === true`
+
+No changes to the confirm button or API call — they use the existing `confirmWorkspaceAction` path.
+
+---
+
+### 4. `tests/supervisor/test_workspace_redeploy.py` (new test file)
+
+- `test_load_workspace_projects_config_missing` — missing file returns `{}`.
+- `test_load_workspace_projects_config_valid` — valid YAML parsed correctly.
+- `test_git_has_local_changes_clean` — empty git status → False.
+- `test_git_has_local_changes_dirty` — non-empty git status → True.
+- `test_redeploy_unknown_project_rejected` — project not in config → capability not proposed.
+- `test_redeploy_unknown_component_rejected` — component not in project config → rejected.
+- `test_redeploy_dirty_rejected_when_not_allowed` — dirty repo + allow_dirty=false → `(False, ...)`.
+- `test_redeploy_concurrent_rejected` — lock held → `(False, "deployment already running ...")`.
+- `test_redeploy_pull_failure_stops_early` — git pull fails → returns failure, no compose called.
+- `test_redeploy_backend_only` — only backend component → compose called once for backend service.
+- `test_redeploy_success_returns_sha_and_url` — full success path → result contains sha and preview_url.
+
+---
+
+## Excluded
+
+- True SSE/WebSocket streaming of deployment progress (synchronous execution with stage summaries in result is sufficient for this ticket).
+- Rollback on failure.
+- Production or cloud deployment.
+- Multi-host orchestration.
+- Arbitrary remote shell access or LLM-generated commands.
+- Allowing redeployment of a project other than the active workspace project.
+- Hot-reload of `workspace_projects.yml` without supervisor restart.
+
+## Acceptance criteria
+
+- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe; requesting an unconfigured project returns a refusal explanation.
+- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested services being rebuilt.
+- No `git pull` or `docker compose` command runs before the user clicks Confirm in the chat.
+- The confirmation card displays: project id, repository path (or identifier), branch, whether pull is enabled, selected components, and a dirty-repo warning when applicable.
+- When `allow_dirty: false` and the repository has uncommitted changes, the confirm endpoint returns a failure with an explanation; no compose command is executed.
+- A second "Confirm" for the same project while the first is running returns HTTP 500 with "deployment already running."
+- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
+- On failure, the chat bubble shows the failed stage (PULLING or BUILDING \<component\>) and the first 500 characters of the relevant stderr.
+- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
+- All new test cases in `test_workspace_redeploy.py` pass.
+
+---
+
+## Review
+
+# PLAN_FIX_REQUIRED
+
+## Summary
+
+The plan is well structured and keeps redeployment behind the AI Workspace confirmation flow, but it requires additional safety, execution, and test coverage before implementation.
+
+## Required fixes
+
+### 1. Re-check repository state at confirmation time
+
+The dirty-working-tree check performed while proposing the action is only informational. The Supervisor must run `git status --porcelain` again after the user confirms and immediately before any Git or Docker command.
+
+Do not rely on the stored `has_dirty` value as the final safety check.
+
+### 2. Enforce a strict branch policy
+
+The redeployment must not accept an arbitrary branch generated by the LLM.
+
+For the initial implementation:
+
+- Use the project `default_branch` from `workspace_projects.yml`.
+- Read the current branch with `git branch --show-current` at execution time.
+- Refuse redeployment when the current branch does not match the configured branch, unless a controlled checkout policy is explicitly designed.
+- Run the pull only after this validation, using fast-forward-only semantics.
+- Never merge a requested remote branch into an unrelated current local branch.
+
+### 3. Do not block the Supervisor request for the full deployment duration
+
+A Git pull and two Docker builds may take many minutes. The preferred architecture is to start a background deployment job and return a deployment identifier and running status immediately.
+
+The plan must define:
+
+- deployment job creation;
+- running/succeeded/failed status;
+- status retrieval from the workspace;
+- storage of the final message, deployed revision, preview URL, and failed stage.
+
+If synchronous execution is intentionally retained for this demo ticket, explicitly document the limitation and prove that other Supervisor requests remain serviceable during execution.
+
+### 4. Improve redeployment locking and conflict response
+
+- Document that the in-memory project lock is valid only for a single Supervisor process/worker.
+- Ensure the lock is always released in `finally`, including unexpected exceptions and timeouts.
+- Return HTTP `409 Conflict` when another deployment is already running for the project, not HTTP 500.
+- Avoid using user-controlled values as lock keys; use the resolved configured project id.
+
+### 5. Resolve all sensitive execution values from Supervisor configuration
+
+At confirmation time, reload `workspace_projects.yml` and resolve from `project_id`:
+
+- repository path;
+- configured/default branch;
+- allowed components;
+- Docker Compose service names;
+- dirty-repository policy;
+- preview URL.
+
+Do not trust or execute `repo_path`, service names, branch names, or commands received from the frontend, the LLM response, or stale pending-action metadata.
+
+The pending action should contain only safe identifiers and approved business parameters.
+
+### 6. Add missing backend and frontend tests
+
+Backend tests must also cover:
+
+- repository becomes dirty between proposal and confirmation;
+- current branch differs from configured branch;
+- unapproved branch is rejected;
+- repository path does not exist;
+- configured path is not a Git repository;
+- Git timeout;
+- Docker Compose timeout;
+- lock release after command failure, timeout, and unexpected exception;
+- failure of the first component prevents later components from starting;
+- concurrent deployment returns HTTP 409;
+- execution reloads configuration and ignores stale/tampered path or service values.
+
+Frontend tests must cover:
+
+- confirmation card renders project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
+- the full sensitive host path is not displayed when a safe identifier is available;
+- Confirm submits only the pending `action_id` through the existing API;
+- no executable path, command, branch, or service override is submitted from editable client data.
+
+## Preserved requirements
+
+- No Git or Docker command runs before explicit user confirmation.
+- Commands are constructed by trusted Supervisor code only.
+- Components remain limited to configured backend/frontend recipes.
+- Functional development still goes through GitHub issues and the AI Dev Factory pipeline.
+- Existing workspace capabilities must continue working without regression.
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+---
+
+## Instructions de fix
+
+# Plan fix 01
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-01.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Re-check the repository state at execution time
+
+The dirty-working-tree value collected while the action is proposed is informational only.
+
+After confirmation and immediately before any Git or Docker command, the Supervisor must run `git status --porcelain` again and apply the configured dirty-repository policy to the fresh result.
+
+The regenerated plan must not use a stored `has_dirty` value as the final safety decision.
+
+### 2. Enforce the Supervisor-configured branch
+
+The LLM and frontend must not select an arbitrary executable branch.
+
+For this initial implementation:
+
+- resolve the branch from the project's `default_branch` in `workspace_projects.yml`;
+- read the current branch at execution time with `git branch --show-current`;
+- refuse execution when the current branch differs from the configured branch;
+- use fast-forward-only pull semantics only after the branch check succeeds;
+- never merge a requested remote branch into a different current local branch.
+
+The pending action may display the resolved branch but must not treat an LLM-provided or frontend-provided branch as authoritative.
+
+### 3. Avoid blocking the Supervisor during a long deployment
+
+Git pull and Docker builds can take several minutes. Regenerate the plan around a background deployment job that returns immediately with a deployment identifier and a running status.
+
+Define:
+
+- job creation;
+- deployment identifier;
+- running, succeeded, and failed states;
+- status retrieval or polling from the Workspace;
+- persisted or safely retained progress;
+- final deployed revision;
+- preview URL;
+- failed stage and sanitized log excerpt.
+
+If synchronous execution is intentionally kept for a limited demo, the plan must explicitly document the limitation and include a design/test proving that other Supervisor requests remain serviceable while deployment runs.
+
+### 4. Strengthen locking and conflict handling
+
+The regenerated plan must:
+
+- use the resolved configured project id as the lock key;
+- document that an in-memory lock protects only one Supervisor process/worker;
+- release the lock in `finally` after success, command failure, timeout, cancellation, or unexpected exception;
+- return HTTP `409 Conflict` when a deployment is already running for the project, not HTTP 500.
+
+### 5. Resolve all sensitive execution values from current Supervisor configuration
+
+At confirmation/execution time, reload `workspace_projects.yml` and resolve from the safe configured `project_id`:
+
+- repository path;
+- default/configured branch;
+- allowed components;
+- Docker Compose service names;
+- dirty-repository policy;
+- preview URL.
+
+Do not trust or execute paths, branches, service names, commands, or endpoints originating from:
+
+- the frontend;
+- the LLM response;
+- stale pending-action metadata.
+
+The pending action must contain only safe identifiers and approved business parameters. The frontend confirmation card may display a safe repository identifier, not necessarily the full sensitive host path.
+
+### 6. Complete backend and frontend test coverage
+
+Add backend tests for:
+
+- repository becoming dirty between proposal and confirmation;
+- current branch differing from the configured branch;
+- rejection of an unapproved branch;
+- missing repository path;
+- configured path that is not a Git repository;
+- Git timeout;
+- Docker Compose timeout;
+- lock release after command failure, timeout, and unexpected exception;
+- first-component failure preventing later components from starting;
+- concurrent deployment returning HTTP 409;
+- configuration being reloaded at execution;
+- stale or tampered paths and service values being ignored.
+
+Add frontend tests for:
+
+- rendering project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
+- not displaying the full host path when a safe identifier exists;
+- Confirm submitting only the pending `action_id`;
+- no executable path, command, branch, or service override being submitted from editable client data.
+
+## Requirements that must remain preserved
+
+- No Git or Docker command runs before explicit confirmation.
+- Commands are constructed only by trusted Supervisor code.
+- Components remain limited to configured backend/frontend recipes.
+- The operation remains local; production/cloud deployment is out of scope.
+- Existing Workspace capabilities and informational chat behavior remain unchanged.
+- Functional development continues through GitHub issues and the AI Dev Factory pipeline.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` to incorporate every correction above. Do not implement application code during the plan-fix step.
\ No newline at end of file
diff --git a/runs/T227/fixes/context-20260801T173829Z.md b/runs/T227/fixes/context-20260801T173829Z.md
new file mode 100644
index 00000000..ede6432f
--- /dev/null
+++ b/runs/T227/fixes/context-20260801T173829Z.md
@@ -0,0 +1,559 @@
+## Artifact-only instruction (mandatory)
+
+Your response will be written verbatim to `runs/T227/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+Openings such as "The plan has been rewritten…", "This plan now
+covers…", "Plan rewritten as…", "Key points covered…", "The
+document now…" make the output invalid.
+
+---
+
+## Output précédent
+
+## Objective
+
+Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by Docker Compose service rebuilds for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow, with the deployment running in a background job so the Supervisor remains responsive.
+
+## Included
+
+### 1. New config file — `services/supervisor/workspace_projects.yml`
+
+Schema per project (loaded at execution time via env var `WORKSPACE_PROJECTS_CONFIG`):
+
+```yaml
+projects:
+  <project_id>:
+    display_name: "Human-readable name"     # optional, shown in confirmation card
+    repository_path: /host/path/to/repo
+    default_branch: main
+    allow_dirty: false         # false → reject if local uncommitted changes exist
+    redeploy:
+      backend:
+        service: backend       # docker compose service name
+      frontend:
+        service: frontend
+    preview_url: http://localhost:3000       # optional, returned on success
+```
+
+`_load_workspace_projects_config() -> dict` reads this file; returns `{}` on missing file. Called at each proposal and execution — never cached between requests.
+
+---
+
+### 2. `services/supervisor/main.py`
+
+#### a. New module-level state
+
+```python
+# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
+_workspace_redeploy_locks: dict[str, threading.Lock] = {}
+_workspace_redeploy_locks_mutex = threading.Lock()
+
+# Background deployment job registry
+_deployment_jobs: dict[str, dict] = {}        # keyed by deployment_id (UUID)
+_deployment_jobs_lock = threading.Lock()
+```
+
+#### b. `_get_redeploy_lock(project_id: str) -> threading.Lock`
+
+Follows the existing `_get_analysis_lock` pattern (lazy creation, `_workspace_redeploy_locks_mutex` guards the dict).
+
+#### c. `_load_workspace_projects_config() -> dict`
+
+Reads `WORKSPACE_PROJECTS_CONFIG` env var (default: path relative to supervisor package). Returns `{}` on `FileNotFoundError`. Parses YAML; returns `{}` on parse error (logged as warning).
+
+#### d. `_git_has_local_changes(repo_path: str) -> bool`
+
+Runs `subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, timeout=10, capture_output=True, text=True)`. Returns `True` if stdout is non-empty. Raises on repo-not-found (non-existent path or non-git directory).
+
+#### e. `_WORKSPACE_CAPABILITIES` — add entry
+
+```python
+"redeploy_project": {
+    "description": "Pull the latest code and rebuild/restart selected services",
+    "confirmation_required": True,
+},
+```
+
+#### f. `_WORKSPACE_SYSTEM_PROMPT` — extend ALLOWED_CAPABILITIES
+
+```
+- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
+  The branch is always the project's configured default branch (do not include a branch param).
+  Params: pull (bool, default true), components (array, values: "backend", "frontend").
+  proposed_action format: {"capability": "redeploy_project", "description": "...",
+    "params": {"pull": true, "components": ["backend", "frontend"]}}
+```
+
+Update the RESPONSE FORMAT comment to document the optional `params` key.
+
+#### g. `workspace_chat()` — proposal-time validation for `redeploy_project`
+
+After the existing capability allowlist check, when `capability == "redeploy_project"`:
+
+1. Load config via `_load_workspace_projects_config()`. If `project_id` not in config or `redeploy` key absent → set `intent = "informational"`, include explanation in `reply`, return with no `proposed_action`.
+2. Extract `params` from LLM response:
+   - `components`: must be a non-empty subset of configured `redeploy` keys for the project. Reject unknown components with `intent = "informational"`.
+   - `pull`: default `True`. Accept only bool.
+   - Do **not** accept a `branch` param from the LLM — the branch is always resolved from config.
+3. Run `_git_has_local_changes(project_block["repository_path"])` informatively → `has_dirty_warning: bool`. On error (path missing, not a repo), set `has_dirty_warning = None`.
+4. Store in `_pending_workspace_actions[action_id]` under `_workspace_lock`:
+
+   ```python
+   {
+     "project_id": project_id,        # resolved configured key
+     "capability": "redeploy_project",
+     "description": <LLM description>,
+     "params": {"pull": bool, "components": [...]},  # validated
+     "has_dirty_warning": bool | None,              # informational only
+     "created_at": <iso timestamp>,
+   }
+   ```
+
+   **Not stored**: `repo_path`, branch, service names, preview URL — all re-derived from config at execution time.
+
+5. Add to `result["proposed_action"]`:
+
+   ```json
+   {
+     "capability": "redeploy_project",
+     "description": "...",
+     "action_id": "...",
+     "project_id": "timizer",
+     "safe_identifier": "timizer",        // project_id or display_name — never the host path
+     "configured_branch": "main",         // from config, display only
+     "pull": true,
+     "components": ["backend", "frontend"],
+     "has_dirty_warning": false
+   }
+   ```
+
+#### h. `workspace_action_confirm()` — background-job branch for `redeploy_project`
+
+After retrieving and validating the action (existing checks: action exists, project matches, capability allowlisted), add a special path for `redeploy_project` **before** calling `_execute_workspace_capability`:
+
+1. Extract `components` and `pull` from `action["params"]`.
+2. Attempt `lock = _get_redeploy_lock(project_id); acquired = lock.acquire(blocking=False)`.
+3. If `not acquired` → return `JSONResponse(status_code=409, content={"detail": "deployment already running for project"})` without removing action from pending.
+4. Generate `deployment_id = str(uuid4())`.
+5. Under `_deployment_jobs_lock`, initialize:
+
+   ```python
+   _deployment_jobs[deployment_id] = {
+     "deployment_id": deployment_id,
+     "project_id": project_id,
+     "status": "RUNNING",
+     "stage": None,
+     "started_at": <iso>,
+     "completed_at": None,
+     "result_message": None,
+     "deployed_sha": None,
+     "preview_url": None,
+     "error_stage": None,
+     "error_excerpt": None,
+   }
+   ```
+
+6. Remove action from `_pending_workspace_actions` under `_workspace_lock`.
+7. Spawn: `threading.Thread(target=_run_redeploy_job, args=(deployment_id, project_id, components, pull, lock), daemon=True).start()`.
+8. Return immediately: `{"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}`.
+
+#### i. `_run_redeploy_job(deployment_id, project_id, components, pull, lock)` — new function
+
+Runs in a daemon thread. Holds `lock` on entry; must release it in `finally` unconditionally.
+
+All sensitive execution values resolved from config at the start of this function:
+
+```python
+config = _load_workspace_projects_config()
+project_block = config.get("projects", {}).get(project_id)
+```
+
+If `project_block` is None (config changed since proposal) → update job to FAILED, return.
+
+Resolve:
+- `repo_path = project_block["repository_path"]`
+- `default_branch = project_block["default_branch"]`
+- `allow_dirty = project_block.get("allow_dirty", False)`
+- `service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}`
+- `preview_url = project_block.get("preview_url")`
+
+Validate that each component in `components` exists in `service_map`; FAILED otherwise.
+
+**Branch check (before any Git/Docker command):**
+1. Run `git branch --show-current` in `repo_path` (timeout=10). FAILED if command errors.
+2. If current branch ≠ `default_branch` → update job to FAILED stage="BRANCH_MISMATCH", error_excerpt=f"current branch '{current}' differs from configured branch '{default_branch}'". Return.
+
+**Fresh dirty check (before any Git/Docker command):**
+1. Run `_git_has_local_changes(repo_path)`. If True and `allow_dirty` is False → FAILED stage="DIRTY_CHECK", error_excerpt="uncommitted changes detected".
+
+**Execution sequence (inside `try`, lock released in `finally`):**
+
+For each stage, update `_deployment_jobs[deployment_id]["stage"]` under `_deployment_jobs_lock` before running the command.
+
+- If `pull` is True:
+  - Update stage → `"PULLING"`.
+  - `subprocess.run(["git", "pull", "--ff-only", "origin", default_branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`.
+  - Non-zero returncode → FAILED, `error_stage="PULLING"`, `error_excerpt=stderr[:500]`. Return.
+
+- For each `component` in `components` (in order; first failure stops the loop):
+  - `service = service_map[component]`.
+  - Update stage → `f"BUILDING_{component}"`.
+  - `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`.
+  - Non-zero returncode → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt=stderr[:500]`. Return.
+
+- Get deployed SHA: `subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10, capture_output=True, text=True)`.
+
+- Update job to SUCCEEDED: `deployed_sha`, `preview_url`, `result_message`, `completed_at`.
+
+Log each stage to `logger.info("redeploy %s: stage=%s", project_id, stage)`.
+
+`finally` block: `lock.release()`. Always executes on success, failure, timeout, and unexpected exception.
+
+#### j. New endpoint — `GET /workspace/projects/{project_id}/deployments/{deployment_id}`
+
+Returns current job state for polling:
+
+- 200: full `_deployment_jobs[deployment_id]` dict.
+- 404: deployment_id not found, or `project_id` mismatch.
+
+---
+
+### 3. `apps/dashboard/src/api/workspace.js`
+
+Add:
+
+```js
+export const getDeploymentStatus = (projectId, deploymentId) =>
+  api.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`);
+```
+
+---
+
+### 4. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`
+
+#### Extend `ActionConfirmCard`
+
+When `message.proposedAction?.capability === 'redeploy_project'`, render additional rows below the description:
+
+- **Project**: `message.proposedAction.safe_identifier`
+- **Branch**: `message.proposedAction.configured_branch`
+- **Pull**: Yes / No from `message.proposedAction.pull`
+- **Components**: comma-joined `message.proposedAction.components`
+- **Local changes**: warning badge when `message.proposedAction.has_dirty_warning === true`
+
+Do **not** display any host path. Use `safe_identifier` only.
+
+No changes to the Confirm button or the existing `confirmWorkspaceAction` API call.
+
+#### Background deployment polling in `handleConfirmAction`
+
+When the confirm response includes `deployment_id` (i.e. `res.data.deployment_id`):
+
+1. Update message state to `{ confirmed: false, deploymentId: res.data.deployment_id, deploymentStage: 'RUNNING' }`.
+2. Start a polling loop (`setTimeout` chain, interval ~2 s) calling `getDeploymentStatus(projectId, deploymentId)`.
+3. On each poll: update `deploymentStage` in message state.
+4. On `status === 'SUCCEEDED'`: set `confirmed: true`, `confirmResult` to success message including SHA and preview URL. Stop polling.
+5. On `status === 'FAILED'`: set `confirmError` to `${data.error_stage}: ${data.error_excerpt}`. Stop polling.
+6. Cap polling at 15 minutes; if exceeded, display "Deployment timed out — check supervisor logs."
+
+#### Render deployment progress in `ActionConfirmCard`
+
+When `message.deploymentId` is set and `message.confirmed` is false and no `confirmError`:
+- Show spinner with current stage label (e.g. "PULLING…", "BUILDING backend…").
+- Stage labels displayed: PULLING, BUILDING_backend, BUILDING_frontend, VERIFYING, SUCCEEDED, FAILED.
+
+---
+
+### 5. `tests/supervisor/test_workspace_redeploy.py` (new file)
+
+#### Config and helpers
+
+- `test_load_config_missing` — missing file → `{}`.
+- `test_load_config_valid` — valid YAML → parsed correctly.
+- `test_git_has_local_changes_clean` — empty porcelain → False.
+- `test_git_has_local_changes_dirty` — non-empty porcelain → True.
+- `test_git_has_local_changes_not_a_repo` — nonexistent path → raises.
+
+#### Proposal-time validation
+
+- `test_chat_unknown_project_returns_informational` — project not in config → intent=informational, no proposed_action.
+- `test_chat_unknown_component_rejected` — LLM requests component not in config → intent=informational.
+- `test_chat_branch_param_ignored` — LLM provides branch → stripped, configured branch used instead.
+- `test_chat_has_dirty_warning_propagated` — dirty repo → `has_dirty_warning=True` in proposed_action.
+
+#### Confirmation and lock
+
+- `test_confirm_starts_background_job` — confirm returns `{ok: true, deployment_id: ..., status: "RUNNING"}` immediately.
+- `test_confirm_concurrent_returns_409` — lock held → HTTP 409.
+- `test_confirm_unknown_action_id_returns_404` — forged action_id → 404.
+
+#### Background job execution
+
+- `test_job_branch_mismatch_rejected` — current branch ≠ configured → FAILED, no git pull or compose called.
+- `test_job_dirty_between_proposal_and_confirm` — repo clean at proposal, dirty at execution → FAILED.
+- `test_job_pull_failure_stops_early` — git pull fails → FAILED PULLING, no compose called.
+- `test_job_first_component_failure_stops_loop` — backend compose fails → FAILED, frontend compose not called.
+- `test_job_backend_only` — components=["backend"] → compose called once for backend service only.
+- `test_job_frontend_only` — components=["frontend"] → compose called once for frontend service only.
+- `test_job_success_returns_sha_and_url` — full success → status=SUCCEEDED, deployed_sha present, preview_url present.
+- `test_job_lock_released_after_failure` — command failure → lock released (can acquire again immediately).
+- `test_job_lock_released_after_exception` — unexpected exception in thread → lock released.
+- `test_job_git_timeout` — git pull exceeds timeout → FAILED PULLING, lock released.
+- `test_job_compose_timeout` — docker compose exceeds timeout → FAILED BUILDING, lock released.
+- `test_job_path_not_exist` — configured path missing → FAILED, no subprocess called.
+- `test_job_config_reloaded_at_execution` — stale repo_path in pending action not used; fresh config applied.
+- `test_job_stale_service_name_ignored` — tampered service name not executed; service from config used.
+
+#### Status polling endpoint
+
+- `test_get_deployment_status_running` — job in RUNNING state → 200 with stage.
+- `test_get_deployment_status_succeeded` — completed job → 200 with sha, preview_url.
+- `test_get_deployment_status_project_mismatch` — wrong project_id → 404.
+- `test_get_deployment_status_unknown` — unknown deployment_id → 404.
+
+#### Frontend tests (`apps/dashboard/src/components/ProjectWorkspacePanel.test.jsx` or similar)
+
+- `test_confirm_card_renders_redeploy_fields` — renders safe_identifier, configured_branch, pull, components.
+- `test_confirm_card_shows_dirty_warning` — `has_dirty_warning=true` → warning badge visible.
+- `test_confirm_card_no_host_path_displayed` — no element contains the literal `repository_path` value.
+- `test_confirm_submits_only_action_id` — Confirm click sends only `action_id` to `confirmWorkspaceAction`; no path/branch/service override.
+- `test_polling_shows_stage` — mock polling returns BUILDING_backend → spinner text updated.
+- `test_polling_stops_on_succeeded` — SUCCEEDED state → confirmed bubble shown, no further fetch.
+- `test_polling_stops_on_failed` — FAILED state → error shown, no further fetch.
+
+---
+
+### 6. `services/supervisor/workspace_projects.example.yml` (new file)
+
+An example/documentation config with the full schema annotated; never loaded by tests.
+
+---
+
+## Excluded
+
+- SSE or WebSocket streaming of deployment progress (polling via new GET endpoint is sufficient).
+- Rollback on failure.
+- Production or cloud deployment.
+- Multi-host orchestration.
+- Arbitrary remote shell access or LLM-composed commands.
+- Hot-reload of `workspace_projects.yml` without Supervisor restart.
+- Allowing the LLM or frontend to select a branch other than the configured default branch.
+- Deployment cancellation or timeout-triggered abort.
+- Redeploying a project other than the active workspace project via the chat context.
+
+## Acceptance criteria
+
+- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe. Requesting an unconfigured project returns `intent=informational` with a refusal explanation and no proposed_action.
+- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested Docker Compose services being rebuilt/restarted.
+- No `git pull`, `git branch`, or `docker compose` command runs before the user clicks Confirm.
+- The confirmation card displays: safe project identifier (not the host path), configured branch, pull flag, selected components, and a dirty-repo warning when applicable.
+- At execution time, the background job re-reads `workspace_projects.yml` and derives `repo_path`, `default_branch`, service names, `allow_dirty`, and `preview_url` from config — values from the pending action or frontend are never used for command construction.
+- The background job reads the current Git branch at execution time; if it differs from `default_branch`, the job fails with a branch-mismatch message before any Git or Docker command.
+- The background job re-checks `git status --porcelain` at execution time; if dirty and `allow_dirty: false`, the job fails before any Git or Docker command.
+- The `workspace_action_confirm()` endpoint returns HTTP 409 (not 500) when a deployment for the same project is already running.
+- The in-memory per-project lock is always released in a `finally` block, regardless of success, failure, timeout, or unexpected exception.
+- The `workspace_action_confirm()` endpoint returns within one second with `{ok: true, deployment_id: ..., status: "RUNNING"}`; the Supervisor remains responsive to other requests during deployment.
+- The frontend polls `GET /workspace/projects/{project_id}/deployments/{deployment_id}` and updates the chat bubble with the current stage, deployed SHA and preview URL on success, or failed stage and log excerpt on failure.
+- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
+- On failure, the chat bubble shows the failed stage and the first 500 characters of the relevant stderr.
+- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
+- All test cases in `test_workspace_redeploy.py` pass.
+- No frontend test can construct or submit an arbitrary `repo_path`, branch, service name, or shell command via the confirmation card.
+
+---
+
+## Review
+
+# PLAN_FIX_REQUIRED
+
+## Review
+
+Plan review 02 for T227.
+
+## Summary
+
+The regenerated plan resolves the first review's repository, branch, configuration, asynchronous execution, locking, and test-coverage requirements. Three integration and failure-state corrections remain required before implementation.
+
+## Required fixes
+
+### 1. Add the deployment-status proxy to the Control API
+
+The dashboard calls:
+
+```text
+GET /api/projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+and the Supervisor exposes:
+
+```text
+GET /workspace/projects/{project_id}/deployments/{deployment_id}
+```
+
+The regenerated plan must modify `services/control_api/routes/workspace.py` to add:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+This route must validate the project through the existing dependency and forward the GET request to the Supervisor while preserving its response status and JSON body.
+
+Without this proxy, frontend polling will return 404.
+
+### 2. Preserve HTTP 409 responses through the Control API
+
+The current Control API forwarding helper explicitly raises only for selected 4xx statuses and for 5xx responses. A Supervisor `409 Conflict` may therefore be returned by the Control API as HTTP 200 with a `detail` body.
+
+The plan must update the workspace proxy so every Supervisor response with `status_code >= 400` is propagated with the original status, including:
+
+- 409 when another deployment is already running;
+- 404 for an unknown deployment;
+- other validation or execution errors.
+
+Add a test proving that a Supervisor 409 remains a Control API 409.
+
+### 3. Guarantee a terminal job state on timeouts and exceptions
+
+Releasing the per-project lock in `finally` is necessary but insufficient. If `_run_redeploy_job` raises, the daemon thread may terminate while the job remains permanently `RUNNING`.
+
+The regenerated plan must define a top-level exception boundary around the complete background job and ensure all non-success paths write a terminal job state:
+
+- `status = "FAILED"`;
+- `completed_at` set;
+- `error_stage` set to the active stage or a safe internal stage;
+- `error_excerpt` set to a sanitized, bounded message;
+- lock released in `finally`.
+
+Handle at least:
+
+- `subprocess.TimeoutExpired`;
+- `FileNotFoundError`;
+- missing or invalid configuration;
+- missing repository path or non-Git repository;
+- unexpected exceptions.
+
+Add tests verifying both the released lock and the persisted `FAILED` state for timeout and unexpected-exception paths.
+
+## Preserved requirements
+
+The next plan must preserve all corrections already integrated from plan review 01:
+
+- fresh dirty check after confirmation;
+- configured-branch enforcement;
+- no LLM/frontend-controlled executable branch, path, service, or command;
+- background deployment job and polling;
+- safe project identifier in the confirmation card;
+- HTTP 409 for concurrent deployment;
+- unconditional lock release;
+- backend and frontend security/concurrency tests.
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+---
+
+## Instructions de fix
+
+# Plan fix 02
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-02.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Add the Control API polling route
+
+Modify `services/control_api/routes/workspace.py` to expose:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+The route must:
+
+- use the existing project-resolution dependency;
+- forward to Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
+- preserve the Supervisor HTTP status and JSON response;
+- return 404 for an unknown deployment or project mismatch.
+
+Update `apps/dashboard/src/api/workspace.js` to call this Control API route consistently.
+
+### 2. Propagate every Supervisor error status, including 409
+
+Update the workspace proxy forwarding logic so any Supervisor response with `status_code >= 400` is returned or raised with the original HTTP status.
+
+In particular, concurrent redeployment must remain:
+
+```text
+409 Conflict
+```
+
+from Supervisor through Control API to the dashboard. It must not become HTTP 200 with a `detail` field.
+
+Add Control API tests for:
+
+- Supervisor 409 → Control API 409;
+- Supervisor 404 → Control API 404;
+- successful polling response → Control API 200 with unchanged job state.
+
+### 3. Persist FAILED for every background-job failure
+
+Wrap the complete `_run_redeploy_job` body with a top-level exception boundary.
+
+For every timeout, configuration failure, filesystem/Git error, missing executable, or unexpected exception, update the deployment job under `_deployment_jobs_lock` with:
+
+```python
+{
+    "status": "FAILED",
+    "completed_at": <utc timestamp>,
+    "error_stage": <current or safe failure stage>,
+    "error_excerpt": <sanitized message, maximum 500 characters>,
+}
+```
+
+Requirements:
+
+- never leave a terminated job in `RUNNING`;
+- handle `subprocess.TimeoutExpired` explicitly;
+- handle `FileNotFoundError` explicitly;
+- handle invalid/missing project configuration;
+- handle missing or non-Git repository paths;
+- catch unexpected exceptions, log the full server-side exception, and expose only a sanitized bounded excerpt;
+- release the project lock unconditionally in `finally`.
+
+Add tests proving that:
+
+- Git timeout produces `FAILED` and releases the lock;
+- Docker timeout produces `FAILED` and releases the lock;
+- unexpected exception produces `FAILED` and releases the lock;
+- missing executable produces `FAILED`;
+- frontend polling stops on each resulting `FAILED` response.
+
+## Requirements to preserve
+
+Do not regress the corrections already present in the current plan:
+
+- execution-time configuration reload;
+- configured branch only;
+- execution-time branch and dirty checks;
+- safe pending-action metadata;
+- background job returning immediately;
+- per-project conflict locking;
+- no host paths in the UI;
+- frontend submits only the opaque `action_id`;
+- existing capability behavior remains unchanged.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` with these corrections. Do not implement source code as part of the plan-fix step.
\ No newline at end of file
diff --git a/runs/T227/fixes/plan-fix-01.md b/runs/T227/fixes/plan-fix-01.md
new file mode 100644
index 00000000..5479dec8
--- /dev/null
+++ b/runs/T227/fixes/plan-fix-01.md
@@ -0,0 +1,119 @@
+# Plan fix 01
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-01.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Re-check the repository state at execution time
+
+The dirty-working-tree value collected while the action is proposed is informational only.
+
+After confirmation and immediately before any Git or Docker command, the Supervisor must run `git status --porcelain` again and apply the configured dirty-repository policy to the fresh result.
+
+The regenerated plan must not use a stored `has_dirty` value as the final safety decision.
+
+### 2. Enforce the Supervisor-configured branch
+
+The LLM and frontend must not select an arbitrary executable branch.
+
+For this initial implementation:
+
+- resolve the branch from the project's `default_branch` in `workspace_projects.yml`;
+- read the current branch at execution time with `git branch --show-current`;
+- refuse execution when the current branch differs from the configured branch;
+- use fast-forward-only pull semantics only after the branch check succeeds;
+- never merge a requested remote branch into a different current local branch.
+
+The pending action may display the resolved branch but must not treat an LLM-provided or frontend-provided branch as authoritative.
+
+### 3. Avoid blocking the Supervisor during a long deployment
+
+Git pull and Docker builds can take several minutes. Regenerate the plan around a background deployment job that returns immediately with a deployment identifier and a running status.
+
+Define:
+
+- job creation;
+- deployment identifier;
+- running, succeeded, and failed states;
+- status retrieval or polling from the Workspace;
+- persisted or safely retained progress;
+- final deployed revision;
+- preview URL;
+- failed stage and sanitized log excerpt.
+
+If synchronous execution is intentionally kept for a limited demo, the plan must explicitly document the limitation and include a design/test proving that other Supervisor requests remain serviceable while deployment runs.
+
+### 4. Strengthen locking and conflict handling
+
+The regenerated plan must:
+
+- use the resolved configured project id as the lock key;
+- document that an in-memory lock protects only one Supervisor process/worker;
+- release the lock in `finally` after success, command failure, timeout, cancellation, or unexpected exception;
+- return HTTP `409 Conflict` when a deployment is already running for the project, not HTTP 500.
+
+### 5. Resolve all sensitive execution values from current Supervisor configuration
+
+At confirmation/execution time, reload `workspace_projects.yml` and resolve from the safe configured `project_id`:
+
+- repository path;
+- default/configured branch;
+- allowed components;
+- Docker Compose service names;
+- dirty-repository policy;
+- preview URL.
+
+Do not trust or execute paths, branches, service names, commands, or endpoints originating from:
+
+- the frontend;
+- the LLM response;
+- stale pending-action metadata.
+
+The pending action must contain only safe identifiers and approved business parameters. The frontend confirmation card may display a safe repository identifier, not necessarily the full sensitive host path.
+
+### 6. Complete backend and frontend test coverage
+
+Add backend tests for:
+
+- repository becoming dirty between proposal and confirmation;
+- current branch differing from the configured branch;
+- rejection of an unapproved branch;
+- missing repository path;
+- configured path that is not a Git repository;
+- Git timeout;
+- Docker Compose timeout;
+- lock release after command failure, timeout, and unexpected exception;
+- first-component failure preventing later components from starting;
+- concurrent deployment returning HTTP 409;
+- configuration being reloaded at execution;
+- stale or tampered paths and service values being ignored.
+
+Add frontend tests for:
+
+- rendering project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
+- not displaying the full host path when a safe identifier exists;
+- Confirm submitting only the pending `action_id`;
+- no executable path, command, branch, or service override being submitted from editable client data.
+
+## Requirements that must remain preserved
+
+- No Git or Docker command runs before explicit confirmation.
+- Commands are constructed only by trusted Supervisor code.
+- Components remain limited to configured backend/frontend recipes.
+- The operation remains local; production/cloud deployment is out of scope.
+- Existing Workspace capabilities and informational chat behavior remain unchanged.
+- Functional development continues through GitHub issues and the AI Dev Factory pipeline.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` to incorporate every correction above. Do not implement application code during the plan-fix step.
diff --git a/runs/T227/fixes/plan-fix-02.md b/runs/T227/fixes/plan-fix-02.md
new file mode 100644
index 00000000..1e1874d5
--- /dev/null
+++ b/runs/T227/fixes/plan-fix-02.md
@@ -0,0 +1,101 @@
+# Plan fix 02
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-02.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Add the Control API polling route
+
+Modify `services/control_api/routes/workspace.py` to expose:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+The route must:
+
+- use the existing project-resolution dependency;
+- forward to Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
+- preserve the Supervisor HTTP status and JSON response;
+- return 404 for an unknown deployment or project mismatch.
+
+Update `apps/dashboard/src/api/workspace.js` to call this Control API route consistently.
+
+### 2. Propagate every Supervisor error status, including 409
+
+Update the workspace proxy forwarding logic so any Supervisor response with `status_code >= 400` is returned or raised with the original HTTP status.
+
+In particular, concurrent redeployment must remain:
+
+```text
+409 Conflict
+```
+
+from Supervisor through Control API to the dashboard. It must not become HTTP 200 with a `detail` field.
+
+Add Control API tests for:
+
+- Supervisor 409 → Control API 409;
+- Supervisor 404 → Control API 404;
+- successful polling response → Control API 200 with unchanged job state.
+
+### 3. Persist FAILED for every background-job failure
+
+Wrap the complete `_run_redeploy_job` body with a top-level exception boundary.
+
+For every timeout, configuration failure, filesystem/Git error, missing executable, or unexpected exception, update the deployment job under `_deployment_jobs_lock` with:
+
+```python
+{
+    "status": "FAILED",
+    "completed_at": <utc timestamp>,
+    "error_stage": <current or safe failure stage>,
+    "error_excerpt": <sanitized message, maximum 500 characters>,
+}
+```
+
+Requirements:
+
+- never leave a terminated job in `RUNNING`;
+- handle `subprocess.TimeoutExpired` explicitly;
+- handle `FileNotFoundError` explicitly;
+- handle invalid/missing project configuration;
+- handle missing or non-Git repository paths;
+- catch unexpected exceptions, log the full server-side exception, and expose only a sanitized bounded excerpt;
+- release the project lock unconditionally in `finally`.
+
+Add tests proving that:
+
+- Git timeout produces `FAILED` and releases the lock;
+- Docker timeout produces `FAILED` and releases the lock;
+- unexpected exception produces `FAILED` and releases the lock;
+- missing executable produces `FAILED`;
+- frontend polling stops on each resulting `FAILED` response.
+
+## Requirements to preserve
+
+Do not regress the corrections already present in the current plan:
+
+- execution-time configuration reload;
+- configured branch only;
+- execution-time branch and dirty checks;
+- safe pending-action metadata;
+- background job returning immediately;
+- per-project conflict locking;
+- no host paths in the UI;
+- frontend submits only the opaque `action_id`;
+- existing capability behavior remains unchanged.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` with these corrections. Do not implement source code as part of the plan-fix step.
diff --git a/runs/T227/implementation-output.md b/runs/T227/implementation-output.md
new file mode 100644
index 00000000..af4681d5
--- /dev/null
+++ b/runs/T227/implementation-output.md
@@ -0,0 +1,23 @@
+All tests pass. Here's a summary of what was implemented for T227:
+
+## Implementation Summary
+
+The full feature was already implemented across previous attempts. The only missing piece was the frontend test file, which I created.
+
+### Files modified or created
+
+| File | Status |
+|------|--------|
+| `services/supervisor/workspace_projects.yml` | Created — empty projects config (loaded at runtime) |
+| `services/supervisor/workspace_projects.example.yml` | Created — annotated schema documentation |
+| `services/supervisor/main.py` | Modified — added: `_workspace_redeploy_locks`, `_deployment_jobs`, `_load_workspace_projects_config()`, `_git_has_local_changes()`, `_get_redeploy_lock()`, `redeploy_project` capability in `_WORKSPACE_CAPABILITIES` and `_WORKSPACE_SYSTEM_PROMPT`, proposal-time validation in `workspace_chat()`, background-job branch in `workspace_action_confirm()`, `_run_redeploy_job()`, `GET /workspace/projects/{project_id}/deployments/{deployment_id}` |
+| `services/control_api/routes/workspace.py` | Already had `GET /projects/{project_id}/workspace/deployments/{deployment_id}` and correct 4xx passthrough |
+| `apps/dashboard/src/api/workspace.js` | Already had `getDeploymentStatus()` |
+| `apps/dashboard/src/components/ProjectWorkspacePanel.jsx` | Already had redeploy confirmation card, dirty warning, and polling loop |
+| `tests/supervisor/test_workspace_redeploy.py` | Already complete — 34 tests |
+| `tests/control_api/test_workspace_redeploy_proxy.py` | Already complete — 4 tests |
+| `apps/dashboard/tests/ProjectWorkspacePanel.test.jsx` | **Created** — 8 frontend tests |
+
+### Test results
+- **Python**: 38/38 pass
+- **Frontend**: 8/8 pass
diff --git a/runs/T227/plan.md b/runs/T227/plan.md
new file mode 100644
index 00000000..a5f9d842
--- /dev/null
+++ b/runs/T227/plan.md
@@ -0,0 +1,419 @@
+## Objective
+
+Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by Docker Compose service rebuilds for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow, with the deployment running in a background job so the Supervisor remains responsive.
+
+## Included
+
+### 1. New config file — `services/supervisor/workspace_projects.yml`
+
+Schema per project (loaded at execution time via env var `WORKSPACE_PROJECTS_CONFIG`):
+
+```yaml
+projects:
+  <project_id>:
+    display_name: "Human-readable name"     # optional, shown in confirmation card
+    repository_path: /host/path/to/repo
+    default_branch: main
+    allow_dirty: false         # false → reject if local uncommitted changes exist
+    redeploy:
+      backend:
+        service: backend       # docker compose service name
+      frontend:
+        service: frontend
+    preview_url: http://localhost:3000       # optional, returned on success
+```
+
+`_load_workspace_projects_config() -> dict` reads this file; returns `{}` on missing file. Called at each proposal and execution — never cached between requests.
+
+---
+
+### 2. `services/supervisor/main.py`
+
+#### a. New module-level state
+
+```python
+# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
+_workspace_redeploy_locks: dict[str, threading.Lock] = {}
+_workspace_redeploy_locks_mutex = threading.Lock()
+
+# Background deployment job registry
+_deployment_jobs: dict[str, dict] = {}        # keyed by deployment_id (UUID)
+_deployment_jobs_lock = threading.Lock()
+```
+
+#### b. `_get_redeploy_lock(project_id: str) -> threading.Lock`
+
+Follows the existing `_get_analysis_lock` pattern (lazy creation, `_workspace_redeploy_locks_mutex` guards the dict).
+
+#### c. `_load_workspace_projects_config() -> dict`
+
+Reads `WORKSPACE_PROJECTS_CONFIG` env var (default: path relative to supervisor package). Returns `{}` on `FileNotFoundError`. Parses YAML; returns `{}` on parse error (logged as warning).
+
+#### d. `_git_has_local_changes(repo_path: str) -> bool`
+
+Runs `subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, timeout=10, capture_output=True, text=True)`. Returns `True` if stdout is non-empty. Raises on repo-not-found (non-existent path or non-git directory).
+
+#### e. `_WORKSPACE_CAPABILITIES` — add entry
+
+```python
+"redeploy_project": {
+    "description": "Pull the latest code and rebuild/restart selected services",
+    "confirmation_required": True,
+},
+```
+
+#### f. `_WORKSPACE_SYSTEM_PROMPT` — extend ALLOWED_CAPABILITIES
+
+```
+- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
+  The branch is always the project's configured default branch (do not include a branch param).
+  Params: pull (bool, default true), components (array, values: "backend", "frontend").
+  proposed_action format: {"capability": "redeploy_project", "description": "...",
+    "params": {"pull": true, "components": ["backend", "frontend"]}}
+```
+
+Update the RESPONSE FORMAT comment to document the optional `params` key.
+
+#### g. `workspace_chat()` — proposal-time validation for `redeploy_project`
+
+After the existing capability allowlist check, when `capability == "redeploy_project"`:
+
+1. Load config via `_load_workspace_projects_config()`. If `project_id` not in config or `redeploy` key absent → set `intent = "informational"`, include explanation in `reply`, return with no `proposed_action`.
+2. Extract `params` from LLM response:
+   - `components`: must be a non-empty subset of configured `redeploy` keys for the project. Reject unknown components with `intent = "informational"`.
+   - `pull`: default `True`. Accept only bool.
+   - Do **not** accept a `branch` param from the LLM — the branch is always resolved from config.
+3. Run `_git_has_local_changes(project_block["repository_path"])` informatively → `has_dirty_warning: bool`. On error (path missing, not a repo), set `has_dirty_warning = None`.
+4. Store in `_pending_workspace_actions[action_id]` under `_workspace_lock`:
+
+   ```python
+   {
+     "project_id": project_id,        # resolved configured key
+     "capability": "redeploy_project",
+     "description": <LLM description>,
+     "params": {"pull": bool, "components": [...]},  # validated
+     "has_dirty_warning": bool | None,              # informational only
+     "created_at": <iso timestamp>,
+   }
+   ```
+
+   **Not stored**: `repo_path`, branch, service names, preview URL — all re-derived from config at execution time.
+
+5. Add to `result["proposed_action"]`:
+
+   ```json
+   {
+     "capability": "redeploy_project",
+     "description": "...",
+     "action_id": "...",
+     "project_id": "timizer",
+     "safe_identifier": "timizer",        // project_id or display_name — never the host path
+     "configured_branch": "main",         // from config, display only
+     "pull": true,
+     "components": ["backend", "frontend"],
+     "has_dirty_warning": false
+   }
+   ```
+
+#### h. `workspace_action_confirm()` — background-job branch for `redeploy_project`
+
+After retrieving and validating the action (existing checks: action exists, project matches, capability allowlisted), add a special path for `redeploy_project` **before** calling `_execute_workspace_capability`:
+
+1. Extract `components` and `pull` from `action["params"]`.
+2. Attempt `lock = _get_redeploy_lock(project_id); acquired = lock.acquire(blocking=False)`.
+3. If `not acquired` → return `JSONResponse(status_code=409, content={"detail": "deployment already running for project"})` without removing action from pending.
+4. Generate `deployment_id = str(uuid4())`.
+5. Under `_deployment_jobs_lock`, initialize:
+
+   ```python
+   _deployment_jobs[deployment_id] = {
+     "deployment_id": deployment_id,
+     "project_id": project_id,
+     "status": "RUNNING",
+     "stage": None,
+     "started_at": <iso>,
+     "completed_at": None,
+     "result_message": None,
+     "deployed_sha": None,
+     "preview_url": None,
+     "error_stage": None,
+     "error_excerpt": None,
+   }
+   ```
+
+6. Remove action from `_pending_workspace_actions` under `_workspace_lock`.
+7. Spawn: `threading.Thread(target=_run_redeploy_job, args=(deployment_id, project_id, components, pull, lock), daemon=True).start()`.
+8. Return immediately: `{"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}`.
+
+#### i. `_run_redeploy_job(deployment_id, project_id, components, pull, lock)` — new function
+
+Runs in a daemon thread. Holds `lock` on entry; must release it unconditionally in `finally`.
+
+**Top-level exception boundary**: the entire function body is wrapped in a `try / except Exception as exc` block with a `finally` that releases `lock`. Any uncaught exception writes `status="FAILED"`, `completed_at` (utc iso), `error_stage="INTERNAL_ERROR"`, `error_excerpt=str(exc)[:500]` to the job under `_deployment_jobs_lock`, and logs the full traceback server-side via `logger.exception`.
+
+**Invariant**: when the thread exits (normally or via any exception), the job record must have `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` must be set.
+
+All sensitive execution values resolved from config at the start of this function:
+
+```python
+config = _load_workspace_projects_config()
+project_block = config.get("projects", {}).get(project_id)
+```
+
+If `project_block` is None (config changed since proposal) → update job to FAILED (`error_stage="CONFIG_MISSING"`, `completed_at` set), return.
+
+Resolve:
+- `repo_path = project_block["repository_path"]`
+- `default_branch = project_block["default_branch"]`
+- `allow_dirty = project_block.get("allow_dirty", False)`
+- `service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}`
+- `preview_url = project_block.get("preview_url")`
+
+If `repo_path` does not exist on disk → FAILED, `error_stage="PATH_NOT_FOUND"`, `completed_at` set. Return.
+
+Validate that each component in `components` exists in `service_map`; FAILED, `error_stage="INVALID_COMPONENT"`, `completed_at` set. Return.
+
+**Branch check (before any Git/Docker command):**
+1. Run `git branch --show-current` in `repo_path` (timeout=10).
+2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
+3. `subprocess.TimeoutExpired` → FAILED, `error_stage="BRANCH_CHECK_TIMEOUT"`, `error_excerpt="git branch --show-current timed out"`, `completed_at` set. Return.
+4. Non-zero returncode → FAILED, `error_stage="BRANCH_CHECK"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.
+5. If current branch ≠ `default_branch` → FAILED, `error_stage="BRANCH_MISMATCH"`, `error_excerpt=f"current branch '{current}' differs from configured branch '{default_branch}'"`, `completed_at` set. Return.
+
+**Fresh dirty check (before any Git/Docker command):**
+1. Call `_git_has_local_changes(repo_path)`.
+2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
+3. `subprocess.TimeoutExpired` → FAILED, `error_stage="DIRTY_CHECK_TIMEOUT"`, `completed_at` set. Return.
+4. If True and `allow_dirty` is False → FAILED, `error_stage="DIRTY_CHECK"`, `error_excerpt="uncommitted changes detected"`, `completed_at` set. Return.
+
+**Execution sequence:**
+
+For each stage, update `_deployment_jobs[deployment_id]["stage"]` under `_deployment_jobs_lock` before running the command.
+
+- If `pull` is True:
+  - Update stage → `"PULLING"`.
+  - `subprocess.run(["git", "pull", "--ff-only", "origin", default_branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`.
+  - `subprocess.TimeoutExpired` → FAILED, `error_stage="PULLING"`, `error_excerpt="git pull timed out after 120 s"`, `completed_at` set. Return.
+  - `FileNotFoundError` → FAILED, `error_stage="PULLING"`, `error_excerpt="git executable not found"`, `completed_at` set. Return.
+  - Non-zero returncode → FAILED, `error_stage="PULLING"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.
+
+- For each `component` in `components` (in order; first failure stops the loop):
+  - `service = service_map[component]`.
+  - Update stage → `f"BUILDING_{component}"`.
+  - `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`.
+  - `subprocess.TimeoutExpired` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker compose timed out after 300 s"`, `completed_at` set. Return.
+  - `FileNotFoundError` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker executable not found"`, `completed_at` set. Return.
+  - Non-zero returncode → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.
+
+- Get deployed SHA: `subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10, ...)`. Failure here is non-fatal: use `deployed_sha = None`.
+
+- Update job to SUCCEEDED: `deployed_sha`, `preview_url`, `result_message`, `completed_at`.
+
+Log each stage to `logger.info("redeploy %s: stage=%s", project_id, stage)`.
+
+`finally` block: `lock.release()`. Always executes on success, failure, timeout, and unexpected exception.
+
+#### j. New Supervisor endpoint — `GET /workspace/projects/{project_id}/deployments/{deployment_id}`
+
+Returns current job state for polling:
+
+- 200: full `_deployment_jobs[deployment_id]` dict, when `_deployment_jobs[deployment_id]["project_id"] == project_id`.
+- 404: `deployment_id` not found, or `project_id` mismatch.
+
+---
+
+### 3. `services/control_api/routes/workspace.py`
+
+#### a. New polling proxy route
+
+Add:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+This route must:
+- use the existing project-resolution dependency to validate `project_id`;
+- forward to the Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
+- preserve the Supervisor HTTP status code and JSON response body verbatim;
+- return 404 for an unknown deployment or project mismatch (pass through Supervisor 404).
+
+#### b. Propagate all Supervisor error statuses (≥ 400)
+
+Update the workspace proxy forwarding helper so that **any** Supervisor response with `status_code >= 400` is returned with the original HTTP status. This currently applies to:
+
+- `409 Conflict` (concurrent deployment already running);
+- `404 Not Found` (unknown deployment, unknown action);
+- any other 4xx or 5xx from the Supervisor.
+
+The forwarded response must carry the same `status_code` and the same JSON body as the Supervisor response. It must not be silently collapsed to HTTP 200 with a `detail` field.
+
+---
+
+### 4. `apps/dashboard/src/api/workspace.js`
+
+Add:
+
+```js
+export const getDeploymentStatus = (projectId, deploymentId) =>
+  api.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`);
+```
+
+The URL targets the Control API route added in §3a.
+
+---
+
+### 5. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`
+
+#### Extend `ActionConfirmCard`
+
+When `message.proposedAction?.capability === 'redeploy_project'`, render additional rows below the description:
+
+- **Project**: `message.proposedAction.safe_identifier`
+- **Branch**: `message.proposedAction.configured_branch`
+- **Pull**: Yes / No from `message.proposedAction.pull`
+- **Components**: comma-joined `message.proposedAction.components`
+- **Local changes**: warning badge when `message.proposedAction.has_dirty_warning === true`
+
+Do **not** display any host path. Use `safe_identifier` only.
+
+No changes to the Confirm button or the existing `confirmWorkspaceAction` API call.
+
+#### Background deployment polling in `handleConfirmAction`
+
+When the confirm response includes `deployment_id` (i.e. `res.data.deployment_id`):
+
+1. Update message state to `{ confirmed: false, deploymentId: res.data.deployment_id, deploymentStage: 'RUNNING' }`.
+2. Start a polling loop (`setTimeout` chain, interval ~2 s) calling `getDeploymentStatus(projectId, deploymentId)`.
+3. On each poll: update `deploymentStage` in message state.
+4. On `status === 'SUCCEEDED'`: set `confirmed: true`, `confirmResult` to success message including SHA and preview URL. Stop polling.
+5. On `status === 'FAILED'`: set `confirmError` to `${data.error_stage}: ${data.error_excerpt}`. Stop polling.
+6. On HTTP 4xx or 5xx from the polling request: stop polling, display error.
+7. Cap polling at 15 minutes; if exceeded, display "Deployment timed out — check supervisor logs."
+
+#### Render deployment progress in `ActionConfirmCard`
+
+When `message.deploymentId` is set and `message.confirmed` is false and no `confirmError`:
+- Show spinner with current stage label (e.g. "PULLING…", "BUILDING backend…").
+- Stage labels displayed: PULLING, BUILDING_backend, BUILDING_frontend, VERIFYING, SUCCEEDED, FAILED.
+
+---
+
+### 6. `tests/supervisor/test_workspace_redeploy.py` (new file)
+
+#### Config and helpers
+
+- `test_load_config_missing` — missing file → `{}`.
+- `test_load_config_valid` — valid YAML → parsed correctly.
+- `test_git_has_local_changes_clean` — empty porcelain → False.
+- `test_git_has_local_changes_dirty` — non-empty porcelain → True.
+- `test_git_has_local_changes_not_a_repo` — nonexistent path → raises.
+
+#### Proposal-time validation
+
+- `test_chat_unknown_project_returns_informational` — project not in config → intent=informational, no proposed_action.
+- `test_chat_unknown_component_rejected` — LLM requests component not in config → intent=informational.
+- `test_chat_branch_param_ignored` — LLM provides branch → stripped, configured branch used instead.
+- `test_chat_has_dirty_warning_propagated` — dirty repo → `has_dirty_warning=True` in proposed_action.
+
+#### Confirmation and lock
+
+- `test_confirm_starts_background_job` — confirm returns `{ok: true, deployment_id: ..., status: "RUNNING"}` immediately.
+- `test_confirm_concurrent_returns_409` — lock held → HTTP 409.
+- `test_confirm_unknown_action_id_returns_404` — forged action_id → 404.
+
+#### Background job execution
+
+- `test_job_branch_mismatch_rejected` — current branch ≠ configured → FAILED (status set, completed_at set), no git pull or compose called.
+- `test_job_dirty_between_proposal_and_confirm` — repo clean at proposal, dirty at execution → FAILED (status set, completed_at set).
+- `test_job_pull_failure_stops_early` — git pull fails → FAILED PULLING (status set, completed_at set), no compose called.
+- `test_job_first_component_failure_stops_loop` — backend compose fails → FAILED (status set, completed_at set), frontend compose not called.
+- `test_job_backend_only` — components=["backend"] → compose called once for backend service only.
+- `test_job_frontend_only` — components=["frontend"] → compose called once for frontend service only.
+- `test_job_success_returns_sha_and_url` — full success → status=SUCCEEDED, deployed_sha present, preview_url present, completed_at set.
+- `test_job_lock_released_after_failure` — command failure → lock released (can acquire again immediately), status=FAILED, completed_at set.
+- `test_job_lock_released_after_exception` — unexpected exception in thread → lock released, status=FAILED, completed_at set, error_stage="INTERNAL_ERROR".
+- `test_job_git_timeout` — git pull exceeds timeout → FAILED PULLING, lock released, status=FAILED, completed_at set.
+- `test_job_compose_timeout` — docker compose exceeds timeout → FAILED BUILDING, lock released, status=FAILED, completed_at set.
+- `test_job_git_not_found` — git executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
+- `test_job_docker_not_found` — docker executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
+- `test_job_path_not_exist` — configured path missing → FAILED PATH_NOT_FOUND, no subprocess called, lock released, completed_at set.
+- `test_job_config_reloaded_at_execution` — stale repo_path in pending action not used; fresh config applied.
+- `test_job_stale_service_name_ignored` — tampered service name not executed; service from config used.
+- `test_job_config_missing_at_execution` — project removed from config between proposal and execution → FAILED CONFIG_MISSING, lock released, completed_at set.
+- `test_job_terminal_state_always_set` — simulate unexpected exception → status=FAILED, completed_at set, error_stage="INTERNAL_ERROR", lock released.
+
+#### Supervisor status polling endpoint
+
+- `test_get_deployment_status_running` — job in RUNNING state → 200 with stage.
+- `test_get_deployment_status_succeeded` — completed job → 200 with sha, preview_url.
+- `test_get_deployment_status_project_mismatch` — wrong project_id → 404.
+- `test_get_deployment_status_unknown` — unknown deployment_id → 404.
+
+---
+
+### 7. `tests/control_api/test_workspace_redeploy_proxy.py` (new file)
+
+#### Control API proxy correctness
+
+- `test_proxy_polling_200` — Supervisor returns 200 with job state → Control API returns 200 with unchanged body.
+- `test_proxy_supervisor_409_becomes_control_api_409` — Supervisor returns 409 → Control API returns 409 (not 200 with detail).
+- `test_proxy_supervisor_404_becomes_control_api_404` — Supervisor returns 404 → Control API returns 404.
+- `test_proxy_unknown_project_returns_404` — project_id fails the existing project-resolution dependency → 404 before forwarding.
+
+---
+
+### 8. Frontend tests (`apps/dashboard/src/components/ProjectWorkspacePanel.test.jsx` or similar)
+
+- `test_confirm_card_renders_redeploy_fields` — renders safe_identifier, configured_branch, pull, components.
+- `test_confirm_card_shows_dirty_warning` — `has_dirty_warning=true` → warning badge visible.
+- `test_confirm_card_no_host_path_displayed` — no element contains the literal `repository_path` value.
+- `test_confirm_submits_only_action_id` — Confirm click sends only `action_id` to `confirmWorkspaceAction`; no path/branch/service override.
+- `test_polling_shows_stage` — mock polling returns BUILDING_backend → spinner text updated.
+- `test_polling_stops_on_succeeded` — SUCCEEDED state → confirmed bubble shown, no further fetch.
+- `test_polling_stops_on_failed` — FAILED state → error shown, no further fetch.
+- `test_polling_stops_on_http_error` — polling returns 4xx → error displayed, no further fetch.
+
+---
+
+### 9. `services/supervisor/workspace_projects.example.yml` (new file)
+
+An example/documentation config with the full schema annotated; never loaded by tests.
+
+---
+
+## Excluded
+
+- SSE or WebSocket streaming of deployment progress (polling via new GET endpoint is sufficient).
+- Rollback on failure.
+- Production or cloud deployment.
+- Multi-host orchestration.
+- Arbitrary remote shell access or LLM-composed commands.
+- Hot-reload of `workspace_projects.yml` without Supervisor restart.
+- Allowing the LLM or frontend to select a branch other than the configured default branch.
+- Deployment cancellation or timeout-triggered abort.
+- Redeploying a project other than the active workspace project via the chat context.
+
+## Acceptance criteria
+
+- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe. Requesting an unconfigured project returns `intent=informational` with a refusal explanation and no `proposed_action`.
+- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested Docker Compose services being rebuilt/restarted.
+- No `git pull`, `git branch`, or `docker compose` command runs before the user clicks Confirm.
+- The confirmation card displays: safe project identifier (not the host path), configured branch, pull flag, selected components, and a dirty-repo warning when applicable.
+- At execution time, the background job re-reads `workspace_projects.yml` and derives `repo_path`, `default_branch`, service names, `allow_dirty`, and `preview_url` from config — values from the pending action or frontend are never used for command construction.
+- The background job reads the current Git branch at execution time; if it differs from `default_branch`, the job fails with a branch-mismatch message before any Git or Docker command.
+- The background job re-checks `git status --porcelain` at execution time; if dirty and `allow_dirty: false`, the job fails before any Git or Docker command.
+- `workspace_action_confirm()` returns HTTP 409 when a deployment for the same project is already running; this 409 is preserved through the Control API proxy and reaches the dashboard as HTTP 409.
+- The in-memory per-project lock is always released in a `finally` block, regardless of success, failure, timeout, or unexpected exception.
+- `workspace_action_confirm()` returns within one second with `{ok: true, deployment_id: ..., status: "RUNNING"}`; the Supervisor remains responsive during deployment.
+- When `_run_redeploy_job` exits (normally or via any exception), the deployment job record has `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` is always set. A job must never remain permanently in `"RUNNING"` after the thread exits.
+- `subprocess.TimeoutExpired`, `FileNotFoundError`, missing/invalid configuration, missing repository path, non-Git repository, and unexpected exceptions each produce `status="FAILED"`, `completed_at` set, `error_stage` set to an appropriate label, and `error_excerpt` bounded to 500 characters.
+- The frontend polls `GET /projects/{project_id}/workspace/deployments/{deployment_id}` on the Control API and updates the chat bubble with the current stage, deployed SHA and preview URL on success, or failed stage and log excerpt on failure.
+- The Control API polling route validates `project_id` with the existing project-resolution dependency and forwards the Supervisor response status and body unchanged.
+- Control API tests confirm: Supervisor 409 → Control API 409; Supervisor 404 → Control API 404; Supervisor 200 → Control API 200 with unchanged body.
+- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
+- On failure, the chat bubble shows the failed stage and the first 500 characters of the relevant stderr or error message.
+- Frontend polling stops immediately when the response carries `status: "FAILED"`, `status: "SUCCEEDED"`, or an HTTP error; no further fetches are made after a terminal state.
+- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
+- All test cases in `test_workspace_redeploy.py` and `test_workspace_redeploy_proxy.py` pass.
+- No frontend test can construct or submit an arbitrary `repo_path`, branch, service name, or shell command via the confirmation card.
diff --git a/runs/T227/prompts/coder-attempt-1.md b/runs/T227/prompts/coder-attempt-1.md
new file mode 100644
index 00000000..d573a21e
--- /dev/null
+++ b/runs/T227/prompts/coder-attempt-1.md
@@ -0,0 +1,370 @@
+# GLOBAL CONTEXT
+
+# Global Context — ai-dev-factory
+
+## Vision
+
+ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.
+
+Le système doit permettre :
+- création de tickets structurés
+- génération de prompts spécialisés
+- orchestration planner/coder/reviewer/tester
+- reviews IA intermédiaires
+- maintenance automatique de la mémoire projet
+- workflow GitHub-centric basé sur PR
+
+Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).
+
+## Principes
+
+- GitHub = source de vérité workflow
+- PR = protocole de communication agentique
+- mémoire versionnée dans le repository
+- architecture explicitement documentée
+- aucun merge sans validations IA requises
+
+## Reviews obligatoires
+
+Aucun merge sans :
+- PLAN_APPROVED
+- IMPLEMENTATION_APPROVED
+- MEMORY_APPROVED
+
+## Mémoire
+
+Le système mémoire est composé de :
+- global-context.md
+- project-life.md
+- decisions-log.md
+
+## Workflow cible
+
+1. Ticket
+2. Classification risque
+3. Planner
+4. Review plan
+5. Coder
+6. Reviewer
+7. Tester
+8. Review implémentation
+9. Memory updater
+10. Review mémoire
+11. Merge
+
+---
+
+# ROLE
+
+# Role — Coder
+
+## Mission
+
+Implémenter strictement un ticket en suivant le plan validé et les skills applicables.
+
+## Tu dois
+
+- lire le ticket
+- lire le plan validé
+- respecter le scope
+- lister les fichiers créés ou modifiés
+- produire un changement minimal, lisible et testable
+- ajouter ou adapter les tests si nécessaire
+- signaler les hypothèses et limites
+
+## Tu ne dois pas
+
+- élargir le ticket
+- réécrire l’architecture sans demande explicite
+- faire un refactor massif non demandé
+- modifier la mémoire projet sauf si le ticket le demande explicitement
+- masquer les erreurs ou incertitudes
+
+## Sortie attendue
+
+- résumé des changements
+- liste des fichiers modifiés
+- vérifications effectuées
+- limites connues
+
+## Règles
+
+- coder uniquement après `PLAN_APPROVED`
+- ne jamais contourner les contraintes du plan
+- garder les changements petits et reviewables
+
+---
+
+# SKILL: workflow-discipline
+
+# Skill — Workflow Discipline
+
+## Objectif
+
+Faire respecter le lifecycle officiel des tickets et PR IA.
+
+## Règles
+
+- respecter l’ordre des étapes du workflow
+- ne pas bypass les reviews obligatoires
+- maintenir les statuts cohérents
+- conserver les artefacts versionnés
+- séparer plan, implémentation et mémoire
+
+## Refuser si
+
+- une review obligatoire est sautée
+- la mémoire est mise à jour avant validation implémentation
+- le workflow officiel est contourné
+
+---
+
+# SKILL: git-discipline
+
+# Skill — Git Discipline
+
+## Objectif
+
+Maintenir un historique Git propre, compréhensible et traçable.
+
+## Règles
+
+- un ticket = une unité de travail cohérente
+- éviter les commits mélangeant plusieurs sujets
+- utiliser des messages de commit explicites
+- conserver les PR lisibles
+- éviter les modifications hors scope
+- maintenir les fichiers mémoire cohérents avec les changements réels
+
+## Refuser si
+
+- la PR mélange plusieurs fonctionnalités
+- des changements non liés sont ajoutés
+- les commits deviennent impossibles à reviewer
+
+---
+
+# SKILL: code-quality
+
+# Skill — Code Quality
+
+## Objectif
+
+Produire des changements simples, lisibles, robustes et faciles à reviewer.
+
+## Règles
+
+- privilégier le code simple avant le code sophistiqué
+- utiliser des noms explicites
+- garder des fonctions courtes et lisibles
+- éviter la magie cachée
+- gérer les erreurs explicitement
+- ajouter des logs utiles sans bruit excessif
+- éviter les dépendances inutiles
+- conserver un changement borné au ticket
+
+## Refuser si
+
+- le code devient inutilement complexe
+- le ticket introduit une dépendance non justifiée
+- les erreurs sont masquées
+- les changements dépassent le scope demandé
+
+---
+
+# SKILL: refactor-safety
+
+# Skill — Refactor Safety
+
+## Objectif
+
+Limiter les régressions et les dérives de scope lors des modifications.
+
+## Règles
+
+- modifier uniquement le périmètre demandé
+- éviter les refactors transversaux implicites
+- préserver les comportements existants
+- maintenir la compatibilité sauf demande explicite
+- privilégier des changements incrémentaux
+
+## Refuser si
+
+- le ticket dérive vers une réécriture globale
+- plusieurs couches sont modifiées sans justification
+- le comportement change silencieusement
+
+---
+
+# SKILL: security
+
+# Skill — Security
+
+## Objectif
+
+Réduire les risques de sécurité et éviter les comportements dangereux.
+
+## Règles
+
+- ne pas exposer de secrets dans logs ou documentation
+- limiter les permissions au strict nécessaire
+- éviter les exécutions implicites dangereuses
+- valider les entrées externes
+- documenter les impacts sécurité importants
+- éviter les comportements destructifs implicites
+
+## Refuser si
+
+- des secrets sont hardcodés
+- des données sensibles sont logguées
+- une opération destructive n’est pas explicitement contrôlée
+
+---
+
+# TASK
+
+# Generic Coder Task
+
+Read the ticket and the approved plan below, then implement the required changes.
+
+The implementation must:
+- follow the approved plan strictly
+- remain within scope
+- list all created or modified files
+- be minimal, readable, and testable
+
+The ticket follows.
+
+
+# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat
+
+**Source**: GitHub Issue #311
+
+## Description
+
+## Objective
+
+Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.
+
+## User story
+
+As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:
+
+> Pull the latest changes and redeploy the backend and frontend of this project.
+
+so that I can update the locally hosted test environment without connecting manually to the host machine.
+
+## Expected interaction
+
+Example request:
+
+> Pull and redeploy the backend and frontend of Timizer.
+
+The Workspace must:
+
+1. resolve the current or explicitly named project;
+2. resolve the configured repository, branch, backend service, and frontend service;
+3. prepare a structured redeployment action;
+4. show the exact target and operation for human confirmation;
+5. delegate the approved action to the Supervisor;
+6. pull the configured branch;
+7. rebuild and restart the requested local components;
+8. return execution status and useful logs to the conversation.
+
+## Structured action
+
+The LLM should produce a constrained action proposal similar to:
+
+```json
+{
+  "action": "redeploy_project",
+  "project_id": "timizer",
+  "pull": true,
+  "branch": "main",
+  "components": ["backend", "frontend"]
+}
+```
+
+The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.
+
+## Project configuration
+
+Each authorized project must define its local redeployment recipe outside the prompt, for example:
+
+```yaml
+projects:
+  timizer:
+    repository_path: /projects/timizer
+    default_branch: main
+    redeploy:
+      backend:
+        service: backend
+      frontend:
+        service: frontend
+```
+
+The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.
+
+## Requirements
+
+- Support natural-language requests targeting:
+  - backend only;
+  - frontend only;
+  - backend and frontend.
+- Use the active Workspace project when the request says “this project”.
+- Allow an explicit project name only when it resolves to an authorized configured project.
+- Use only server-side project configuration and allowlisted operations.
+- Route every action through the Supervisor.
+- Require human confirmation before running the pull or redeployment.
+- The confirmation card must display:
+  - project;
+  - repository path or safe project identifier;
+  - branch;
+  - whether a pull will occur;
+  - components to rebuild/restart;
+  - whether local uncommitted changes were detected.
+- Refuse execution when:
+  - the project is unknown or not authorized;
+  - no redeployment recipe exists;
+  - the branch is not allowed;
+  - the repository has unsafe local changes according to the configured policy;
+  - another deployment for the same project is already running.
+- Do not use an unrestricted LLM-generated shell command.
+- Stream or periodically return progress for pull, build, restart, and health verification.
+- Return concise success or failure output with useful log excerpts.
+- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
+- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.
+
+## Suggested execution states
+
+- `PROPOSED`
+- `AWAITING_CONFIRMATION`
+- `PULLING`
+- `BUILDING`
+- `RESTARTING`
+- `VERIFYING`
+- `SUCCEEDED`
+- `FAILED`
+
+## Acceptance criteria
+
+- From a project Workspace, “pull and redeploy this project” resolves to that project.
+- The user can request backend only, frontend only, or both.
+- No repository mutation or service restart occurs before confirmation.
+- The Supervisor executes only the configured redeployment recipe.
+- The selected branch is pulled using the configured safe strategy.
+- Backend and frontend services are rebuilt/restarted according to the requested components.
+- Concurrent redeployment of the same project is prevented.
+- Pull, build, restart, and health-check progress is visible from the chat.
+- Success returns the deployed revision and local/preview URL when configured.
+- Failure returns the failed stage and actionable log excerpts.
+- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
+- Existing Workspace conversations and non-mutating chat behavior continue to work.
+
+## Out of scope
+
+- Production or cloud deployment.
+- Arbitrary remote shell access.
+- Allowing the LLM to compose unrestricted commands.
+- Rollback management.
+- Multi-host deployment orchestration.
\ No newline at end of file
diff --git a/runs/T227/prompts/coder-attempt-2.md b/runs/T227/prompts/coder-attempt-2.md
new file mode 100644
index 00000000..d573a21e
--- /dev/null
+++ b/runs/T227/prompts/coder-attempt-2.md
@@ -0,0 +1,370 @@
+# GLOBAL CONTEXT
+
+# Global Context — ai-dev-factory
+
+## Vision
+
+ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.
+
+Le système doit permettre :
+- création de tickets structurés
+- génération de prompts spécialisés
+- orchestration planner/coder/reviewer/tester
+- reviews IA intermédiaires
+- maintenance automatique de la mémoire projet
+- workflow GitHub-centric basé sur PR
+
+Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).
+
+## Principes
+
+- GitHub = source de vérité workflow
+- PR = protocole de communication agentique
+- mémoire versionnée dans le repository
+- architecture explicitement documentée
+- aucun merge sans validations IA requises
+
+## Reviews obligatoires
+
+Aucun merge sans :
+- PLAN_APPROVED
+- IMPLEMENTATION_APPROVED
+- MEMORY_APPROVED
+
+## Mémoire
+
+Le système mémoire est composé de :
+- global-context.md
+- project-life.md
+- decisions-log.md
+
+## Workflow cible
+
+1. Ticket
+2. Classification risque
+3. Planner
+4. Review plan
+5. Coder
+6. Reviewer
+7. Tester
+8. Review implémentation
+9. Memory updater
+10. Review mémoire
+11. Merge
+
+---
+
+# ROLE
+
+# Role — Coder
+
+## Mission
+
+Implémenter strictement un ticket en suivant le plan validé et les skills applicables.
+
+## Tu dois
+
+- lire le ticket
+- lire le plan validé
+- respecter le scope
+- lister les fichiers créés ou modifiés
+- produire un changement minimal, lisible et testable
+- ajouter ou adapter les tests si nécessaire
+- signaler les hypothèses et limites
+
+## Tu ne dois pas
+
+- élargir le ticket
+- réécrire l’architecture sans demande explicite
+- faire un refactor massif non demandé
+- modifier la mémoire projet sauf si le ticket le demande explicitement
+- masquer les erreurs ou incertitudes
+
+## Sortie attendue
+
+- résumé des changements
+- liste des fichiers modifiés
+- vérifications effectuées
+- limites connues
+
+## Règles
+
+- coder uniquement après `PLAN_APPROVED`
+- ne jamais contourner les contraintes du plan
+- garder les changements petits et reviewables
+
+---
+
+# SKILL: workflow-discipline
+
+# Skill — Workflow Discipline
+
+## Objectif
+
+Faire respecter le lifecycle officiel des tickets et PR IA.
+
+## Règles
+
+- respecter l’ordre des étapes du workflow
+- ne pas bypass les reviews obligatoires
+- maintenir les statuts cohérents
+- conserver les artefacts versionnés
+- séparer plan, implémentation et mémoire
+
+## Refuser si
+
+- une review obligatoire est sautée
+- la mémoire est mise à jour avant validation implémentation
+- le workflow officiel est contourné
+
+---
+
+# SKILL: git-discipline
+
+# Skill — Git Discipline
+
+## Objectif
+
+Maintenir un historique Git propre, compréhensible et traçable.
+
+## Règles
+
+- un ticket = une unité de travail cohérente
+- éviter les commits mélangeant plusieurs sujets
+- utiliser des messages de commit explicites
+- conserver les PR lisibles
+- éviter les modifications hors scope
+- maintenir les fichiers mémoire cohérents avec les changements réels
+
+## Refuser si
+
+- la PR mélange plusieurs fonctionnalités
+- des changements non liés sont ajoutés
+- les commits deviennent impossibles à reviewer
+
+---
+
+# SKILL: code-quality
+
+# Skill — Code Quality
+
+## Objectif
+
+Produire des changements simples, lisibles, robustes et faciles à reviewer.
+
+## Règles
+
+- privilégier le code simple avant le code sophistiqué
+- utiliser des noms explicites
+- garder des fonctions courtes et lisibles
+- éviter la magie cachée
+- gérer les erreurs explicitement
+- ajouter des logs utiles sans bruit excessif
+- éviter les dépendances inutiles
+- conserver un changement borné au ticket
+
+## Refuser si
+
+- le code devient inutilement complexe
+- le ticket introduit une dépendance non justifiée
+- les erreurs sont masquées
+- les changements dépassent le scope demandé
+
+---
+
+# SKILL: refactor-safety
+
+# Skill — Refactor Safety
+
+## Objectif
+
+Limiter les régressions et les dérives de scope lors des modifications.
+
+## Règles
+
+- modifier uniquement le périmètre demandé
+- éviter les refactors transversaux implicites
+- préserver les comportements existants
+- maintenir la compatibilité sauf demande explicite
+- privilégier des changements incrémentaux
+
+## Refuser si
+
+- le ticket dérive vers une réécriture globale
+- plusieurs couches sont modifiées sans justification
+- le comportement change silencieusement
+
+---
+
+# SKILL: security
+
+# Skill — Security
+
+## Objectif
+
+Réduire les risques de sécurité et éviter les comportements dangereux.
+
+## Règles
+
+- ne pas exposer de secrets dans logs ou documentation
+- limiter les permissions au strict nécessaire
+- éviter les exécutions implicites dangereuses
+- valider les entrées externes
+- documenter les impacts sécurité importants
+- éviter les comportements destructifs implicites
+
+## Refuser si
+
+- des secrets sont hardcodés
+- des données sensibles sont logguées
+- une opération destructive n’est pas explicitement contrôlée
+
+---
+
+# TASK
+
+# Generic Coder Task
+
+Read the ticket and the approved plan below, then implement the required changes.
+
+The implementation must:
+- follow the approved plan strictly
+- remain within scope
+- list all created or modified files
+- be minimal, readable, and testable
+
+The ticket follows.
+
+
+# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat
+
+**Source**: GitHub Issue #311
+
+## Description
+
+## Objective
+
+Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.
+
+## User story
+
+As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:
+
+> Pull the latest changes and redeploy the backend and frontend of this project.
+
+so that I can update the locally hosted test environment without connecting manually to the host machine.
+
+## Expected interaction
+
+Example request:
+
+> Pull and redeploy the backend and frontend of Timizer.
+
+The Workspace must:
+
+1. resolve the current or explicitly named project;
+2. resolve the configured repository, branch, backend service, and frontend service;
+3. prepare a structured redeployment action;
+4. show the exact target and operation for human confirmation;
+5. delegate the approved action to the Supervisor;
+6. pull the configured branch;
+7. rebuild and restart the requested local components;
+8. return execution status and useful logs to the conversation.
+
+## Structured action
+
+The LLM should produce a constrained action proposal similar to:
+
+```json
+{
+  "action": "redeploy_project",
+  "project_id": "timizer",
+  "pull": true,
+  "branch": "main",
+  "components": ["backend", "frontend"]
+}
+```
+
+The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.
+
+## Project configuration
+
+Each authorized project must define its local redeployment recipe outside the prompt, for example:
+
+```yaml
+projects:
+  timizer:
+    repository_path: /projects/timizer
+    default_branch: main
+    redeploy:
+      backend:
+        service: backend
+      frontend:
+        service: frontend
+```
+
+The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.
+
+## Requirements
+
+- Support natural-language requests targeting:
+  - backend only;
+  - frontend only;
+  - backend and frontend.
+- Use the active Workspace project when the request says “this project”.
+- Allow an explicit project name only when it resolves to an authorized configured project.
+- Use only server-side project configuration and allowlisted operations.
+- Route every action through the Supervisor.
+- Require human confirmation before running the pull or redeployment.
+- The confirmation card must display:
+  - project;
+  - repository path or safe project identifier;
+  - branch;
+  - whether a pull will occur;
+  - components to rebuild/restart;
+  - whether local uncommitted changes were detected.
+- Refuse execution when:
+  - the project is unknown or not authorized;
+  - no redeployment recipe exists;
+  - the branch is not allowed;
+  - the repository has unsafe local changes according to the configured policy;
+  - another deployment for the same project is already running.
+- Do not use an unrestricted LLM-generated shell command.
+- Stream or periodically return progress for pull, build, restart, and health verification.
+- Return concise success or failure output with useful log excerpts.
+- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
+- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.
+
+## Suggested execution states
+
+- `PROPOSED`
+- `AWAITING_CONFIRMATION`
+- `PULLING`
+- `BUILDING`
+- `RESTARTING`
+- `VERIFYING`
+- `SUCCEEDED`
+- `FAILED`
+
+## Acceptance criteria
+
+- From a project Workspace, “pull and redeploy this project” resolves to that project.
+- The user can request backend only, frontend only, or both.
+- No repository mutation or service restart occurs before confirmation.
+- The Supervisor executes only the configured redeployment recipe.
+- The selected branch is pulled using the configured safe strategy.
+- Backend and frontend services are rebuilt/restarted according to the requested components.
+- Concurrent redeployment of the same project is prevented.
+- Pull, build, restart, and health-check progress is visible from the chat.
+- Success returns the deployed revision and local/preview URL when configured.
+- Failure returns the failed stage and actionable log excerpts.
+- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
+- Existing Workspace conversations and non-mutating chat behavior continue to work.
+
+## Out of scope
+
+- Production or cloud deployment.
+- Arbitrary remote shell access.
+- Allowing the LLM to compose unrestricted commands.
+- Rollback management.
+- Multi-host deployment orchestration.
\ No newline at end of file
diff --git a/runs/T227/prompts/planner-attempt-1.md b/runs/T227/prompts/planner-attempt-1.md
new file mode 100644
index 00000000..476e8f01
--- /dev/null
+++ b/runs/T227/prompts/planner-attempt-1.md
@@ -0,0 +1,381 @@
+# GLOBAL CONTEXT
+
+# Global Context — ai-dev-factory
+
+## Vision
+
+ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.
+
+Le système doit permettre :
+- création de tickets structurés
+- génération de prompts spécialisés
+- orchestration planner/coder/reviewer/tester
+- reviews IA intermédiaires
+- maintenance automatique de la mémoire projet
+- workflow GitHub-centric basé sur PR
+
+Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).
+
+## Principes
+
+- GitHub = source de vérité workflow
+- PR = protocole de communication agentique
+- mémoire versionnée dans le repository
+- architecture explicitement documentée
+- aucun merge sans validations IA requises
+
+## Reviews obligatoires
+
+Aucun merge sans :
+- PLAN_APPROVED
+- IMPLEMENTATION_APPROVED
+- MEMORY_APPROVED
+
+## Mémoire
+
+Le système mémoire est composé de :
+- global-context.md
+- project-life.md
+- decisions-log.md
+
+## Workflow cible
+
+1. Ticket
+2. Classification risque
+3. Planner
+4. Review plan
+5. Coder
+6. Reviewer
+7. Tester
+8. Review implémentation
+9. Memory updater
+10. Review mémoire
+11. Merge
+
+---
+
+# ROLE
+
+# Role — Planner
+
+## Mission
+
+Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.
+
+## Tu dois
+
+- comprendre le ticket
+- proposer les étapes minimales
+- lister les fichiers à créer ou modifier
+- identifier les risques
+- expliciter le hors scope
+- produire un plan Markdown versionnable
+- signaler les hypothèses nécessaires
+
+## Tu ne dois pas
+
+- coder
+- réécrire le ticket
+- anticiper les tickets suivants
+- élargir le scope
+- masquer les incertitudes
+
+## Sortie attendue
+
+Un fichier de plan conforme à `ai/templates/plan-template.md`.
+
+## Règles
+
+- le plan doit rester court
+- le plan doit être exécutable par un Coder sans ambiguïté
+- toute hypothèse doit être explicite
+- toute dérive de scope doit être refusée
+
+## Structure obligatoire
+
+Tout plan doit contenir au minimum **les sections suivantes** (titres
+Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :
+
+| Français (recommandé)         | English equivalent       |
+|-------------------------------|--------------------------|
+| `## Contexte`                 | `## Context`             |
+| `## Objectif`                 | `## Objective`           |
+| `## Inclus`                   | `## Included`            |
+| `## Hors scope`               | `## Excluded`            |
+| `## Critères d'acceptation`   | `## Acceptance criteria` |
+
+Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.
+
+Ces titres sont obligatoires même si une section est courte : un ticket
+trivial peut produire un plan court, mais la structure doit rester stable.
+
+Ne jamais produire uniquement un résumé.
+Ne jamais produire un compte rendu d’implémentation.
+
+## Interdictions absolues
+
+Tu ne dois jamais écrire :
+- "implémentation terminée"
+- "syntaxe valide"
+- "changements appliqués"
+- "voici ce qui a été fait"
+
+Tu dois produire uniquement un plan futur, pas un compte rendu passé.
+
+---
+
+# SKILL: workflow-discipline
+
+# Skill — Workflow Discipline
+
+## Objectif
+
+Faire respecter le lifecycle officiel des tickets et PR IA.
+
+## Règles
+
+- respecter l’ordre des étapes du workflow
+- ne pas bypass les reviews obligatoires
+- maintenir les statuts cohérents
+- conserver les artefacts versionnés
+- séparer plan, implémentation et mémoire
+
+## Refuser si
+
+- une review obligatoire est sautée
+- la mémoire est mise à jour avant validation implémentation
+- le workflow officiel est contourné
+
+---
+
+# SKILL: architecture-discipline
+
+# Skill — Architecture Discipline
+
+## Objectif
+
+Préserver la cohérence architecture du projet dans le temps.
+
+## Règles
+
+- respecter les invariants documentés
+- éviter les couplages implicites
+- éviter les dépendances inutiles
+- éviter les refactors transversaux non demandés
+- documenter toute nouvelle règle structurante
+- privilégier les changements locaux et bornés
+
+## Refuser si
+
+- le scope dérive
+- plusieurs couches sont modifiées sans justification
+- des conventions existantes sont cassées
+- la mémoire projet devient incohérente
+
+---
+
+# SKILL: documentation
+
+# Skill — Documentation
+
+## Objectif
+
+Maintenir une documentation utile, concise et alignée avec le code réel.
+
+## Règles
+
+- documenter les décisions importantes
+- éviter les documentations vagues
+- garder la mémoire projet cohérente
+- expliciter les invariants architecture
+- préférer Markdown simple et versionnable
+
+## Refuser si
+
+- la documentation diverge du comportement réel
+- la mémoire contient des suppositions non validées
+- des décisions importantes ne sont pas tracées
+
+---
+
+# TASK
+
+The ticket follows.
+# Generic Planner Task Read the ticket below and produce a detailed implementation plan.
+
+## Artifact-only output (strict)
+
+Your response will be written verbatim to `runs/<ticket>/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+
+This rule applies to both initial plans and rewrites after a review.
+Examples of forbidden openings: "The plan has been rewritten…",
+"This plan now covers…", "Plan rewritten as a real implementation
+document…", "Key points covered…", "The document now contains…",
+"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".
+
+Do not use the Write tool on `plan.md` and then print a status summary —
+your stdout IS the artifact. If you do write the file, stdout must still
+be the full plan (same four headings), not a report about it.
+
+## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
+## Objective
+## Included
+## Excluded
+## Acceptance criteria
+These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
+markdown
+## Objective
+Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
+naming convention. Behaviour is preserved.
+
+## Included
+- `utils.py`: rename `foo` → `bar`, update the docstring.
+- `tests/test_utils.py`: update the single import and assertion.
+
+## Excluded
+- Renaming callers in other modules (tracked in a follow-up ticket).
+- Any logic change inside `foo` / `bar`.
+
+## Acceptance criteria
+- `utils.py` no longer defines `foo`.
+- `pytest tests/test_utils.py` passes.
+- No other file references the old name.
+
+The ticket follows.
+
+
+
+# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat
+
+**Source**: GitHub Issue #311
+
+## Description
+
+## Objective
+
+Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.
+
+## User story
+
+As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:
+
+> Pull the latest changes and redeploy the backend and frontend of this project.
+
+so that I can update the locally hosted test environment without connecting manually to the host machine.
+
+## Expected interaction
+
+Example request:
+
+> Pull and redeploy the backend and frontend of Timizer.
+
+The Workspace must:
+
+1. resolve the current or explicitly named project;
+2. resolve the configured repository, branch, backend service, and frontend service;
+3. prepare a structured redeployment action;
+4. show the exact target and operation for human confirmation;
+5. delegate the approved action to the Supervisor;
+6. pull the configured branch;
+7. rebuild and restart the requested local components;
+8. return execution status and useful logs to the conversation.
+
+## Structured action
+
+The LLM should produce a constrained action proposal similar to:
+
+```json
+{
+  "action": "redeploy_project",
+  "project_id": "timizer",
+  "pull": true,
+  "branch": "main",
+  "components": ["backend", "frontend"]
+}
+```
+
+The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.
+
+## Project configuration
+
+Each authorized project must define its local redeployment recipe outside the prompt, for example:
+
+```yaml
+projects:
+  timizer:
+    repository_path: /projects/timizer
+    default_branch: main
+    redeploy:
+      backend:
+        service: backend
+      frontend:
+        service: frontend
+```
+
+The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.
+
+## Requirements
+
+- Support natural-language requests targeting:
+  - backend only;
+  - frontend only;
+  - backend and frontend.
+- Use the active Workspace project when the request says “this project”.
+- Allow an explicit project name only when it resolves to an authorized configured project.
+- Use only server-side project configuration and allowlisted operations.
+- Route every action through the Supervisor.
+- Require human confirmation before running the pull or redeployment.
+- The confirmation card must display:
+  - project;
+  - repository path or safe project identifier;
+  - branch;
+  - whether a pull will occur;
+  - components to rebuild/restart;
+  - whether local uncommitted changes were detected.
+- Refuse execution when:
+  - the project is unknown or not authorized;
+  - no redeployment recipe exists;
+  - the branch is not allowed;
+  - the repository has unsafe local changes according to the configured policy;
+  - another deployment for the same project is already running.
+- Do not use an unrestricted LLM-generated shell command.
+- Stream or periodically return progress for pull, build, restart, and health verification.
+- Return concise success or failure output with useful log excerpts.
+- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
+- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.
+
+## Suggested execution states
+
+- `PROPOSED`
+- `AWAITING_CONFIRMATION`
+- `PULLING`
+- `BUILDING`
+- `RESTARTING`
+- `VERIFYING`
+- `SUCCEEDED`
+- `FAILED`
+
+## Acceptance criteria
+
+- From a project Workspace, “pull and redeploy this project” resolves to that project.
+- The user can request backend only, frontend only, or both.
+- No repository mutation or service restart occurs before confirmation.
+- The Supervisor executes only the configured redeployment recipe.
+- The selected branch is pulled using the configured safe strategy.
+- Backend and frontend services are rebuilt/restarted according to the requested components.
+- Concurrent redeployment of the same project is prevented.
+- Pull, build, restart, and health-check progress is visible from the chat.
+- Success returns the deployed revision and local/preview URL when configured.
+- Failure returns the failed stage and actionable log excerpts.
+- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
+- Existing Workspace conversations and non-mutating chat behavior continue to work.
+
+## Out of scope
+
+- Production or cloud deployment.
+- Arbitrary remote shell access.
+- Allowing the LLM to compose unrestricted commands.
+- Rollback management.
+- Multi-host deployment orchestration.
\ No newline at end of file
diff --git a/runs/T227/prompts/planner-attempt-2.md b/runs/T227/prompts/planner-attempt-2.md
new file mode 100644
index 00000000..7f479ab9
--- /dev/null
+++ b/runs/T227/prompts/planner-attempt-2.md
@@ -0,0 +1,771 @@
+# GLOBAL CONTEXT
+
+# Global Context — ai-dev-factory
+
+## Vision
+
+ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.
+
+Le système doit permettre :
+- création de tickets structurés
+- génération de prompts spécialisés
+- orchestration planner/coder/reviewer/tester
+- reviews IA intermédiaires
+- maintenance automatique de la mémoire projet
+- workflow GitHub-centric basé sur PR
+
+Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).
+
+## Principes
+
+- GitHub = source de vérité workflow
+- PR = protocole de communication agentique
+- mémoire versionnée dans le repository
+- architecture explicitement documentée
+- aucun merge sans validations IA requises
+
+## Reviews obligatoires
+
+Aucun merge sans :
+- PLAN_APPROVED
+- IMPLEMENTATION_APPROVED
+- MEMORY_APPROVED
+
+## Mémoire
+
+Le système mémoire est composé de :
+- global-context.md
+- project-life.md
+- decisions-log.md
+
+## Workflow cible
+
+1. Ticket
+2. Classification risque
+3. Planner
+4. Review plan
+5. Coder
+6. Reviewer
+7. Tester
+8. Review implémentation
+9. Memory updater
+10. Review mémoire
+11. Merge
+
+---
+
+# ROLE
+
+# Role — Planner
+
+## Mission
+
+Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.
+
+## Tu dois
+
+- comprendre le ticket
+- proposer les étapes minimales
+- lister les fichiers à créer ou modifier
+- identifier les risques
+- expliciter le hors scope
+- produire un plan Markdown versionnable
+- signaler les hypothèses nécessaires
+
+## Tu ne dois pas
+
+- coder
+- réécrire le ticket
+- anticiper les tickets suivants
+- élargir le scope
+- masquer les incertitudes
+
+## Sortie attendue
+
+Un fichier de plan conforme à `ai/templates/plan-template.md`.
+
+## Règles
+
+- le plan doit rester court
+- le plan doit être exécutable par un Coder sans ambiguïté
+- toute hypothèse doit être explicite
+- toute dérive de scope doit être refusée
+
+## Structure obligatoire
+
+Tout plan doit contenir au minimum **les sections suivantes** (titres
+Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :
+
+| Français (recommandé)         | English equivalent       |
+|-------------------------------|--------------------------|
+| `## Contexte`                 | `## Context`             |
+| `## Objectif`                 | `## Objective`           |
+| `## Inclus`                   | `## Included`            |
+| `## Hors scope`               | `## Excluded`            |
+| `## Critères d'acceptation`   | `## Acceptance criteria` |
+
+Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.
+
+Ces titres sont obligatoires même si une section est courte : un ticket
+trivial peut produire un plan court, mais la structure doit rester stable.
+
+Ne jamais produire uniquement un résumé.
+Ne jamais produire un compte rendu d’implémentation.
+
+## Interdictions absolues
+
+Tu ne dois jamais écrire :
+- "implémentation terminée"
+- "syntaxe valide"
+- "changements appliqués"
+- "voici ce qui a été fait"
+
+Tu dois produire uniquement un plan futur, pas un compte rendu passé.
+
+---
+
+# SKILL: workflow-discipline
+
+# Skill — Workflow Discipline
+
+## Objectif
+
+Faire respecter le lifecycle officiel des tickets et PR IA.
+
+## Règles
+
+- respecter l’ordre des étapes du workflow
+- ne pas bypass les reviews obligatoires
+- maintenir les statuts cohérents
+- conserver les artefacts versionnés
+- séparer plan, implémentation et mémoire
+
+## Refuser si
+
+- une review obligatoire est sautée
+- la mémoire est mise à jour avant validation implémentation
+- le workflow officiel est contourné
+
+---
+
+# SKILL: architecture-discipline
+
+# Skill — Architecture Discipline
+
+## Objectif
+
+Préserver la cohérence architecture du projet dans le temps.
+
+## Règles
+
+- respecter les invariants documentés
+- éviter les couplages implicites
+- éviter les dépendances inutiles
+- éviter les refactors transversaux non demandés
+- documenter toute nouvelle règle structurante
+- privilégier les changements locaux et bornés
+
+## Refuser si
+
+- le scope dérive
+- plusieurs couches sont modifiées sans justification
+- des conventions existantes sont cassées
+- la mémoire projet devient incohérente
+
+---
+
+# SKILL: documentation
+
+# Skill — Documentation
+
+## Objectif
+
+Maintenir une documentation utile, concise et alignée avec le code réel.
+
+## Règles
+
+- documenter les décisions importantes
+- éviter les documentations vagues
+- garder la mémoire projet cohérente
+- expliciter les invariants architecture
+- préférer Markdown simple et versionnable
+
+## Refuser si
+
+- la documentation diverge du comportement réel
+- la mémoire contient des suppositions non validées
+- des décisions importantes ne sont pas tracées
+
+---
+
+# TASK
+
+The ticket follows.
+# Generic Planner Task Read the ticket below and produce a detailed implementation plan.
+
+## Artifact-only output (strict)
+
+Your response will be written verbatim to `runs/<ticket>/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+
+This rule applies to both initial plans and rewrites after a review.
+Examples of forbidden openings: "The plan has been rewritten…",
+"This plan now covers…", "Plan rewritten as a real implementation
+document…", "Key points covered…", "The document now contains…",
+"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".
+
+Do not use the Write tool on `plan.md` and then print a status summary —
+your stdout IS the artifact. If you do write the file, stdout must still
+be the full plan (same four headings), not a report about it.
+
+## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
+## Objective
+## Included
+## Excluded
+## Acceptance criteria
+These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
+markdown
+## Objective
+Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
+naming convention. Behaviour is preserved.
+
+## Included
+- `utils.py`: rename `foo` → `bar`, update the docstring.
+- `tests/test_utils.py`: update the single import and assertion.
+
+## Excluded
+- Renaming callers in other modules (tracked in a follow-up ticket).
+- Any logic change inside `foo` / `bar`.
+
+## Acceptance criteria
+- `utils.py` no longer defines `foo`.
+- `pytest tests/test_utils.py` passes.
+- No other file references the old name.
+
+The ticket follows.
+
+
+
+# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat
+
+**Source**: GitHub Issue #311
+
+## Description
+
+## Objective
+
+Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.
+
+## User story
+
+As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:
+
+> Pull the latest changes and redeploy the backend and frontend of this project.
+
+so that I can update the locally hosted test environment without connecting manually to the host machine.
+
+## Expected interaction
+
+Example request:
+
+> Pull and redeploy the backend and frontend of Timizer.
+
+The Workspace must:
+
+1. resolve the current or explicitly named project;
+2. resolve the configured repository, branch, backend service, and frontend service;
+3. prepare a structured redeployment action;
+4. show the exact target and operation for human confirmation;
+5. delegate the approved action to the Supervisor;
+6. pull the configured branch;
+7. rebuild and restart the requested local components;
+8. return execution status and useful logs to the conversation.
+
+## Structured action
+
+The LLM should produce a constrained action proposal similar to:
+
+```json
+{
+  "action": "redeploy_project",
+  "project_id": "timizer",
+  "pull": true,
+  "branch": "main",
+  "components": ["backend", "frontend"]
+}
+```
+
+The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.
+
+## Project configuration
+
+Each authorized project must define its local redeployment recipe outside the prompt, for example:
+
+```yaml
+projects:
+  timizer:
+    repository_path: /projects/timizer
+    default_branch: main
+    redeploy:
+      backend:
+        service: backend
+      frontend:
+        service: frontend
+```
+
+The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.
+
+## Requirements
+
+- Support natural-language requests targeting:
+  - backend only;
+  - frontend only;
+  - backend and frontend.
+- Use the active Workspace project when the request says “this project”.
+- Allow an explicit project name only when it resolves to an authorized configured project.
+- Use only server-side project configuration and allowlisted operations.
+- Route every action through the Supervisor.
+- Require human confirmation before running the pull or redeployment.
+- The confirmation card must display:
+  - project;
+  - repository path or safe project identifier;
+  - branch;
+  - whether a pull will occur;
+  - components to rebuild/restart;
+  - whether local uncommitted changes were detected.
+- Refuse execution when:
+  - the project is unknown or not authorized;
+  - no redeployment recipe exists;
+  - the branch is not allowed;
+  - the repository has unsafe local changes according to the configured policy;
+  - another deployment for the same project is already running.
+- Do not use an unrestricted LLM-generated shell command.
+- Stream or periodically return progress for pull, build, restart, and health verification.
+- Return concise success or failure output with useful log excerpts.
+- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
+- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.
+
+## Suggested execution states
+
+- `PROPOSED`
+- `AWAITING_CONFIRMATION`
+- `PULLING`
+- `BUILDING`
+- `RESTARTING`
+- `VERIFYING`
+- `SUCCEEDED`
+- `FAILED`
+
+## Acceptance criteria
+
+- From a project Workspace, “pull and redeploy this project” resolves to that project.
+- The user can request backend only, frontend only, or both.
+- No repository mutation or service restart occurs before confirmation.
+- The Supervisor executes only the configured redeployment recipe.
+- The selected branch is pulled using the configured safe strategy.
+- Backend and frontend services are rebuilt/restarted according to the requested components.
+- Concurrent redeployment of the same project is prevented.
+- Pull, build, restart, and health-check progress is visible from the chat.
+- Success returns the deployed revision and local/preview URL when configured.
+- Failure returns the failed stage and actionable log excerpts.
+- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
+- Existing Workspace conversations and non-mutating chat behavior continue to work.
+
+## Out of scope
+
+- Production or cloud deployment.
+- Arbitrary remote shell access.
+- Allowing the LLM to compose unrestricted commands.
+- Rollback management.
+- Multi-host deployment orchestration.
+
+---
+
+## Contexte de retry injecté par run_ticket.py
+
+## Artifact-only instruction (mandatory)
+
+Your response will be written verbatim to `runs/T227/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+Openings such as "The plan has been rewritten…", "This plan now
+covers…", "Plan rewritten as…", "Key points covered…", "The
+document now…" make the output invalid.
+
+---
+
+## Output précédent
+
+Now I have everything I need. Let me write the plan.
+
+## Objective
+
+Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by a `docker compose up --build` for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow.
+
+## Included
+
+### 1. New config file — `supervisor/workspace_projects.yml`
+
+Schema per project:
+```yaml
+projects:
+  <project_id>:
+    repository_path: /host/path/to/repo
+    default_branch: main
+    allow_dirty: false         # reject if local uncommitted changes exist
+    redeploy:
+      backend:
+        service: backend       # docker compose service name
+      frontend:
+        service: frontend
+    preview_url: http://localhost:3000   # optional, returned on success
+```
+
+Loaded once at capability execution time via `_load_workspace_projects_config()`. No hot-reload required.
+
+---
+
+### 2. `supervisor/main.py`
+
+**a. New constants / state:**
+- `_WORKSPACE_REDEPLOY_LOCKS: dict[str, threading.Lock]` — per-project lock, created lazily via `_get_redeploy_lock(project_id)`.
+
+**b. New helper functions:**
+- `_load_workspace_projects_config() -> dict` — reads `supervisor/workspace_projects.yml` (path resolvable via env var `WORKSPACE_PROJECTS_CONFIG`); returns `{}` on missing file.
+- `_git_has_local_changes(repo_path: str) -> bool` — runs `git status --porcelain` (subprocess, timeout=10); returns True if output is non-empty.
+- `_resolve_redeploy_project(project_id, config) -> dict | None` — looks up the project in the loaded config, returns the project block or None if not found.
+
+**c. `_WORKSPACE_CAPABILITIES`:** add entry:
+```python
+"redeploy_project": {
+    "description": "Pull the latest code and rebuild/restart selected services",
+    "confirmation_required": True,
+},
+```
+
+**d. `_WORKSPACE_SYSTEM_PROMPT`:** extend ALLOWED_CAPABILITIES block:
+```
+- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
+  Params: pull (bool, default true), branch (string, default configured branch),
+  components (array, allowed values: "backend", "frontend").
+  proposed_action format: {"capability": "redeploy_project", "description": "...",
+    "params": {"pull": true, "branch": "main", "components": ["backend", "frontend"]}}
+```
+
+Also update the RESPONSE FORMAT comment to document the optional `params` key.
+
+**e. `workspace_chat()` endpoint — after capability allowlist check, for `redeploy_project`:**
+1. Load project config; reject with `intent=informational` + explanation if project not in config or config missing redeploy recipes.
+2. Extract and validate `params`:
+   - `components`: must be a non-empty subset of configured services for that project; reject unknowns.
+   - `pull`: default `True`.
+   - `branch`: default `project_block["default_branch"]`.
+3. Check local changes: run `_git_has_local_changes(repo_path)` and store result as `has_dirty` in pending action metadata.
+4. Store full metadata in `_pending_workspace_actions[action_id]`:
+   ```python
+   {
+     "project_id": project_id,
+     "capability": "redeploy_project",
+     "description": ...,
+     "params": {"pull": True, "branch": "main", "components": ["backend", "frontend"]},
+     "repo_path": "/host/path/to/repo",
+     "has_dirty": False,
+     "created_at": ...,
+   }
+   ```
+5. Add `repo_path`, `has_dirty`, `params` to `result["proposed_action"]` so the frontend can render the rich confirmation card.
+
+**f. `workspace_action_confirm()` endpoint:**
+- Pass `action["params"]`, `action["repo_path"]`, `action["has_dirty"]` to `_execute_workspace_capability`.
+
+**g. `_execute_workspace_capability(project_id, capability, params=None, repo_path=None, has_dirty=None)`:**
+Add `elif capability == "redeploy_project":` branch:
+1. Re-load config; re-validate project and components (defense-in-depth).
+2. Reject if `has_dirty` is True and `allow_dirty` is False for the project.
+3. Acquire `_get_redeploy_lock(project_id).acquire(blocking=False)`; return `(False, "deployment already running for this project")` if already locked.
+4. Inside try/finally (release lock in finally):
+   - If `params["pull"]` is True: run `subprocess.run(["git", "pull", "--ff-only", "origin", branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`. On non-zero returncode return `(False, f"PULLING failed: {stderr[:500]}")`.
+   - For each component in `params["components"]`, in order: run `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`. On non-zero returncode return `(False, f"BUILDING {component} failed: {stderr[:500]}")`.
+   - After all components succeed: get deployed revision with `git rev-parse --short HEAD`.
+   - Return `(True, f"Deployed revision {sha}. Services restarted: {components}. {preview_url or ''}")`.
+5. Log each stage to `logger.info(...)` with project_id and action_id.
+
+---
+
+### 3. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`
+
+**Extend `ActionConfirmCard`** — when `message.proposedAction.capability === 'redeploy_project'`, render additional details below the description:
+- Project: `message.proposedAction.project_id` (the workspace project_id)
+- Repository: `message.proposedAction.repo_path` (or a safe short identifier)
+- Branch: `message.proposedAction.params.branch`
+- Pull: yes/no from `message.proposedAction.params.pull`
+- Components: comma-joined list from `message.proposedAction.params.components`
+- Local changes: warning badge if `message.proposedAction.has_dirty === true`
+
+No changes to the confirm button or API call — they use the existing `confirmWorkspaceAction` path.
+
+---
+
+### 4. `tests/supervisor/test_workspace_redeploy.py` (new test file)
+
+- `test_load_workspace_projects_config_missing` — missing file returns `{}`.
+- `test_load_workspace_projects_config_valid` — valid YAML parsed correctly.
+- `test_git_has_local_changes_clean` — empty git status → False.
+- `test_git_has_local_changes_dirty` — non-empty git status → True.
+- `test_redeploy_unknown_project_rejected` — project not in config → capability not proposed.
+- `test_redeploy_unknown_component_rejected` — component not in project config → rejected.
+- `test_redeploy_dirty_rejected_when_not_allowed` — dirty repo + allow_dirty=false → `(False, ...)`.
+- `test_redeploy_concurrent_rejected` — lock held → `(False, "deployment already running ...")`.
+- `test_redeploy_pull_failure_stops_early` — git pull fails → returns failure, no compose called.
+- `test_redeploy_backend_only` — only backend component → compose called once for backend service.
+- `test_redeploy_success_returns_sha_and_url` — full success path → result contains sha and preview_url.
+
+---
+
+## Excluded
+
+- True SSE/WebSocket streaming of deployment progress (synchronous execution with stage summaries in result is sufficient for this ticket).
+- Rollback on failure.
+- Production or cloud deployment.
+- Multi-host orchestration.
+- Arbitrary remote shell access or LLM-generated commands.
+- Allowing redeployment of a project other than the active workspace project.
+- Hot-reload of `workspace_projects.yml` without supervisor restart.
+
+## Acceptance criteria
+
+- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe; requesting an unconfigured project returns a refusal explanation.
+- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested services being rebuilt.
+- No `git pull` or `docker compose` command runs before the user clicks Confirm in the chat.
+- The confirmation card displays: project id, repository path (or identifier), branch, whether pull is enabled, selected components, and a dirty-repo warning when applicable.
+- When `allow_dirty: false` and the repository has uncommitted changes, the confirm endpoint returns a failure with an explanation; no compose command is executed.
+- A second "Confirm" for the same project while the first is running returns HTTP 500 with "deployment already running."
+- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
+- On failure, the chat bubble shows the failed stage (PULLING or BUILDING \<component\>) and the first 500 characters of the relevant stderr.
+- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
+- All new test cases in `test_workspace_redeploy.py` pass.
+
+---
+
+## Review
+
+# PLAN_FIX_REQUIRED
+
+## Summary
+
+The plan is well structured and keeps redeployment behind the AI Workspace confirmation flow, but it requires additional safety, execution, and test coverage before implementation.
+
+## Required fixes
+
+### 1. Re-check repository state at confirmation time
+
+The dirty-working-tree check performed while proposing the action is only informational. The Supervisor must run `git status --porcelain` again after the user confirms and immediately before any Git or Docker command.
+
+Do not rely on the stored `has_dirty` value as the final safety check.
+
+### 2. Enforce a strict branch policy
+
+The redeployment must not accept an arbitrary branch generated by the LLM.
+
+For the initial implementation:
+
+- Use the project `default_branch` from `workspace_projects.yml`.
+- Read the current branch with `git branch --show-current` at execution time.
+- Refuse redeployment when the current branch does not match the configured branch, unless a controlled checkout policy is explicitly designed.
+- Run the pull only after this validation, using fast-forward-only semantics.
+- Never merge a requested remote branch into an unrelated current local branch.
+
+### 3. Do not block the Supervisor request for the full deployment duration
+
+A Git pull and two Docker builds may take many minutes. The preferred architecture is to start a background deployment job and return a deployment identifier and running status immediately.
+
+The plan must define:
+
+- deployment job creation;
+- running/succeeded/failed status;
+- status retrieval from the workspace;
+- storage of the final message, deployed revision, preview URL, and failed stage.
+
+If synchronous execution is intentionally retained for this demo ticket, explicitly document the limitation and prove that other Supervisor requests remain serviceable during execution.
+
+### 4. Improve redeployment locking and conflict response
+
+- Document that the in-memory project lock is valid only for a single Supervisor process/worker.
+- Ensure the lock is always released in `finally`, including unexpected exceptions and timeouts.
+- Return HTTP `409 Conflict` when another deployment is already running for the project, not HTTP 500.
+- Avoid using user-controlled values as lock keys; use the resolved configured project id.
+
+### 5. Resolve all sensitive execution values from Supervisor configuration
+
+At confirmation time, reload `workspace_projects.yml` and resolve from `project_id`:
+
+- repository path;
+- configured/default branch;
+- allowed components;
+- Docker Compose service names;
+- dirty-repository policy;
+- preview URL.
+
+Do not trust or execute `repo_path`, service names, branch names, or commands received from the frontend, the LLM response, or stale pending-action metadata.
+
+The pending action should contain only safe identifiers and approved business parameters.
+
+### 6. Add missing backend and frontend tests
+
+Backend tests must also cover:
+
+- repository becomes dirty between proposal and confirmation;
+- current branch differs from configured branch;
+- unapproved branch is rejected;
+- repository path does not exist;
+- configured path is not a Git repository;
+- Git timeout;
+- Docker Compose timeout;
+- lock release after command failure, timeout, and unexpected exception;
+- failure of the first component prevents later components from starting;
+- concurrent deployment returns HTTP 409;
+- execution reloads configuration and ignores stale/tampered path or service values.
+
+Frontend tests must cover:
+
+- confirmation card renders project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
+- the full sensitive host path is not displayed when a safe identifier is available;
+- Confirm submits only the pending `action_id` through the existing API;
+- no executable path, command, branch, or service override is submitted from editable client data.
+
+## Preserved requirements
+
+- No Git or Docker command runs before explicit user confirmation.
+- Commands are constructed by trusted Supervisor code only.
+- Components remain limited to configured backend/frontend recipes.
+- Functional development still goes through GitHub issues and the AI Dev Factory pipeline.
+- Existing workspace capabilities must continue working without regression.
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+---
+
+## Instructions de fix
+
+# Plan fix 01
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-01.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Re-check the repository state at execution time
+
+The dirty-working-tree value collected while the action is proposed is informational only.
+
+After confirmation and immediately before any Git or Docker command, the Supervisor must run `git status --porcelain` again and apply the configured dirty-repository policy to the fresh result.
+
+The regenerated plan must not use a stored `has_dirty` value as the final safety decision.
+
+### 2. Enforce the Supervisor-configured branch
+
+The LLM and frontend must not select an arbitrary executable branch.
+
+For this initial implementation:
+
+- resolve the branch from the project's `default_branch` in `workspace_projects.yml`;
+- read the current branch at execution time with `git branch --show-current`;
+- refuse execution when the current branch differs from the configured branch;
+- use fast-forward-only pull semantics only after the branch check succeeds;
+- never merge a requested remote branch into a different current local branch.
+
+The pending action may display the resolved branch but must not treat an LLM-provided or frontend-provided branch as authoritative.
+
+### 3. Avoid blocking the Supervisor during a long deployment
+
+Git pull and Docker builds can take several minutes. Regenerate the plan around a background deployment job that returns immediately with a deployment identifier and a running status.
+
+Define:
+
+- job creation;
+- deployment identifier;
+- running, succeeded, and failed states;
+- status retrieval or polling from the Workspace;
+- persisted or safely retained progress;
+- final deployed revision;
+- preview URL;
+- failed stage and sanitized log excerpt.
+
+If synchronous execution is intentionally kept for a limited demo, the plan must explicitly document the limitation and include a design/test proving that other Supervisor requests remain serviceable while deployment runs.
+
+### 4. Strengthen locking and conflict handling
+
+The regenerated plan must:
+
+- use the resolved configured project id as the lock key;
+- document that an in-memory lock protects only one Supervisor process/worker;
+- release the lock in `finally` after success, command failure, timeout, cancellation, or unexpected exception;
+- return HTTP `409 Conflict` when a deployment is already running for the project, not HTTP 500.
+
+### 5. Resolve all sensitive execution values from current Supervisor configuration
+
+At confirmation/execution time, reload `workspace_projects.yml` and resolve from the safe configured `project_id`:
+
+- repository path;
+- default/configured branch;
+- allowed components;
+- Docker Compose service names;
+- dirty-repository policy;
+- preview URL.
+
+Do not trust or execute paths, branches, service names, commands, or endpoints originating from:
+
+- the frontend;
+- the LLM response;
+- stale pending-action metadata.
+
+The pending action must contain only safe identifiers and approved business parameters. The frontend confirmation card may display a safe repository identifier, not necessarily the full sensitive host path.
+
+### 6. Complete backend and frontend test coverage
+
+Add backend tests for:
+
+- repository becoming dirty between proposal and confirmation;
+- current branch differing from the configured branch;
+- rejection of an unapproved branch;
+- missing repository path;
+- configured path that is not a Git repository;
+- Git timeout;
+- Docker Compose timeout;
+- lock release after command failure, timeout, and unexpected exception;
+- first-component failure preventing later components from starting;
+- concurrent deployment returning HTTP 409;
+- configuration being reloaded at execution;
+- stale or tampered paths and service values being ignored.
+
+Add frontend tests for:
+
+- rendering project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
+- not displaying the full host path when a safe identifier exists;
+- Confirm submitting only the pending `action_id`;
+- no executable path, command, branch, or service override being submitted from editable client data.
+
+## Requirements that must remain preserved
+
+- No Git or Docker command runs before explicit confirmation.
+- Commands are constructed only by trusted Supervisor code.
+- Components remain limited to configured backend/frontend recipes.
+- The operation remains local; production/cloud deployment is out of scope.
+- Existing Workspace capabilities and informational chat behavior remain unchanged.
+- Functional development continues through GitHub issues and the AI Dev Factory pipeline.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` to incorporate every correction above. Do not implement application code during the plan-fix step.
\ No newline at end of file
diff --git a/runs/T227/prompts/planner-attempt-3.md b/runs/T227/prompts/planner-attempt-3.md
new file mode 100644
index 00000000..fb07ed63
--- /dev/null
+++ b/runs/T227/prompts/planner-attempt-3.md
@@ -0,0 +1,945 @@
+# GLOBAL CONTEXT
+
+# Global Context — ai-dev-factory
+
+## Vision
+
+ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.
+
+Le système doit permettre :
+- création de tickets structurés
+- génération de prompts spécialisés
+- orchestration planner/coder/reviewer/tester
+- reviews IA intermédiaires
+- maintenance automatique de la mémoire projet
+- workflow GitHub-centric basé sur PR
+
+Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).
+
+## Principes
+
+- GitHub = source de vérité workflow
+- PR = protocole de communication agentique
+- mémoire versionnée dans le repository
+- architecture explicitement documentée
+- aucun merge sans validations IA requises
+
+## Reviews obligatoires
+
+Aucun merge sans :
+- PLAN_APPROVED
+- IMPLEMENTATION_APPROVED
+- MEMORY_APPROVED
+
+## Mémoire
+
+Le système mémoire est composé de :
+- global-context.md
+- project-life.md
+- decisions-log.md
+
+## Workflow cible
+
+1. Ticket
+2. Classification risque
+3. Planner
+4. Review plan
+5. Coder
+6. Reviewer
+7. Tester
+8. Review implémentation
+9. Memory updater
+10. Review mémoire
+11. Merge
+
+---
+
+# ROLE
+
+# Role — Planner
+
+## Mission
+
+Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.
+
+## Tu dois
+
+- comprendre le ticket
+- proposer les étapes minimales
+- lister les fichiers à créer ou modifier
+- identifier les risques
+- expliciter le hors scope
+- produire un plan Markdown versionnable
+- signaler les hypothèses nécessaires
+
+## Tu ne dois pas
+
+- coder
+- réécrire le ticket
+- anticiper les tickets suivants
+- élargir le scope
+- masquer les incertitudes
+
+## Sortie attendue
+
+Un fichier de plan conforme à `ai/templates/plan-template.md`.
+
+## Règles
+
+- le plan doit rester court
+- le plan doit être exécutable par un Coder sans ambiguïté
+- toute hypothèse doit être explicite
+- toute dérive de scope doit être refusée
+
+## Structure obligatoire
+
+Tout plan doit contenir au minimum **les sections suivantes** (titres
+Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :
+
+| Français (recommandé)         | English equivalent       |
+|-------------------------------|--------------------------|
+| `## Contexte`                 | `## Context`             |
+| `## Objectif`                 | `## Objective`           |
+| `## Inclus`                   | `## Included`            |
+| `## Hors scope`               | `## Excluded`            |
+| `## Critères d'acceptation`   | `## Acceptance criteria` |
+
+Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.
+
+Ces titres sont obligatoires même si une section est courte : un ticket
+trivial peut produire un plan court, mais la structure doit rester stable.
+
+Ne jamais produire uniquement un résumé.
+Ne jamais produire un compte rendu d’implémentation.
+
+## Interdictions absolues
+
+Tu ne dois jamais écrire :
+- "implémentation terminée"
+- "syntaxe valide"
+- "changements appliqués"
+- "voici ce qui a été fait"
+
+Tu dois produire uniquement un plan futur, pas un compte rendu passé.
+
+---
+
+# SKILL: workflow-discipline
+
+# Skill — Workflow Discipline
+
+## Objectif
+
+Faire respecter le lifecycle officiel des tickets et PR IA.
+
+## Règles
+
+- respecter l’ordre des étapes du workflow
+- ne pas bypass les reviews obligatoires
+- maintenir les statuts cohérents
+- conserver les artefacts versionnés
+- séparer plan, implémentation et mémoire
+
+## Refuser si
+
+- une review obligatoire est sautée
+- la mémoire est mise à jour avant validation implémentation
+- le workflow officiel est contourné
+
+---
+
+# SKILL: architecture-discipline
+
+# Skill — Architecture Discipline
+
+## Objectif
+
+Préserver la cohérence architecture du projet dans le temps.
+
+## Règles
+
+- respecter les invariants documentés
+- éviter les couplages implicites
+- éviter les dépendances inutiles
+- éviter les refactors transversaux non demandés
+- documenter toute nouvelle règle structurante
+- privilégier les changements locaux et bornés
+
+## Refuser si
+
+- le scope dérive
+- plusieurs couches sont modifiées sans justification
+- des conventions existantes sont cassées
+- la mémoire projet devient incohérente
+
+---
+
+# SKILL: documentation
+
+# Skill — Documentation
+
+## Objectif
+
+Maintenir une documentation utile, concise et alignée avec le code réel.
+
+## Règles
+
+- documenter les décisions importantes
+- éviter les documentations vagues
+- garder la mémoire projet cohérente
+- expliciter les invariants architecture
+- préférer Markdown simple et versionnable
+
+## Refuser si
+
+- la documentation diverge du comportement réel
+- la mémoire contient des suppositions non validées
+- des décisions importantes ne sont pas tracées
+
+---
+
+# TASK
+
+The ticket follows.
+# Generic Planner Task Read the ticket below and produce a detailed implementation plan.
+
+## Artifact-only output (strict)
+
+Your response will be written verbatim to `runs/<ticket>/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+
+This rule applies to both initial plans and rewrites after a review.
+Examples of forbidden openings: "The plan has been rewritten…",
+"This plan now covers…", "Plan rewritten as a real implementation
+document…", "Key points covered…", "The document now contains…",
+"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".
+
+Do not use the Write tool on `plan.md` and then print a status summary —
+your stdout IS the artifact. If you do write the file, stdout must still
+be the full plan (same four headings), not a report about it.
+
+## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
+## Objective
+## Included
+## Excluded
+## Acceptance criteria
+These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
+markdown
+## Objective
+Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
+naming convention. Behaviour is preserved.
+
+## Included
+- `utils.py`: rename `foo` → `bar`, update the docstring.
+- `tests/test_utils.py`: update the single import and assertion.
+
+## Excluded
+- Renaming callers in other modules (tracked in a follow-up ticket).
+- Any logic change inside `foo` / `bar`.
+
+## Acceptance criteria
+- `utils.py` no longer defines `foo`.
+- `pytest tests/test_utils.py` passes.
+- No other file references the old name.
+
+The ticket follows.
+
+
+
+# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat
+
+**Source**: GitHub Issue #311
+
+## Description
+
+## Objective
+
+Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.
+
+## User story
+
+As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:
+
+> Pull the latest changes and redeploy the backend and frontend of this project.
+
+so that I can update the locally hosted test environment without connecting manually to the host machine.
+
+## Expected interaction
+
+Example request:
+
+> Pull and redeploy the backend and frontend of Timizer.
+
+The Workspace must:
+
+1. resolve the current or explicitly named project;
+2. resolve the configured repository, branch, backend service, and frontend service;
+3. prepare a structured redeployment action;
+4. show the exact target and operation for human confirmation;
+5. delegate the approved action to the Supervisor;
+6. pull the configured branch;
+7. rebuild and restart the requested local components;
+8. return execution status and useful logs to the conversation.
+
+## Structured action
+
+The LLM should produce a constrained action proposal similar to:
+
+```json
+{
+  "action": "redeploy_project",
+  "project_id": "timizer",
+  "pull": true,
+  "branch": "main",
+  "components": ["backend", "frontend"]
+}
+```
+
+The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.
+
+## Project configuration
+
+Each authorized project must define its local redeployment recipe outside the prompt, for example:
+
+```yaml
+projects:
+  timizer:
+    repository_path: /projects/timizer
+    default_branch: main
+    redeploy:
+      backend:
+        service: backend
+      frontend:
+        service: frontend
+```
+
+The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.
+
+## Requirements
+
+- Support natural-language requests targeting:
+  - backend only;
+  - frontend only;
+  - backend and frontend.
+- Use the active Workspace project when the request says “this project”.
+- Allow an explicit project name only when it resolves to an authorized configured project.
+- Use only server-side project configuration and allowlisted operations.
+- Route every action through the Supervisor.
+- Require human confirmation before running the pull or redeployment.
+- The confirmation card must display:
+  - project;
+  - repository path or safe project identifier;
+  - branch;
+  - whether a pull will occur;
+  - components to rebuild/restart;
+  - whether local uncommitted changes were detected.
+- Refuse execution when:
+  - the project is unknown or not authorized;
+  - no redeployment recipe exists;
+  - the branch is not allowed;
+  - the repository has unsafe local changes according to the configured policy;
+  - another deployment for the same project is already running.
+- Do not use an unrestricted LLM-generated shell command.
+- Stream or periodically return progress for pull, build, restart, and health verification.
+- Return concise success or failure output with useful log excerpts.
+- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
+- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.
+
+## Suggested execution states
+
+- `PROPOSED`
+- `AWAITING_CONFIRMATION`
+- `PULLING`
+- `BUILDING`
+- `RESTARTING`
+- `VERIFYING`
+- `SUCCEEDED`
+- `FAILED`
+
+## Acceptance criteria
+
+- From a project Workspace, “pull and redeploy this project” resolves to that project.
+- The user can request backend only, frontend only, or both.
+- No repository mutation or service restart occurs before confirmation.
+- The Supervisor executes only the configured redeployment recipe.
+- The selected branch is pulled using the configured safe strategy.
+- Backend and frontend services are rebuilt/restarted according to the requested components.
+- Concurrent redeployment of the same project is prevented.
+- Pull, build, restart, and health-check progress is visible from the chat.
+- Success returns the deployed revision and local/preview URL when configured.
+- Failure returns the failed stage and actionable log excerpts.
+- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
+- Existing Workspace conversations and non-mutating chat behavior continue to work.
+
+## Out of scope
+
+- Production or cloud deployment.
+- Arbitrary remote shell access.
+- Allowing the LLM to compose unrestricted commands.
+- Rollback management.
+- Multi-host deployment orchestration.
+
+---
+
+## Contexte de retry injecté par run_ticket.py
+
+## Artifact-only instruction (mandatory)
+
+Your response will be written verbatim to `runs/T227/plan.md`.
+Rewrite the artifact itself. Do not describe the modifications.
+Do not explain what changed. Do not produce a status report.
+Openings such as "The plan has been rewritten…", "This plan now
+covers…", "Plan rewritten as…", "Key points covered…", "The
+document now…" make the output invalid.
+
+---
+
+## Output précédent
+
+## Objective
+
+Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by Docker Compose service rebuilds for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow, with the deployment running in a background job so the Supervisor remains responsive.
+
+## Included
+
+### 1. New config file — `services/supervisor/workspace_projects.yml`
+
+Schema per project (loaded at execution time via env var `WORKSPACE_PROJECTS_CONFIG`):
+
+```yaml
+projects:
+  <project_id>:
+    display_name: "Human-readable name"     # optional, shown in confirmation card
+    repository_path: /host/path/to/repo
+    default_branch: main
+    allow_dirty: false         # false → reject if local uncommitted changes exist
+    redeploy:
+      backend:
+        service: backend       # docker compose service name
+      frontend:
+        service: frontend
+    preview_url: http://localhost:3000       # optional, returned on success
+```
+
+`_load_workspace_projects_config() -> dict` reads this file; returns `{}` on missing file. Called at each proposal and execution — never cached between requests.
+
+---
+
+### 2. `services/supervisor/main.py`
+
+#### a. New module-level state
+
+```python
+# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
+_workspace_redeploy_locks: dict[str, threading.Lock] = {}
+_workspace_redeploy_locks_mutex = threading.Lock()
+
+# Background deployment job registry
+_deployment_jobs: dict[str, dict] = {}        # keyed by deployment_id (UUID)
+_deployment_jobs_lock = threading.Lock()
+```
+
+#### b. `_get_redeploy_lock(project_id: str) -> threading.Lock`
+
+Follows the existing `_get_analysis_lock` pattern (lazy creation, `_workspace_redeploy_locks_mutex` guards the dict).
+
+#### c. `_load_workspace_projects_config() -> dict`
+
+Reads `WORKSPACE_PROJECTS_CONFIG` env var (default: path relative to supervisor package). Returns `{}` on `FileNotFoundError`. Parses YAML; returns `{}` on parse error (logged as warning).
+
+#### d. `_git_has_local_changes(repo_path: str) -> bool`
+
+Runs `subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, timeout=10, capture_output=True, text=True)`. Returns `True` if stdout is non-empty. Raises on repo-not-found (non-existent path or non-git directory).
+
+#### e. `_WORKSPACE_CAPABILITIES` — add entry
+
+```python
+"redeploy_project": {
+    "description": "Pull the latest code and rebuild/restart selected services",
+    "confirmation_required": True,
+},
+```
+
+#### f. `_WORKSPACE_SYSTEM_PROMPT` — extend ALLOWED_CAPABILITIES
+
+```
+- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
+  The branch is always the project's configured default branch (do not include a branch param).
+  Params: pull (bool, default true), components (array, values: "backend", "frontend").
+  proposed_action format: {"capability": "redeploy_project", "description": "...",
+    "params": {"pull": true, "components": ["backend", "frontend"]}}
+```
+
+Update the RESPONSE FORMAT comment to document the optional `params` key.
+
+#### g. `workspace_chat()` — proposal-time validation for `redeploy_project`
+
+After the existing capability allowlist check, when `capability == "redeploy_project"`:
+
+1. Load config via `_load_workspace_projects_config()`. If `project_id` not in config or `redeploy` key absent → set `intent = "informational"`, include explanation in `reply`, return with no `proposed_action`.
+2. Extract `params` from LLM response:
+   - `components`: must be a non-empty subset of configured `redeploy` keys for the project. Reject unknown components with `intent = "informational"`.
+   - `pull`: default `True`. Accept only bool.
+   - Do **not** accept a `branch` param from the LLM — the branch is always resolved from config.
+3. Run `_git_has_local_changes(project_block["repository_path"])` informatively → `has_dirty_warning: bool`. On error (path missing, not a repo), set `has_dirty_warning = None`.
+4. Store in `_pending_workspace_actions[action_id]` under `_workspace_lock`:
+
+   ```python
+   {
+     "project_id": project_id,        # resolved configured key
+     "capability": "redeploy_project",
+     "description": <LLM description>,
+     "params": {"pull": bool, "components": [...]},  # validated
+     "has_dirty_warning": bool | None,              # informational only
+     "created_at": <iso timestamp>,
+   }
+   ```
+
+   **Not stored**: `repo_path`, branch, service names, preview URL — all re-derived from config at execution time.
+
+5. Add to `result["proposed_action"]`:
+
+   ```json
+   {
+     "capability": "redeploy_project",
+     "description": "...",
+     "action_id": "...",
+     "project_id": "timizer",
+     "safe_identifier": "timizer",        // project_id or display_name — never the host path
+     "configured_branch": "main",         // from config, display only
+     "pull": true,
+     "components": ["backend", "frontend"],
+     "has_dirty_warning": false
+   }
+   ```
+
+#### h. `workspace_action_confirm()` — background-job branch for `redeploy_project`
+
+After retrieving and validating the action (existing checks: action exists, project matches, capability allowlisted), add a special path for `redeploy_project` **before** calling `_execute_workspace_capability`:
+
+1. Extract `components` and `pull` from `action["params"]`.
+2. Attempt `lock = _get_redeploy_lock(project_id); acquired = lock.acquire(blocking=False)`.
+3. If `not acquired` → return `JSONResponse(status_code=409, content={"detail": "deployment already running for project"})` without removing action from pending.
+4. Generate `deployment_id = str(uuid4())`.
+5. Under `_deployment_jobs_lock`, initialize:
+
+   ```python
+   _deployment_jobs[deployment_id] = {
+     "deployment_id": deployment_id,
+     "project_id": project_id,
+     "status": "RUNNING",
+     "stage": None,
+     "started_at": <iso>,
+     "completed_at": None,
+     "result_message": None,
+     "deployed_sha": None,
+     "preview_url": None,
+     "error_stage": None,
+     "error_excerpt": None,
+   }
+   ```
+
+6. Remove action from `_pending_workspace_actions` under `_workspace_lock`.
+7. Spawn: `threading.Thread(target=_run_redeploy_job, args=(deployment_id, project_id, components, pull, lock), daemon=True).start()`.
+8. Return immediately: `{"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}`.
+
+#### i. `_run_redeploy_job(deployment_id, project_id, components, pull, lock)` — new function
+
+Runs in a daemon thread. Holds `lock` on entry; must release it in `finally` unconditionally.
+
+All sensitive execution values resolved from config at the start of this function:
+
+```python
+config = _load_workspace_projects_config()
+project_block = config.get("projects", {}).get(project_id)
+```
+
+If `project_block` is None (config changed since proposal) → update job to FAILED, return.
+
+Resolve:
+- `repo_path = project_block["repository_path"]`
+- `default_branch = project_block["default_branch"]`
+- `allow_dirty = project_block.get("allow_dirty", False)`
+- `service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}`
+- `preview_url = project_block.get("preview_url")`
+
+Validate that each component in `components` exists in `service_map`; FAILED otherwise.
+
+**Branch check (before any Git/Docker command):**
+1. Run `git branch --show-current` in `repo_path` (timeout=10). FAILED if command errors.
+2. If current branch ≠ `default_branch` → update job to FAILED stage="BRANCH_MISMATCH", error_excerpt=f"current branch '{current}' differs from configured branch '{default_branch}'". Return.
+
+**Fresh dirty check (before any Git/Docker command):**
+1. Run `_git_has_local_changes(repo_path)`. If True and `allow_dirty` is False → FAILED stage="DIRTY_CHECK", error_excerpt="uncommitted changes detected".
+
+**Execution sequence (inside `try`, lock released in `finally`):**
+
+For each stage, update `_deployment_jobs[deployment_id]["stage"]` under `_deployment_jobs_lock` before running the command.
+
+- If `pull` is True:
+  - Update stage → `"PULLING"`.
+  - `subprocess.run(["git", "pull", "--ff-only", "origin", default_branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`.
+  - Non-zero returncode → FAILED, `error_stage="PULLING"`, `error_excerpt=stderr[:500]`. Return.
+
+- For each `component` in `components` (in order; first failure stops the loop):
+  - `service = service_map[component]`.
+  - Update stage → `f"BUILDING_{component}"`.
+  - `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`.
+  - Non-zero returncode → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt=stderr[:500]`. Return.
+
+- Get deployed SHA: `subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10, capture_output=True, text=True)`.
+
+- Update job to SUCCEEDED: `deployed_sha`, `preview_url`, `result_message`, `completed_at`.
+
+Log each stage to `logger.info("redeploy %s: stage=%s", project_id, stage)`.
+
+`finally` block: `lock.release()`. Always executes on success, failure, timeout, and unexpected exception.
+
+#### j. New endpoint — `GET /workspace/projects/{project_id}/deployments/{deployment_id}`
+
+Returns current job state for polling:
+
+- 200: full `_deployment_jobs[deployment_id]` dict.
+- 404: deployment_id not found, or `project_id` mismatch.
+
+---
+
+### 3. `apps/dashboard/src/api/workspace.js`
+
+Add:
+
+```js
+export const getDeploymentStatus = (projectId, deploymentId) =>
+  api.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`);
+```
+
+---
+
+### 4. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`
+
+#### Extend `ActionConfirmCard`
+
+When `message.proposedAction?.capability === 'redeploy_project'`, render additional rows below the description:
+
+- **Project**: `message.proposedAction.safe_identifier`
+- **Branch**: `message.proposedAction.configured_branch`
+- **Pull**: Yes / No from `message.proposedAction.pull`
+- **Components**: comma-joined `message.proposedAction.components`
+- **Local changes**: warning badge when `message.proposedAction.has_dirty_warning === true`
+
+Do **not** display any host path. Use `safe_identifier` only.
+
+No changes to the Confirm button or the existing `confirmWorkspaceAction` API call.
+
+#### Background deployment polling in `handleConfirmAction`
+
+When the confirm response includes `deployment_id` (i.e. `res.data.deployment_id`):
+
+1. Update message state to `{ confirmed: false, deploymentId: res.data.deployment_id, deploymentStage: 'RUNNING' }`.
+2. Start a polling loop (`setTimeout` chain, interval ~2 s) calling `getDeploymentStatus(projectId, deploymentId)`.
+3. On each poll: update `deploymentStage` in message state.
+4. On `status === 'SUCCEEDED'`: set `confirmed: true`, `confirmResult` to success message including SHA and preview URL. Stop polling.
+5. On `status === 'FAILED'`: set `confirmError` to `${data.error_stage}: ${data.error_excerpt}`. Stop polling.
+6. Cap polling at 15 minutes; if exceeded, display "Deployment timed out — check supervisor logs."
+
+#### Render deployment progress in `ActionConfirmCard`
+
+When `message.deploymentId` is set and `message.confirmed` is false and no `confirmError`:
+- Show spinner with current stage label (e.g. "PULLING…", "BUILDING backend…").
+- Stage labels displayed: PULLING, BUILDING_backend, BUILDING_frontend, VERIFYING, SUCCEEDED, FAILED.
+
+---
+
+### 5. `tests/supervisor/test_workspace_redeploy.py` (new file)
+
+#### Config and helpers
+
+- `test_load_config_missing` — missing file → `{}`.
+- `test_load_config_valid` — valid YAML → parsed correctly.
+- `test_git_has_local_changes_clean` — empty porcelain → False.
+- `test_git_has_local_changes_dirty` — non-empty porcelain → True.
+- `test_git_has_local_changes_not_a_repo` — nonexistent path → raises.
+
+#### Proposal-time validation
+
+- `test_chat_unknown_project_returns_informational` — project not in config → intent=informational, no proposed_action.
+- `test_chat_unknown_component_rejected` — LLM requests component not in config → intent=informational.
+- `test_chat_branch_param_ignored` — LLM provides branch → stripped, configured branch used instead.
+- `test_chat_has_dirty_warning_propagated` — dirty repo → `has_dirty_warning=True` in proposed_action.
+
+#### Confirmation and lock
+
+- `test_confirm_starts_background_job` — confirm returns `{ok: true, deployment_id: ..., status: "RUNNING"}` immediately.
+- `test_confirm_concurrent_returns_409` — lock held → HTTP 409.
+- `test_confirm_unknown_action_id_returns_404` — forged action_id → 404.
+
+#### Background job execution
+
+- `test_job_branch_mismatch_rejected` — current branch ≠ configured → FAILED, no git pull or compose called.
+- `test_job_dirty_between_proposal_and_confirm` — repo clean at proposal, dirty at execution → FAILED.
+- `test_job_pull_failure_stops_early` — git pull fails → FAILED PULLING, no compose called.
+- `test_job_first_component_failure_stops_loop` — backend compose fails → FAILED, frontend compose not called.
+- `test_job_backend_only` — components=["backend"] → compose called once for backend service only.
+- `test_job_frontend_only` — components=["frontend"] → compose called once for frontend service only.
+- `test_job_success_returns_sha_and_url` — full success → status=SUCCEEDED, deployed_sha present, preview_url present.
+- `test_job_lock_released_after_failure` — command failure → lock released (can acquire again immediately).
+- `test_job_lock_released_after_exception` — unexpected exception in thread → lock released.
+- `test_job_git_timeout` — git pull exceeds timeout → FAILED PULLING, lock released.
+- `test_job_compose_timeout` — docker compose exceeds timeout → FAILED BUILDING, lock released.
+- `test_job_path_not_exist` — configured path missing → FAILED, no subprocess called.
+- `test_job_config_reloaded_at_execution` — stale repo_path in pending action not used; fresh config applied.
+- `test_job_stale_service_name_ignored` — tampered service name not executed; service from config used.
+
+#### Status polling endpoint
+
+- `test_get_deployment_status_running` — job in RUNNING state → 200 with stage.
+- `test_get_deployment_status_succeeded` — completed job → 200 with sha, preview_url.
+- `test_get_deployment_status_project_mismatch` — wrong project_id → 404.
+- `test_get_deployment_status_unknown` — unknown deployment_id → 404.
+
+#### Frontend tests (`apps/dashboard/src/components/ProjectWorkspacePanel.test.jsx` or similar)
+
+- `test_confirm_card_renders_redeploy_fields` — renders safe_identifier, configured_branch, pull, components.
+- `test_confirm_card_shows_dirty_warning` — `has_dirty_warning=true` → warning badge visible.
+- `test_confirm_card_no_host_path_displayed` — no element contains the literal `repository_path` value.
+- `test_confirm_submits_only_action_id` — Confirm click sends only `action_id` to `confirmWorkspaceAction`; no path/branch/service override.
+- `test_polling_shows_stage` — mock polling returns BUILDING_backend → spinner text updated.
+- `test_polling_stops_on_succeeded` — SUCCEEDED state → confirmed bubble shown, no further fetch.
+- `test_polling_stops_on_failed` — FAILED state → error shown, no further fetch.
+
+---
+
+### 6. `services/supervisor/workspace_projects.example.yml` (new file)
+
+An example/documentation config with the full schema annotated; never loaded by tests.
+
+---
+
+## Excluded
+
+- SSE or WebSocket streaming of deployment progress (polling via new GET endpoint is sufficient).
+- Rollback on failure.
+- Production or cloud deployment.
+- Multi-host orchestration.
+- Arbitrary remote shell access or LLM-composed commands.
+- Hot-reload of `workspace_projects.yml` without Supervisor restart.
+- Allowing the LLM or frontend to select a branch other than the configured default branch.
+- Deployment cancellation or timeout-triggered abort.
+- Redeploying a project other than the active workspace project via the chat context.
+
+## Acceptance criteria
+
+- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe. Requesting an unconfigured project returns `intent=informational` with a refusal explanation and no proposed_action.
+- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested Docker Compose services being rebuilt/restarted.
+- No `git pull`, `git branch`, or `docker compose` command runs before the user clicks Confirm.
+- The confirmation card displays: safe project identifier (not the host path), configured branch, pull flag, selected components, and a dirty-repo warning when applicable.
+- At execution time, the background job re-reads `workspace_projects.yml` and derives `repo_path`, `default_branch`, service names, `allow_dirty`, and `preview_url` from config — values from the pending action or frontend are never used for command construction.
+- The background job reads the current Git branch at execution time; if it differs from `default_branch`, the job fails with a branch-mismatch message before any Git or Docker command.
+- The background job re-checks `git status --porcelain` at execution time; if dirty and `allow_dirty: false`, the job fails before any Git or Docker command.
+- The `workspace_action_confirm()` endpoint returns HTTP 409 (not 500) when a deployment for the same project is already running.
+- The in-memory per-project lock is always released in a `finally` block, regardless of success, failure, timeout, or unexpected exception.
+- The `workspace_action_confirm()` endpoint returns within one second with `{ok: true, deployment_id: ..., status: "RUNNING"}`; the Supervisor remains responsive to other requests during deployment.
+- The frontend polls `GET /workspace/projects/{project_id}/deployments/{deployment_id}` and updates the chat bubble with the current stage, deployed SHA and preview URL on success, or failed stage and log excerpt on failure.
+- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
+- On failure, the chat bubble shows the failed stage and the first 500 characters of the relevant stderr.
+- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
+- All test cases in `test_workspace_redeploy.py` pass.
+- No frontend test can construct or submit an arbitrary `repo_path`, branch, service name, or shell command via the confirmation card.
+
+---
+
+## Review
+
+# PLAN_FIX_REQUIRED
+
+## Review
+
+Plan review 02 for T227.
+
+## Summary
+
+The regenerated plan resolves the first review's repository, branch, configuration, asynchronous execution, locking, and test-coverage requirements. Three integration and failure-state corrections remain required before implementation.
+
+## Required fixes
+
+### 1. Add the deployment-status proxy to the Control API
+
+The dashboard calls:
+
+```text
+GET /api/projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+and the Supervisor exposes:
+
+```text
+GET /workspace/projects/{project_id}/deployments/{deployment_id}
+```
+
+The regenerated plan must modify `services/control_api/routes/workspace.py` to add:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+This route must validate the project through the existing dependency and forward the GET request to the Supervisor while preserving its response status and JSON body.
+
+Without this proxy, frontend polling will return 404.
+
+### 2. Preserve HTTP 409 responses through the Control API
+
+The current Control API forwarding helper explicitly raises only for selected 4xx statuses and for 5xx responses. A Supervisor `409 Conflict` may therefore be returned by the Control API as HTTP 200 with a `detail` body.
+
+The plan must update the workspace proxy so every Supervisor response with `status_code >= 400` is propagated with the original status, including:
+
+- 409 when another deployment is already running;
+- 404 for an unknown deployment;
+- other validation or execution errors.
+
+Add a test proving that a Supervisor 409 remains a Control API 409.
+
+### 3. Guarantee a terminal job state on timeouts and exceptions
+
+Releasing the per-project lock in `finally` is necessary but insufficient. If `_run_redeploy_job` raises, the daemon thread may terminate while the job remains permanently `RUNNING`.
+
+The regenerated plan must define a top-level exception boundary around the complete background job and ensure all non-success paths write a terminal job state:
+
+- `status = "FAILED"`;
+- `completed_at` set;
+- `error_stage` set to the active stage or a safe internal stage;
+- `error_excerpt` set to a sanitized, bounded message;
+- lock released in `finally`.
+
+Handle at least:
+
+- `subprocess.TimeoutExpired`;
+- `FileNotFoundError`;
+- missing or invalid configuration;
+- missing repository path or non-Git repository;
+- unexpected exceptions.
+
+Add tests verifying both the released lock and the persisted `FAILED` state for timeout and unexpected-exception paths.
+
+## Preserved requirements
+
+The next plan must preserve all corrections already integrated from plan review 01:
+
+- fresh dirty check after confirmation;
+- configured-branch enforcement;
+- no LLM/frontend-controlled executable branch, path, service, or command;
+- background deployment job and polling;
+- safe project identifier in the confirmation card;
+- HTTP 409 for concurrent deployment;
+- unconditional lock release;
+- backend and frontend security/concurrency tests.
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+---
+
+## Instructions de fix
+
+# Plan fix 02
+
+## Ticket
+
+T227 — Add pull and local backend/frontend redeployment action to AI Workspace
+
+## Source review
+
+`runs/T227/reviews/plan-review-02.md`
+
+## Decision
+
+PLAN_FIX_REQUIRED
+
+## Required plan corrections
+
+### 1. Add the Control API polling route
+
+Modify `services/control_api/routes/workspace.py` to expose:
+
+```text
+GET /projects/{project_id}/workspace/deployments/{deployment_id}
+```
+
+The route must:
+
+- use the existing project-resolution dependency;
+- forward to Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
+- preserve the Supervisor HTTP status and JSON response;
+- return 404 for an unknown deployment or project mismatch.
+
+Update `apps/dashboard/src/api/workspace.js` to call this Control API route consistently.
+
+### 2. Propagate every Supervisor error status, including 409
+
+Update the workspace proxy forwarding logic so any Supervisor response with `status_code >= 400` is returned or raised with the original HTTP status.
+
+In particular, concurrent redeployment must remain:
+
+```text
+409 Conflict
+```
+
+from Supervisor through Control API to the dashboard. It must not become HTTP 200 with a `detail` field.
+
+Add Control API tests for:
+
+- Supervisor 409 → Control API 409;
+- Supervisor 404 → Control API 404;
+- successful polling response → Control API 200 with unchanged job state.
+
+### 3. Persist FAILED for every background-job failure
+
+Wrap the complete `_run_redeploy_job` body with a top-level exception boundary.
+
+For every timeout, configuration failure, filesystem/Git error, missing executable, or unexpected exception, update the deployment job under `_deployment_jobs_lock` with:
+
+```python
+{
+    "status": "FAILED",
+    "completed_at": <utc timestamp>,
+    "error_stage": <current or safe failure stage>,
+    "error_excerpt": <sanitized message, maximum 500 characters>,
+}
+```
+
+Requirements:
+
+- never leave a terminated job in `RUNNING`;
+- handle `subprocess.TimeoutExpired` explicitly;
+- handle `FileNotFoundError` explicitly;
+- handle invalid/missing project configuration;
+- handle missing or non-Git repository paths;
+- catch unexpected exceptions, log the full server-side exception, and expose only a sanitized bounded excerpt;
+- release the project lock unconditionally in `finally`.
+
+Add tests proving that:
+
+- Git timeout produces `FAILED` and releases the lock;
+- Docker timeout produces `FAILED` and releases the lock;
+- unexpected exception produces `FAILED` and releases the lock;
+- missing executable produces `FAILED`;
+- frontend polling stops on each resulting `FAILED` response.
+
+## Requirements to preserve
+
+Do not regress the corrections already present in the current plan:
+
+- execution-time configuration reload;
+- configured branch only;
+- execution-time branch and dirty checks;
+- safe pending-action metadata;
+- background job returning immediately;
+- per-project conflict locking;
+- no host paths in the UI;
+- frontend submits only the opaque `action_id`;
+- existing capability behavior remains unchanged.
+
+## Expected output
+
+Regenerate `runs/T227/plan.md` with these correct

… truncated 108848 chars from pr diff (conflict context size guard) …

```

---

## Ticket branch diff since merge-base (bf5a0605)

(no source paths — only runtime/noise diffs against main)

---

## Conflicted Files

### tests/test_conflict_resolver.py

```
"""Tests for T143 — conflict detection and CONFLICT_RESOLUTION_* states."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_ticket import VALID_STATES, TRANSITIONS
from run_daemon import (
    AUTO_RUNNABLE_STATES,
    HUMAN_GATE_STATES,
    _load_state_json,
    _save_state_json,
    detect_pr_conflict,
)


# ── VALID_STATES ──────────────────────────────────────────────────────────────

def test_conflict_resolution_needed_in_valid_states():
    assert "CONFLICT_RESOLUTION_NEEDED" in VALID_STATES


def test_conflict_resolution_failed_in_valid_states():
    assert "CONFLICT_RESOLUTION_FAILED" in VALID_STATES


def test_conflict_resolving_in_valid_states():
    assert "CONFLICT_RESOLVING" in VALID_STATES


def test_conflict_resolved_review_needed_in_valid_states():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" in VALID_STATES


# ── AUTO_RUNNABLE_STATES ──────────────────────────────────────────────────────

def test_conflict_resolution_needed_not_auto_runnable():
    assert "CONFLICT_RESOLUTION_NEEDED" not in AUTO_RUNNABLE_STATES


def test_conflict_resolution_failed_not_auto_runnable():
    assert "CONFLICT_RESOLUTION_FAILED" not in AUTO_RUNNABLE_STATES


def test_conflict_resolving_not_auto_runnable():
    assert "CONFLICT_RESOLVING" not in AUTO_RUNNABLE_STATES


def test_conflict_resolved_review_needed_not_auto_runnable():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" not in AUTO_RUNNABLE_STATES


# ── HUMAN_GATE_STATES ─────────────────────────────────────────────────────────

def test_conflict_resolution_needed_in_human_gate():
    assert "CONFLICT_RESOLUTION_NEEDED" in HUMAN_GATE_STATES


def test_conflict_resolution_failed_in_human_gate():
    assert "CONFLICT_RESOLUTION_FAILED" in HUMAN_GATE_STATES


def test_conflict_resolved_review_needed_in_human_gate():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" in HUMAN_GATE_STATES


# ── TRANSITIONS ───────────────────────────────────────────────────────────────

def test_conflict_resolution_failed_is_terminal():
    assert "CONFLICT_RESOLUTION_FAILED" not in TRANSITIONS


def test_conflict_resolution_needed_is_not_in_transitions():
    assert "CONFLICT_RESOLUTION_NEEDED" not in TRANSITIONS


# ── detect_pr_conflict — gh returns CONFLICTING ───────────────────────────────

def _make_run_dir(tmp_path: Path, ticket_id: str = "T001", **extra) -> Path:
    run_dir = tmp_path / ticket_id
    run_dir.mkdir(parents=True)
    state = {"ticket_id": ticket_id, "state": "IMPLEMENTATION_REVIEW_NEEDED", "pr_number": 42, **extra}
    (run_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return run_dir


def _mock_gh_conflicting(files=None):
    files = files or [{"path": "src/foo.py"}, {"path": "src/bar.py"}]
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "CONFLICTING"}))
    files_response = MagicMock(returncode=0, stdout=json.dumps({"files": files}))
    return [mergeable_response, files_response]


def test_detect_pr_conflict_returns_true_on_conflicting(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting()):
        result = detect_pr_conflict("T001", 42, run_dir, repo=None)
    assert result is True


def test_detect_pr_conflict_writes_metadata_to_state_json(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting()):
        detect_pr_conflict("T001", 42, run_dir, repo=None)
    data = _load_state_json(run_dir)
    assert data["state"] == "CONFLICT_RESOLUTION_NEEDED"
    assert data["pre_conflict_state"] == "IMPLEMENTATION_REVIEW_NEEDED"
    assert data["conflict_pr_number"] == 42
    assert "conflict_detected_at" in data
    assert isinstance(data["conflicted_files"], list)


def test_detect_pr_conflict_captures_file_list(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    files = [{"path": "tools/foo.py"}, {"path": "services/bar.py"}]
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting(files)):
        detect_pr_conflict("T001", 42, run_dir)
    data = _load_state_json(run_dir)
    assert "tools/foo.py" in data["conflicted_files"]
    assert "services/bar.py" in data["conflicted_files"]


# ── detect_pr_conflict — gh returns non-conflicting ──────────────────────────

def test_detect_pr_conflict_returns_false_when_mergeable(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "MERGEABLE"}))
    with patch("run_daemon.subprocess.run", return_value=mergeable_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_does_not_modify_state_when_not_conflicting(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    original = _load_state_json(run_dir)
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "MERGEABLE"}))
    with patch("run_daemon.subprocess.run", return_value=mergeable_response):
        detect_pr_conflict("T001", 42, run_dir)
    data = _load_state_json(run_dir)
    assert data["state"] == original["state"]


# ── detect_pr_conflict — gh failure ──────────────────────────────────────────

def test_detect_pr_conflict_returns_false_on_gh_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    error_response = MagicMock(returncode=1, stdout="", stderr="Not found")
    with patch("run_daemon.subprocess.run", return_value=error_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_returns_false_when_gh_missing(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=FileNotFoundError):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_returns_false_on_invalid_json(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    bad_response = MagicMock(returncode=0, stdout="not-json")
    with patch("run_daemon.subprocess.run", return_value=bad_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


# ── TicketSummary — conflict fields serialised ────────────────────────────────

def test_ticket_summary_serialises_conflict_fields():
    from services.control_api.models.schemas import TicketSummary

    ts = TicketSummary(
        ticket_id="T001",
        state="CONFLICT_RESOLUTION_NEEDED",
        conflict_status="CONFLICT_RESOLUTION_NEEDED",
        conflicted_files=["src/foo.py"],
        conflict_detected_at="2026-05-23T12:00:00Z",
        pre_conflict_state="PLAN_APPROVED",
    )
    d = ts.model_dump()
    assert d["conflict_status"] == "CONFLICT_RESOLUTION_NEEDED"
    assert d["conflicted_files"] == ["src/foo.py"]
    assert d["conflict_detected_at"] == "2026-05-23T12:00:00Z"
    assert d["pre_conflict_state"] == "PLAN_APPROVED"


def test_ticket_summary_conflict_fields_default_to_none():
    from services.control_api.models.schemas import TicketSummary

    ts = TicketSummary(ticket_id="T001", state="PLAN_APPROVED")
    assert ts.conflict_status is None
    assert ts.conflicted_files is None
    assert ts.conflict_detected_at is None
    assert ts.pre_conflict_state is None
    assert ts.conflict_error is None


def test_get_ticket_exposes_conflict_error_from_error_log(isolated_tmp):
    from fastapi.testclient import TestClient

    run_dir = _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_FAILED")
    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True)
    (conflict_dir / "error.log").write_text(
        "[2026-07-03T14:32:34Z] failed to prepare clean tree before rebase\n",
        encoding="utf-8",
    )
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] == "CONFLICT_RESOLUTION_FAILED"
    assert "failed to prepare clean tree" in body["conflict_error"]


# ── GET /tickets/{id} returns conflict fields ─────────────────────────────────

def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path)


def _make_ticket(tmp_path: Path, ticket_id: str, state: str, **extra) -> Path:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    data = {"ticket_id": ticket_id, "state": state, **extra}
    (run_dir / "state.json").write_text(json.dumps(data), encoding="utf-8")
    return run_dir


@pytest.fixture()
def isolated_tmp(tmp_path, monkeypatch):
    """tmp_path with AI_DEV_FACTORY_RUNTIME_ROOT cleared so resolve_runs_dir uses tmp_path."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    return tmp_path


def test_get_ticket_exposes_conflict_fields(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(
        isolated_tmp, "T001", "CONFLICT_RESOLUTION_NEEDED",
        pre_conflict_state="PLAN_APPROVED",
        conflict_detected_at="2026-05-23T10:00:00Z",
        conflict_pr_number=7,
        conflicted_files=["a.py", "b.py"],
    )
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] == "CONFLICT_RESOLUTION_NEEDED"
    assert body["pre_conflict_state"] == "PLAN_APPROVED"
    assert body["conflict_detected_at"] == "2026-05-23T10:00:00Z"
    assert body["conflicted_files"] == ["a.py", "b.py"]


def test_get_ticket_conflict_fields_null_when_no_conflict(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] is None
    assert body["conflicted_files"] is None


# ── POST /mark-conflict-failed ────────────────────────────────────────────────

def test_mark_conflict_failed_transitions_state(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_NEEDED",
                 pre_conflict_state="PLAN_APPROVED",
                 conflict_detected_at="2026-05-23T10:00:00Z",
                 conflicted_files=[])
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    state_file = isolated_tmp / "runs" / "T001" / "state.json"
    data = json.loads(state_file.read_text())
    assert data["state"] == "CONFLICT_RESOLUTION_FAILED"


def test_mark_conflict_failed_returns_409_from_wrong_state(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 409


def test_mark_conflict_failed_returns_409_from_conflict_resolution_failed(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_FAILED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 409


def test_mark_conflict_failed_returns_404_on_unknown_ticket(isolated_tmp):
    from fastapi.testclient import TestClient

    (isolated_tmp / "runs").mkdir(parents=True)
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T999/mark-conflict-failed")
    assert r.status_code == 404


# ── CONFLICT_RESOLUTION_FAILED is terminal ────────────────────────────────────

def test_conflict_resolution_failed_has_no_outgoing_transitions():
    assert TRANSITIONS.get("CONFLICT_RESOLUTION_FAILED", "NOT_PRESENT") == "NOT_PRESENT"


# ── resolve_conflicts — multi-pass and max-pass tests ─────────────────────────

import run_conflict_resolver as _rcr  # noqa: E402  (after sys.path setup above)


def _make_resolver_fixture(tmp_path: Path, ticket_id: str = "T001") -> tuple[Path, Path]:
    """Return (run_dir, context_path) after creating the minimum fixture."""
    branch = "ticket/test-branch"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    state = {"ticket_id": ticket_id, "state": "CONFLICT_RESOLVING", "branch": branch}
    (run_dir / "state.json").write_text(json.dumps(state, indent=2))

    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir()
    context_path = conflict_dir / "context.md"
    context_path.write_text("# context\n")

    prompt_dir = tmp_path / "prompts" / "generic"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "conflict-resolver.md").write_text("# Resolve\n")

    return run_dir, context_path


def _git_ok(stdout: str = "") -> MagicMock:
    return MagicMock(returncode=0, stdout=stdout, stderr="")


def _git_fail(stderr: str = "error", stdout: str = "") -> MagicMock:
    return MagicMock(returncode=1, stdout=stdout, stderr=stderr)


def test_resolve_conflicts_multi_pass_success(tmp_path, monkeypatch):
    """Two-pass scenario: pass 1 leaves one file conflicted, pass 2 clears all.

    Expected: state → CONFLICT_RESOLVED_REVIEW_NEEDED, return 0.
    """
    ticket_id = "T001"
    run_dir, context_path = _make_resolver_fixture(tmp_path, ticket_id)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(_rcr, "collect_context", MagicMock(return_value=context_path))
    monkeypatch.setattr(_rcr, "execute_external_command", MagicMock(return_value=("ok", "", 0)))
    monkeypatch.setattr(_rcr, "compose_runtime_prompt", MagicMock(return_value="prompt"))
    monkeypatch.setattr(_rcr, "_run_tests", MagicMock(return_value="Exit code: 0\n"))
    monkeypatch.setattr(_rcr, "_prepare_clean_tree_for_rebase", lambda _tid: True)
    monkeypatch.setattr(_rcr, "_scrub_runtime_noise_before_rebase", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_purge_oversized_runtime_artifacts", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_unstage_noise_paths", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_rebase_in_progress", lambda: False)
    advance_seq = iter([
        ["file_a.py", "file_b.py"],
        ["file_b.py"],
        [],
    ])
    monkeypatch.setattr(
        _rcr,
        "_advance_past_runtime_conflicts",
        lambda *args, **kwargs: next(advance_seq, []),
    )
    monkeypatch.setattr(
        _rcr,
        "_run_rebase_continue",
        lambda _tid: MagicMock(returncode=0, stdout="", stderr=""),
    )

    subprocess_calls = [
        # _get_current_branch
        _git_ok("ticket/test-branch\n"),
        # git fetch origin
        _git_ok(),
        # git rebase origin/main → conflict
        _git_fail("CONFLICT"),
        # _list_conflicted_files (initial)
        _git_ok("file_a.py\nfile_b.py\n"),
        # Pass 1: git add -- file_a.py file_b.py
        _git_ok(),
        # Pass 2: git add -- file_b.py
        _git_ok(),
        # git add -A (artifacts)
        _git_ok(),
        # git commit
        _git_ok("[branch abc1234]"),
        # git rev-parse --short HEAD
        _git_ok("abc1234"),
        # git push --force-with-lease
        _git_ok(),
    ]

    with patch("run_conflict_resolver.subprocess.run", side_effect=subprocess_calls):
        rc = _rcr.resolve_conflicts(ticket_id, exec_cmd="dummy")

    assert rc == 0
    state = json.loads((run_dir / "state.json").read_text())
    assert state["state"] == "CONFLICT_RESOLVED_REVIEW_NEEDED"


def test_resolve_conflicts_max_pass_failure(tmp_path, monkeypatch):
    """All passes leave conflicts unresolved.

    Expected: git rebase --abort called, state → CONFLICT_RESOLUTION_FAILED, return 2.
    """
    ticket_id = "T001"
    run_dir, context_path = _make_resolver_fixture(tmp_path, ticket_id)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(_rcr, "collect_context", MagicMock(return_value=context_path))
    monkeypatch.setattr(_rcr, "execute_external_command", MagicMock(return_value=("ok", "", 0)))
    monkeypatch.setattr(_rcr, "compose_runtime_prompt", MagicMock(return_value="prompt"))
    monkeypatch.setattr(_rcr, "_prepare_clean_tree_for_rebase", lambda _tid: True)
    monkeypatch.setattr(_rcr, "_scrub_runtime_noise_before_rebase", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_purge_oversized_runtime_artifacts", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_unstage_noise_paths", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_rebase_in_progress", lambda: False)
    monkeypatch.setattr(
        _rcr,
        "_advance_past_runtime_conflicts",
        lambda *args, **kwargs: ["file_a.py"],
    )
    monkeypatch.setattr(
        _rcr,
        "_run_rebase_continue",
        lambda _tid: MagicMock(returncode=1, stdout="", stderr="CONFLICT"),
    )

    max_passes = _rcr.MAX_RESOLVER_PASSES

    subprocess_calls = [
        # _get_current_branch
        _git_ok("ticket/test-branch\n"),
        # git fetch origin
        _git_ok(),
        # git rebase origin/main → conflict
        _git_fail("CONFLICT"),
        # _list_conflicted_files (initial)
        _git_ok("file_a.py\n"),
    ]
    for _ in range(max_passes):
        subprocess_calls += [
            # git add -- file_a.py
            _git_ok(),
            # git rebase --continue → conflict persists
            _git_fail("CONFLICT"),
            # _list_conflicted_files → still conflicted
            _git_ok("file_a.py\n"),
        ]
    # git rebase --abort
    subprocess_calls.append(_git_ok())

    abort_calls: list[list[str]] = []

    original_run = _rcr._run_git

    def _tracking_run_git(args: list[str]) -> MagicMock:
        if args == ["rebase", "--abort"]:
            abort_calls.append(args)
        return original_run(args)

    with patch("run_conflict_resolver.subprocess.run", side_effect=subprocess_calls):
        monkeypatch.setattr(_rcr, "_run_git", _tracking_run_git)
        rc = _rcr.resolve_conflicts(ticket_id, exec_cmd="dummy")

    assert rc == 2
    state = json.loads((run_dir / "state.json").read_text())
    assert state["state"] == "CONFLICT_RESOLUTION_FAILED"
    assert len(abort_calls) >= 1, "git rebase --abort must be called on max-pass failure"


def test_blocking_dirty_paths_ignores_runtime_noise():
    import run_conflict_resolver as rcr

    porcelain = "\n".join([
        " M runs/T010/runtime.log",
        " M runs/T010/daemon.lock",
        "?? runs/T010/conflict/error.log",
        "?? runs/T010/prompts/conflict-resolver-attempt-1.md",
        " M README.md",
    ])
    assert rcr._blocking_dirty_paths(porcelain, "T010") == ["README.md"]


def test_split_conflicts_separates_runtime_paths():
    import run_conflict_resolver as rcr

    files = [
        "README.md",
        "runs/T010/state.json",
        "runs/T010/plan.md",
        "docs/architecture.md",
    ]
    source, runtime = rcr._split_conflicts("T010", files)
    assert source == ["README.md", "docs/architecture.md"]
    assert runtime == ["runs/T010/state.json", "runs/T010/plan.md"]


def test_split_conflicts_treats_foreign_runs_and_node_modules_as_runtime():
    import run_conflict_resolver as rcr

    files = [
        "frontend/src/App.tsx",
        "runs/T011/conflict/context.md",
        "runs/T014/prompts/conflict-resolver-attempt-1.md",
        "runs/T025/state.json",
        "frontend/node_modules/lru-cache/package.json",
        "node_modules/.package-lock.json",
        "backend/target/surefire-reports/TEST-Foo.xml",
        "frontend/dist/index.html",
    ]
    source, runtime = rcr._split_conflicts("T025", files)
    assert source == ["frontend/src/App.tsx"]
    assert runtime == [
        "runs/T011/conflict/context.md",
        "runs/T014/prompts/conflict-resolver-attempt-1.md",
        "runs/T025/state.json",
        "frontend/node_modules/lru-cache/package.json",
        "node_modules/.package-lock.json",
        "backend/target/surefire-reports/TEST-Foo.xml",
        "frontend/dist/index.html",
    ]


def test_auto_resolve_runtime_keeps_own_ticket_takes_upstream_for_foreign(
    monkeypatch,
):
    import run_conflict_resolver as rcr

    calls: list[list[str]] = []

    def _fake_git(args):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    rcr._auto_resolve_runtime_conflicts(
        "T025",
        [
            "runs/T025/state.json",
            "runs/T011/conflict/context.md",
            "frontend/node_modules/foo/package.json",
        ],
    )
    assert ["checkout", "--theirs", "--", "runs/T025/state.json"] in calls
    assert ["checkout", "--ours", "--", "runs/T011/conflict/context.md"] in calls
    assert ["checkout", "--ours", "--", "frontend/node_modules/foo/package.json"] in calls


def test_blocking_dirty_paths_ignores_foreign_runs_and_node_modules():
    import run_conflict_resolver as rcr

    porcelain = "\n".join([
        " M runs/T011/state.json",
        " M frontend/node_modules/lru-cache/package.json",
        " M frontend/src/App.tsx",
        " M runs/T025/runtime.log",
    ])
    assert rcr._blocking_dirty_paths(porcelain, "T025") == ["frontend/src/App.tsx"]


def test_scrub_ticket_runtime_dir_resets_whole_runtime_prefix(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    calls: list[list[str]] = []

    def _fake_git(args):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    rcr._scrub_ticket_runtime_dir("T010")
    assert ["checkout", "HEAD", "--", "runs/T010/"] in calls
    assert ["clean", "-fd", "--", "runs/T010"] in calls


def test_prepare_clean_tree_for_rebase_fails_when_runtime_still_dirty(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)

    def _fake_git(args):
        if args[:3] == ["status", "--porcelain", "--"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=" M runs/T010/state.json\n", stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is False


def test_prepare_clean_tree_tolerates_retry_state_json(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)

    def _fake_git(args):
        if args[:3] == ["status", "--porcelain", "--"]:
            return subprocess.CompletedProcess(
                args, 0, stdout="?? runs/T010/retry-state.json\n", stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is True


def test_advance_past_runtime_retries_when_continue_hits_target_conflicts(
    tmp_path, monkeypatch,
):
    """rebase --continue that only conflicts on build artifacts must not abort."""
    import run_conflict_resolver as rcr

    run_dir = tmp_path / "runs" / "T025"
    run_dir.mkdir(parents=True)
    data: dict = {}
    calls = {"list": 0, "continue": 0, "auto": 0}
    pending_target = ["backend/target/surefire-reports/x.xml"]

    def _fake_list():
        calls["list"] += 1
        if calls["auto"] == 0 and calls["continue"] >= 1:
            return list(pending_target)
        return []

    def _fake_continue(_tid):
        calls["continue"] += 1
        if calls["continue"] == 1:
            return subprocess.CompletedProcess(
                ["git", "rebase", "--continue"],
                1,
                stdout="",
                stderr="CONFLICT (content): Merge conflict in backend/target/x\n",
            )
        return subprocess.CompletedProcess(
            ["git", "rebase", "--continue"], 0, stdout="", stderr="",
        )

    def _fake_auto(_tid, paths):
        calls["auto"] += 1
        assert paths == pending_target
        pending_target.clear()

    rebase_alive = {"v": True}

    def _fake_rebase_in_progress():
        return rebase_alive["v"]

    def _fake_continue_and_maybe_done(_tid):
        result = _fake_continue(_tid)
        if result.returncode == 0:
            rebase_alive["v"] = False
        return result

    monkeypatch.setattr(rcr, "_list_conflicted_files", _fake_list)
    monkeypatch.setattr(rcr, "_effective_source_conflicts", lambda _tid: [])
    monkeypatch.setattr(rcr, "_rebase_in_progress", _fake_rebase_in_progress)
    monkeypatch.setattr(rcr, "_run_rebase_continue", _fake_continue_and_maybe_done)
    monkeypatch.setattr(rcr, "_auto_resolve_runtime_conflicts", _fake_auto)
    monkeypatch.setattr(rcr, "_log", lambda *_a, **_k: None)
    monkeypatch.setattr(rcr, "_write_error_log", lambda *_a, **_k: None)
    monkeypatch.setattr(rcr, "_persist_conflict_state", lambda *_a, **_k: None)

    result = rcr._advance_past_runtime_conflicts("T025", run_dir, data)
    assert result == []
    assert calls["auto"] >= 1
    assert calls["continue"] >= 1


def test_conflict_resolution_eligible_from_git_conflicts(tmp_path):
    import subprocess as sp
    from conflict_resolution_eligibility import conflict_resolution_eligible, git_conflicted_files

    wt = tmp_path / "wt"
    wt.mkdir()
    sp.run(["git", "init"], cwd=wt, capture_output=True, check=True)
    sp.run(["git", "config", "user.email", "t@test"], cwd=wt, capture_output=True)
    sp.run(["git", "config", "user.name", "t"], cwd=wt, capture_output=True)
    (wt / "f.txt").write_text("<<<<<<< ours\na\n=======\nb\n>>>>>>> theirs\n")
    sp.run(["git", "add", "f.txt"], cwd=wt, capture_output=True)
    sp.run(["git", "commit", "-m", "c"], cwd=wt, capture_output=True)

    state = {"state": "IMPLEMENTATION_REVIEW_NEEDED"}
    assert conflict_resolution_eligible(state, wt) is False
    assert git_conflicted_files(wt) == []
```

### tools/agent_runner/run_conflict_resolver.py

```
#!/usr/bin/env python3
"""Conflict resolver executor for ai-dev-factory.

Runs inside the ticket worktree:
1. Fetches origin and rebases onto the integration branch (``main`` by default).
2. On rebase conflict: collects context, invokes AI agent to edit files.
3. Loops until all conflicts cleared or MAX_RESOLVER_PASSES reached.
4. Stages only conflicted files per pass.
5. Runs tests.
6. Commits artifacts with message conflict(T{id}): resolve conflicts against <base>.
7. Pushes with --force-with-lease.
8. Transitions state to CONFLICT_RESOLVED_REVIEW_NEEDED (success)
   or CONFLICT_RESOLUTION_FAILED (any failure).
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

MAX_RESOLVER_PASSES = int(os.environ.get("CONFLICT_RESOLVER_MAX_PASSES", "3"))

_CONFLICT_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})

ROOT = Path(__file__).resolve().parent
_RUN_STEP_PATH = ROOT / "run_step.py"
_CONTEXT_COLLECTOR_PATH = ROOT / "conflict_context_collector.py"

_tpl_spec = importlib.util.spec_from_file_location(
    "_ticket_pr_lifecycle_cr", ROOT / "ticket_pr_lifecycle.py",
)
_tpl_mod = importlib.util.module_from_spec(_tpl_spec)  # type: ignore[arg-type]
_tpl_spec.loader.exec_module(_tpl_mod)  # type: ignore[union-attr]
resolve_integration_branch = _tpl_mod.resolve_integration_branch
rebase_onto_ref = _tpl_mod.rebase_onto_ref
ensure_pr_base_branch = _tpl_mod.ensure_pr_base_branch
del _tpl_spec, _tpl_mod

_rs_spec = importlib.util.spec_from_file_location("_run_step", _RUN_STEP_PATH)
_rs_mod = importlib.util.module_from_spec(_rs_spec)  # type: ignore[arg-type]
_rs_spec.loader.exec_module(_rs_mod)  # type: ignore[union-attr]
execute_external_command = _rs_mod.execute_external_command
compose_runtime_prompt = _rs_mod.compose_runtime_prompt
del _rs_spec, _rs_mod

_cc_spec = importlib.util.spec_from_file_location("_cc", _CONTEXT_COLLECTOR_PATH)
_cc_mod = importlib.util.module_from_spec(_cc_spec)  # type: ignore[arg-type]
_cc_spec.loader.exec_module(_cc_mod)  # type: ignore[union-attr]
collect_context = _cc_mod.collect_context
del _cc_spec, _cc_mod

_rc_spec = importlib.util.spec_from_file_location("_runtime_checkpoint", ROOT / "runtime_checkpoint.py")
_rc_mod = importlib.util.module_from_spec(_rc_spec)  # type: ignore[arg-type]
_rc_spec.loader.exec_module(_rc_mod)  # type: ignore[union-attr]
is_ignorable_runtime_dirty_path = _rc_mod.is_ignorable_runtime_dirty_path
parse_porcelain_paths = _rc_mod.parse_porcelain_paths
del _rc_spec, _rc_mod


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(ticket_id: str, message: str) -> None:
    log_path = Path("runs") / ticket_id / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] conflict-resolver: {message}\n")


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        args, text=True, capture_output=True, check=False, cwd=cwd, env=env
    )


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return _run(["git"] + args)


def _write_state(run_dir: Path, data: dict) -> None:
    data["updated_at"] = _now_iso()
    state_file = run_dir / "state.json"
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(state_file)


def _transition_state(
    ticket_id: str,
    run_dir: Path,
    new_state: str,
    *,
    backup: dict | None = None,
    conflicted_files: list[str] | None = None,
) -> None:
    """Transition workflow state, restoring conflict metadata when ``backup`` is set.

    During rebase, tracked ``runs/{ticket}/state.json`` can rewind to an older
    commit — pass the resolver's in-memory snapshot so ``pre_conflict_state`` survives.
    """
    if backup is not None:
        files = conflicted_files
        if files is None:
            raw = backup.get("conflicted_files")
            files = list(raw) if isinstance(raw, list) else []
        _persist_conflict_state(run_dir, backup, new_state, files)
        _log(ticket_id, f"state → {new_state}")
        return
    state_file = run_dir / "state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["state"] = new_state
    _write_state(run_dir, data)
    _log(ticket_id, f"state → {new_state}")


def _persist_conflict_state(
    run_dir: Path,
    backup: dict,
    new_state: str,
    conflicted_files: list[str],
) -> None:
    """Restore conflict metadata after rebase rewinds tracked ``state.json``."""
    ticket_id = backup.get("ticket_id") or run_dir.name
    prefix = _runtime_path_prefix(ticket_id)
    source_files = [f for f in conflicted_files if not f.startswith(prefix)]
    data = dict(backup)
    pre = data.get("pre_conflict_state") or backup.get("state", "")
    if pre in _CONFLICT_STATES:
        pre = backup.get("pre_conflict_state") or "IMPLEMENTATION_REVIEW_NEEDED"
    data["pre_conflict_state"] = pre
    data["state"] = new_state
    data["conflicted_files"] = source_files
    if not data.get("conflict_detected_at"):
        data["conflict_detected_at"] = _now_iso()
    _write_state(run_dir, data)


def _ensure_conflict_dir(run_dir: Path) -> Path:
    """``git clean`` may remove ``runs/{ticket}/conflict/`` mid-run — recreate it."""
    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    return conflict_dir


def _write_error_log(run_dir: Path, message: str, stderr: str = "") -> None:
    conflict_dir = _ensure_conflict_dir(run_dir)
    error_path = conflict_dir / "error.log"
    content = f"[{_now_iso()}] {message}\n"
    if stderr.strip():
        content += f"\n--- stderr ---\n{stderr.strip()}\n"
    with error_path.open("a", encoding="utf-8") as fh:
        fh.write(content)


def _normalize_branch(name: str) -> str:
    if name.startswith("refs/heads/"):
        return name[len("refs/heads/"):]
    return name


def _rebase_head_branch() -> str | None:
    result = _run_git(["rev-parse", "--git-path", "rebase-merge/head-name"])
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    return _normalize_branch(raw) if raw else None


def _get_current_branch() -> str:
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("failed to determine current git branch")
    branch = _normalize_branch(result.stdout.strip())
    if branch == "HEAD":
        rebase_branch = _rebase_head_branch()
        if rebase_branch:
            return rebase_branch
    return branch


def _list_conflicted_files() -> list[str]:
    result = _run_git(["diff", "--name-only", "--diff-filter=U"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _runtime_path_prefix(ticket_id: str) -> str:
    return f"runs/{ticket_id}/"


def _is_runtime_artifact_path(path: str, ticket_id: str | None = None) -> bool:
    """True for workflow ``runs/``, deps, and build trees — never AI-merge these.

    Other tickets' ``runs/TXXX/`` often land on ``main`` via merged PRs. When this
    ticket rebases, those paths conflict, but they are not this ticket's source
    code and must not be handed to the conflict-resolver agent. Same for
    ``node_modules`` and Maven/Gradle ``target/`` / ``build/`` output that
    sometimes gets committed by accident.
    """
    _ = ticket_id
    if not path:
        return False
    if path.startswith("./"):
        path = path[2:]
    if path == "runs" or path.startswith("runs/"):
        return True
    if path == "node_modules" or path.startswith("node_modules/"):
        return True
    if "/node_modules/" in path or path.endswith("/node_modules"):
        return True
    # Build / dependency / bytecode output — never resolve via the agent.
    parts = path.split("/")
    if "target" in parts or "build" in parts or "dist" in parts:
        return True
    if "__pycache__" in parts or path.endswith((".pyc", ".class")):
        return True
    if path == ".venv" or path.startswith(".venv/") or "/.venv/" in path:
        return True
    return False


def _split_conflicts(ticket_id: str, files: list[str]) -> tuple[list[str], list[str]]:
    source = [f for f in files if not _is_runtime_artifact_path(f, ticket_id)]
    runtime = [f for f in files if _is_runtime_artifact_path(f, ticket_id)]
    return source, runtime


def _has_conflict_markers(path: str) -> bool:
    try:
        return "<<<<<<< " in Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _scan_source_marker_conflicts(ticket_id: str) -> list[str]:
    """Return source paths that still contain conflict markers on disk."""
    found: list[str] = []
    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue
        rel = path.as_posix()
        if rel.startswith(".git/") or _is_runtime_artifact_path(rel, ticket_id):
            continue
        if _has_conflict_markers(rel):
            found.append(rel)
    return sorted(found)


def _effective_source_conflicts(ticket_id: str) -> list[str]:
    """Merge git unmerged paths with on-disk marker scan (source files only)."""
    unmerged = _list_conflicted_files()
    source, runtime = _split_conflicts(ticket_id, unmerged)
    marker_paths = _scan_source_marker_conflicts(ticket_id)
    merged: list[str] = []
    seen: set[str] = set()
    for path in source + marker_paths:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return merged


def _abort_rebase(ticket_id: str) -> None:
    _log(ticket_id, "aborting rebase")
    _run_git(["rebase", "--abort"])


def _run_tests(ticket_id: str, run_dir: Path) -> str:
    """Run pytest and return output text for the test report."""
    tests_dir = Path("tests")
    if not tests_dir.exists():
        return "No tests/ directory found — skipped.\n"

    result = _run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
    )
    if result.returncode == 5:
        return (
            f"# Test Report — conflict resolution for {ticket_id}\n"
            f"Generated at: {_now_iso()}\n"
            "Exit code: 0\n\n"
            "No pytest tests collected — skipped.\n"
        )
    lines = [
        f"# Test Report — conflict resolution for {ticket_id}",
        f"Generated at: {_now_iso()}",
        f"Exit code: {result.returncode}",
        "",
        "## Output",
        "",
        result.stdout or "(no stdout)",
    ]
    if result.stderr.strip():
        lines += ["", "## Stderr", "", result.stderr.strip()]

    return "\n".join(lines) + "\n"


def _blocking_dirty_paths(porcelain: str, ticket_id: str) -> list[str]:
    """Return dirty paths that should block rebase (real source edits only)."""
    blocking: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().split(" -> ")[-1]
        if _is_runtime_artifact_path(path, ticket_id):
            continue
        if is_ignorable_runtime_dirty_path(path):
            continue
        blocking.append(path)
    return blocking


def _runtime_tree_porcelain(ticket_id: str) -> str:
    prefix = _runtime_path_prefix(ticket_id)
    result = _run_git(["status", "--porcelain", "--", prefix])
    if result.returncode != 0:
        return "<git status failed>"
    return result.stdout


def _scrub_ticket_runtime_dir(ticket_id: str) -> None:
    """Reset tracked runtime artifacts and drop *all* untracked files under
    ``runs/{ticket}/`` so they cannot block ``git rebase`` / ``--continue``.

    Live workflow state is held in-memory (``state_backup``) and rewritten after
    each transition — leaving an untracked ``state.json`` on disk will make
    later commits that recreate ``runs/{ticket}/`` fail with "would be
    overwritten by merge".
    """
    import shutil

    prefix = _runtime_path_prefix(ticket_id)
    _run_git(["checkout", "HEAD", "--", prefix])
    # Wipe untracked scratch under this ticket's runs tree entirely.
    _run_git(["clean", "-fd", "--", prefix.rstrip("/")])
    untracked = _run_git(["ls-files", "--others", "--exclude-standard", prefix])
    if untracked.returncode == 0:
        for rel in untracked.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            path = Path(rel)
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    _run_git(["checkout", "HEAD", "--", prefix])


def _try_resume_clean_rebase(ticket_id: str, run_dir: Path) -> bool:
    """If rebase is stuck with no unmerged paths, scrub noise and continue.

    Returns True when the rebase finished or advanced to real conflicts.
    """
    if not _rebase_in_progress():
        return False
    if _list_conflicted_files():
        return False
    _log(ticket_id, "rebase stuck with no unmerged files — scrubbing and continuing")
    _scrub_ticket_runtime_dir(ticket_id)
    cont = _run_rebase_continue(ticket_id)
    if cont.returncode == 0:
        return True
    out_lower = (cont.stdout + cont.stderr).lower()
    if "nothing to commit" in out_lower or "no changes" in out_lower:
        _run_git(["rebase", "--skip"])
        return True
    if _list_conflicted_files():
        return True
    detail = "\n".join(
        x for x in (cont.stdout.strip(), cont.stderr.strip()) if x
    ) or "<no output>"
    _write_error_log(run_dir, f"stuck rebase --continue failed: {detail}")
    return False


def _blocking_runtime_dirty(porcelain: str) -> list[str]:
    """Return non-ignorable dirty paths under ``runs/{ticket}/``."""
    return [
        path
        for path in parse_porcelain_paths(porcelain)
        if not is_ignorable_runtime_dirty_path(path)
    ]


def _rebase_in_progress() -> bool:
    for subpath in ("rebase-merge", "rebase-apply"):
        result = _run_git(["rev-parse", "--git-path", subpath])
        if result.returncode != 0:
            continue
        if Path(result.stdout.strip()).exists():
            return True
    return False


def _prepare_clean_tree_for_rebase(ticket_id: str) -> bool:
    """Ensure the worktree is clean enough for ``git rebase``.

    The in-memory ``state.json`` backup lives outside git — reset the tracked
    ``runs/{ticket}/`` tree so ``runtime.log``, deleted locks, and workflow
    state edits do not block the rebase.
    """
    _scrub_ticket_runtime_dir(ticket_id)

    runtime_dirty = _runtime_tree_porcelain(ticket_id).strip()
    blocking_runtime = _blocking_runtime_dirty(runtime_dirty) if runtime_dirty else []
    if blocking_runtime:
        _log(
            ticket_id,
            f"runtime tree still dirty after scrub: {', '.join(blocking_runtime)}",
        )
        return False

    remaining = _run_git(["status", "--porcelain"])
    if remaining.returncode != 0:
        return False
    blocking = _blocking_dirty_paths(remaining.stdout, ticket_id)
    if blocking:
        _log(ticket_id, f"blocking dirty paths before rebase: {blocking}")
        return False
    return True


def _auto_resolve_runtime_conflicts(ticket_id: str, paths: list[str]) -> None:
    """Auto-stage runtime/artifact conflicts without invoking the AI agent.

    During rebase, ``--theirs`` is the commit being replayed (ticket branch) and
    ``--ours`` is upstream. Keep this ticket's own ``runs/{ticket}/`` from the
    ticket branch; for every other runtime/build noise path (foreign ``runs/``,
    ``node_modules``, ``target/``, …), take upstream so the agent never merges them.
    """
    own_prefix = _runtime_path_prefix(ticket_id)
    for path in paths:
        keep_ticket = path.startswith(own_prefix)
        # Rebase inverts merge semantics: --theirs = replayed commit.
        preferred = "--theirs" if keep_ticket else "--ours"
        fallback = "--ours" if keep_ticket else "--theirs"
        result = _run_git(["checkout", preferred, "--", path])
        if result.returncode != 0:
            _run_git(["checkout", fallback, "--", path])
        _run_git(["add", "--", path])


# GitHub rejects blobs over 100 MB; keep a safer ceiling for runtime artifacts.
_MAX_COMMIT_ARTIFACT_BYTES = 5 * 1024 * 1024


def _purge_oversized_runtime_artifacts(ticket_id: str) -> None:
    """Delete oversized conflict dumps so they cannot be committed/pushed."""
    root = Path("runs") / ticket_id
    for path in list(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size <= _MAX_COMMIT_ARTIFACT_BYTES:
            continue
        rel = path.as_posix()
        _log(ticket_id, f"purging oversized runtime artifact ({size} bytes): {rel}")
        path.unlink(missing_ok=True)
        _run_git(["rm", "-f", "--ignore-unmatch", "--", rel])


def _unstage_noise_paths(ticket_id: str) -> None:
    """Keep foreign ``runs/`` and node_modules out of the resolution commit."""
    staged = _run_git(["diff", "--cached", "--name-only"])
    if staged.returncode != 0:
        return
    own_prefix = _runtime_path_prefix(ticket_id)
    drop: list[str] = []
    for path in staged.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if _is_runtime_artifact_path(path, ticket_id) and not path.startswith(own_prefix):
            drop.append(path)
            continue
        if path.startswith(own_prefix):
            try:
                if Path(path).is_file() and Path(path).stat().st_size > _MAX_COMMIT_ARTIFACT_BYTES:
                    drop.append(path)
            except OSError:
                pass
    if drop:
        _log(ticket_id, f"unstaging noise paths from resolution commit: {drop[:20]}")
        _run_git(["reset", "HEAD", "--", *drop])


def _scrub_before_rebase_continue(ticket_id: str) -> None:
    """Drop unstaged runtime noise so ``git rebase --continue`` is not blocked."""
    _scrub_ticket_runtime_dir(ticket_id)


def _run_rebase_continue(ticket_id: str) -> subprocess.CompletedProcess[str]:
    _scrub_before_rebase_continue(ticket_id)
    env = dict(os.environ)
    env["GIT_EDITOR"] = "true"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        ["git", "rebase", "--continue"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _advance_past_runtime_conflicts(
    ticket_id: str,
    run_dir: Path,
    data: dict,
    *,
    max_steps: int = 128,
) -> list[str] | None:
    """Auto-resolve runtime/build conflicts and continue until source conflicts.

    Each ``git rebase --continue`` can surface a new wave of foreign ``runs/``,
    ``node_modules``, or ``target/`` conflicts on later commits. Those must be
    auto-resolved in-loop — never treated as a hard failure.
    """
    for step in range(max_steps):
        raw = _list_conflicted_files()
        source = _effective_source_conflicts(ticket_id)
        _, runtime = _split_conflicts(ticket_id, raw)

        if runtime:
            _log(ticket_id, f"auto-resolving runtime path conflicts: {runtime}")
            _auto_resolve_runtime_conflicts(ticket_id, runtime)

        if source:
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", source)
            return source

        if not _rebase_in_progress():
            return []

        if raw:
            # Runtime-only unmerged paths were resolved; re-check before continue.
            continue

        cont = _run_rebase_continue(ticket_id)
        if cont.returncode == 0:
            continue

        out_lower = (cont.stdout + cont.stderr).lower()
        if "nothing to commit" in out_lower or "no changes" in out_lower:
            _run_git(["rebase", "--skip"])
            continue

        # Untracked runs/{ticket}/ (e.g. live state.json) blocks applying a
        # commit that recreates those paths — scrub and retry once.
        if "untracked working tree files would be overwritten" in out_lower:
            _log(ticket_id, "rebase --continue blocked by untracked runtime files; scrubbing")
            _scrub_ticket_runtime_dir(ticket_id)
            cont = _run_rebase_continue(ticket_id)
            if cont.returncode == 0:
                continue
            out_lower = (cont.stdout + cont.stderr).lower()
            if "nothing to commit" in out_lower or "no changes" in out_lower:
                _run_git(["rebase", "--skip"])
                continue

        source = _effective_source_conflicts(ticket_id)
        if source:
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", source)
            return source

        # Continue failed because the next commit only conflicts on runtime/build
        # noise — loop so the next iteration auto-resolves and continues.
        raw_after = _list_conflicted_files()
        _, runtime_after = _split_conflicts(ticket_id, raw_after)
        if runtime_after:
            _log(
                ticket_id,
                f"rebase --continue hit runtime-only conflicts; continuing auto-resolve "
                f"({len(runtime_after)} paths)",
            )
            continue

        if raw_after:
            # Unmerged paths that somehow aren't classified — still try once more
            # after re-split rather than aborting immediately.
            _log(ticket_id, f"rebase --continue left unclassified conflicts: {raw_after}")
            continue

        detail = "\n".join(
            x for x in (cont.stdout.strip(), cont.stderr.strip()) if x
        ) or "<no output>"
        _write_error_log(run_dir, f"rebase --continue failed (runtime step {step + 1}): {detail}")
        return None

    _write_error_log(run_dir, f"exceeded {max_steps} runtime conflict advance steps")
    return None


def _scrub_runtime_noise_before_rebase(ticket_id: str) -> None:
    """Drop volatile runtime paths immediately before ``git rebase``."""
    _scrub_ticket_runtime_dir(ticket_id)


def resolve_conflicts(ticket_id: str, exec_cmd: str) -> int:
    run_dir = Path("runs") / ticket_id
    state_file = run_dir / "state.json"

    if not state_file.exists():
        print(f"error: state.json not found for {ticket_id}", file=sys.stderr)
        return 2

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"error: state.json unreadable: {exc}", file=sys.stderr)
        return 2

    branch = data.get("branch", "")
    state_backup = dict(data)
    _log(ticket_id, f"start branch={branch}")

    # Safety guard: never run on main
    try:
        current_branch = _get_current_branch()
    except RuntimeError as exc:
        _log(ticket_id, f"failed to read branch: {exc}")
        _write_error_log(run_dir, str(exc))
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    if current_branch == "main":
        msg = "safety: refusing to resolve conflicts on 'main' branch"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # Verify branch matches state
    if branch and _normalize_branch(current_branch) != _normalize_branch(branch):
        msg = f"branch mismatch: current={current_branch!r} state={branch!r}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    conflict_dir = _ensure_conflict_dir(run_dir)

    # 1. fetch origin
    _log(ticket_id, "git fetch origin")
    fetch = _run_git(["fetch", "origin"])
    if fetch.returncode != 0:
        msg = f"git fetch failed: {fetch.stderr.strip()}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg, fetch.stderr)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # 2. git rebase onto the integration branch (or resume an in-progress rebase)
    integration_branch = resolve_integration_branch(ticket_id, run_dir)
    rebase_ref = rebase_onto_ref(integration_branch)
    rebase_had_conflicts = False
    if _rebase_in_progress():
        conflicted_files = _list_conflicted_files()
        if conflicted_files:
            _log(ticket_id, f"resuming in-progress rebase conflicts: {conflicted_files}")
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
            rebase_had_conflicts = True
        elif _try_resume_clean_rebase(ticket_id, run_dir):
            _log(ticket_id, "resumed stuck rebase after scrub")
            # Fall through: either done or new conflicts — re-check below via
            # _advance_past_runtime_conflicts / conflicted_files listing.
            conflicted_files = _list_conflicted_files()
            if conflicted_files:
                _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
                rebase_had_conflicts = True
            elif _rebase_in_progress():
                # Still rebasing — let the advance loop finish it.
                rebase_had_conflicts = True
            else:
                rebase_had_conflicts = False
        else:
            msg = "rebase in progress but no unmerged files found"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2
    else:
        if not _prepare_clean_tree_for_rebase(ticket_id):
            remaining = _run_git(["status", "--porcelain"])
            if remaining.returncode != 0:
                blocking = ["<git status failed>"]
            else:
                blocking = _blocking_dirty_paths(remaining.stdout, ticket_id)
                if not blocking:
                    # Own-ticket runtime dirt that survived scrub (reported separately).
                    blocking = _blocking_runtime_dirty(
                        _runtime_tree_porcelain(ticket_id),
                    ) or ["<unknown dirty tree after scrub>"]
            msg = (
                "failed to prepare clean tree before rebase"
                f" — blocking paths: {blocking}"
            )
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2

        _scrub_runtime_noise_before_rebase(ticket_id)
        rebase = _run_git(["rebase", rebase_ref])
        _log(ticket_id, f"git rebase {rebase_ref} exit={rebase.returncode}")

        if rebase.returncode != 0:
            conflicted_files = _list_conflicted_files()
            if not conflicted_files:
                msg = f"rebase failed with no conflict markers: {rebase.stderr.strip()}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, rebase.stderr)
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            _log(ticket_id, f"conflicts detected: {conflicted_files}")
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
            rebase_had_conflicts = True

    if rebase_had_conflicts:
        conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
        if conflicted_files is None:
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2
        if not conflicted_files:
            rebase_had_conflicts = False

    if rebase_had_conflicts:
        prompt_path = Path("prompts") / "generic" / "conflict-resolver.md"
        if not prompt_path.exists():
            msg = f"prompt not found: {prompt_path}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2

        pass_count = 0
        while conflicted_files and pass_count < MAX_RESOLVER_PASSES:
            pass_count += 1
            pass_conflicted = list(conflicted_files)
            _log(ticket_id, f"[pass {pass_count}/{MAX_RESOLVER_PASSES}] start conflicted={pass_conflicted}")

            # Collect context after conflict markers exist on disk
            try:
                context_path = collect_context(ticket_id, conflicted_files=pass_conflicted)
                _log(ticket_id, f"context written: {context_path}")
            except Exception as exc:
                _log(ticket_id, f"context collection failed pass {pass_count}: {exc}")
                _write_error_log(run_dir, f"context collection failed: {exc}")
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            context_content = context_path.read_text(encoding="utf-8")
            task_content = prompt_path.read_text(encoding="utf-8") + "\n\n" + context_content
            runtime_prompt = compose_runtime_prompt(ticket_id, "conflict-resolver", task_content)

            # Snapshot the prompt
            prompts_dir = run_dir / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            existing = list(prompts_dir.glob("conflict-resolver-attempt-*.md"))
            attempt_num = len(existing) + 1
            snapshot = prompts_dir / f"conflict-resolver-attempt-{attempt_num}.md"
            snapshot.write_text(runtime_prompt, encoding="utf-8")
            _log(ticket_id, f"prompt snapshot: {snapshot}")

            _log(ticket_id, f"invoking AI resolver pass {pass_count}")
            stdout, stderr_ai, rc = execute_external_command(exec_cmd, runtime_prompt)

            if rc != 0:
                detail = (stdout or stderr_ai or "").strip()
                msg = f"AI resolver failed (rc={rc}) pass {pass_count}"
                if detail:
                    msg = f"{msg}: {detail[:800]}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, stderr_ai)
                (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")

            # Check which files still have markers after AI edit (before staging)
            still_unresolved_markers = [f for f in pass_conflicted if _has_conflict_markers(f)]
            if still_unresolved_markers:
                msg = (
                    f"AI resolver pass {pass_count} finished but conflict markers remain in:"
                    f" {still_unresolved_markers}"
                )
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, stderr_ai)
                conflicted_files = still_unresolved_markers
                continue

            # Stage only the conflicted files (not git add -A)
            staged = list(pass_conflicted)
            add = _run_git(["add", "--"] + staged)
            if add.returncode != 0:
                msg = f"git add failed: {add.stderr.strip()}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, add.stderr)
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            # git rebase --continue
            continue_result = _run_rebase_continue(ticket_id)
            continue_rc = continue_result.returncode

            if continue_rc != 0:
                out_lower = (continue_result.stdout + continue_result.stderr).lower()
                if "nothing to commit" in out_lower or "no changes" in out_lower:
                    _run_git(["rebase", "--skip"])
                    _log(ticket_id, "rebase --skip (nothing to commit)")
                    conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                    if conflicted_files is None:
                        _abort_rebase(ticket_id)
                        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                        return 2
                    continue
                else:
                    new_conflicted = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                    if new_conflicted is None:
                        _abort_rebase(ticket_id)
                        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                        return 2
                    # [] means runtime-only conflicts were cleared and the rebase
                    # finished (or has no further source conflicts). Do NOT treat
                    # that as a hard failure — the previous continue_rc!=0 was
                    # expected when the next commit only conflicted on noise.
                    _log(ticket_id, (
                        f"[pass {pass_count}/{MAX_RESOLVER_PASSES}]"
                        f" conflicted={pass_conflicted}"
                        f" | staged={staged}"
                        f" | unresolved={still_unresolved_markers}"
                        f" | continue_rc={continue_rc}"
                        f" | next_source={new_conflicted}"
                    ))
                    conflicted_files = new_conflicted
                    continue
            else:
                # Successful continue — check for conflicts from the next commit
                conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                if conflicted_files is None:
                    _abort_rebase(ticket_id)
                    _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                    return 2

            _log(ticket_id, (
                f"[pass {pass_count}/{MAX_RESOLVER_PASSES}]"
                f" conflicted={pass_conflicted}"
                f" | staged={staged}"
                f" | unresolved={still_unresolved_markers}"
                f" | continue_rc={continue_rc}"
            ))

        if conflicted_files:
            msg = (
                f"conflicts remain after {pass_count}/{MAX_RESOLVER_PASSES} passes:"
                f" {conflicted_files}"
            )
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2

        _log(ticket_id, f"all conflicts resolved after {pass_count} pass(es)")

    else:
        # Clean rebase — write resolution.md noting no conflicts needed
        conflict_dir = _ensure_conflict_dir(run_dir)
        res_path = conflict_dir / "resolution.md"
        if not res_path.exists():
            res_path.write_text(
                f"# Resolution — {ticket_id}\n\n"
                f"Rebase onto {rebase_ref} completed with no conflicts.\n"
                f"Generated at: {_now_iso()}\n",
                encoding="utf-8",
            )
        _log(ticket_id, "rebase clean — no conflicts")

    # 3. run tests
    conflict_dir = _ensure_conflict_dir(run_dir)
    _log(ticket_id, "running tests")
    test_report = _run_tests(ticket_id, run_dir)
    test_report_path = conflict_dir / "test-report.md"
    test_report_path.write_text(test_report, encoding="utf-8")
    _log(ticket_id, f"test-report written: {test_report_path}")

    if "Exit code: 0" not in test_report and "skipped" not in test_report.lower():
        msg = "tests failed after conflict resolution"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # 4. commit resolution artifacts — never push runtime noise or oversized blobs
    _log(ticket_id, "staging and committing resolution artifacts")
    _purge_oversized_runtime_artifacts(ticket_id)
    add_all = _run_git(["add", "-A"])
    if add_all.returncode != 0:
        _log(ticket_id, f"git add before commit failed: {add_all.stderr.strip()}")
    _unstage_noise_paths(ticket_id)

    commit_msg = f"conflict({ticket_id}): resolve conflicts against {integration_branch}"
    commit = _run_git(["commit", "-m", commit_msg])
    if commit.returncode != 0:
        out = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in out:
            _log(ticket_id, "nothing to commit after resolution")
        else:
            msg = f"commit failed: {commit.stderr.strip()}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg, commit.stderr)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2
    else:
        sha_result = _run_git(["rev-parse", "--short", "HEAD"])
        sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown"
        _log(ticket_id, f"commit: sha={sha}")

    # 5. push with --force-with-lease
    push_target = branch or current_branch
    _log(ticket_id, f"git push --force-with-lease origin {push_target}")
    push = _run_git(["push", "--force-with-lease", "origin", push_target])
    if push.returncode != 0:
        msg = f"push --force-with-lease failed: {push.stderr.strip()}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg, push.stderr)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    _log(ticket_id, "push succeeded")
    ensure_pr_base_branch(ticket_id, run_dir, None)

    # 6. transition after clean rebase + passing tests
    _transition_state(
        ticket_id, run_dir, "CONFLICT_RESOLVED_REVIEW_NEEDED", backup=state_backup,
    )
    try:
        from conflict_resolution_eligibility import reset_conflict_resolution_auto_retry

        reset_conflict_resolution_auto_retry(run_dir)
    except Exception as exc:
        _log(ticket_id, f"clear conflict retry state: skipped — {exc}")
    try:
        state_after = json.loads(state_file.read_text(encoding="utf-8"))
        rt_path = ROOT / "run_ticket.py"
        spec = importlib.util.spec_from_file_location("_run_ticket_finalize", rt_path)
        rt_mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(rt_mod)  # type: ignore[union-attr]
        final_state = rt_mod._maybe_auto_finalize_conflict_resolution(
            ticket_id, state_after,
        )
    except Exception as exc:
        _log(ticket_id, f"auto-finalize-conflict: skipped — {exc}")
        final_state = None

    if final_state:
        _log(ticket_id, f"done → {final_state} (auto-finalize)")
    else:
        _log(ticket_id, "done → CONFLICT_RESOLVED_REVIEW_NEEDED")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conflict resolver executor")
    parser.add_argument("ticket_id")
    parser.add_argument("--exec-cmd", required=True, help="AI runtime command")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    run_dir = Path("runs") / args.ticket_id
    try:
        return resolve_conflicts(args.ticket_id, args.exec_cmd)
    except Exception as exc:
        if run_dir.joinpath("state.json").is_file():
            _write_error_log(run_dir, f"uncaught resolver error: {exc}")
            try:
                _transition_state(args.ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            except Exception:
                pass
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```