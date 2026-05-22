I have read all the relevant files. Here is the full implementation review.

---

# PR Review — T139 Runtime Dashboard

## Résumé

Implémentation d'un dashboard runtime de type read-only avec cleanup sécurisé. 7 endpoints FastAPI, 8 composants React, 20 tests pytest et 9 tests Vitest. Le périmètre respecte le plan V1 réduit approuvé après la review plan.

## Vérifications effectuées

- Backend : `services/control_api/routes/runtime_dashboard.py` (320 lignes)
- Enregistrement router dans `services/control_api/main.py`
- Frontend : `RuntimeDashboardPage.jsx`, `SandboxRunsTable.jsx`, `ProposalRunsTable.jsx`, `RuntimeHealthPanel.jsx`, `LogViewerDrawer.jsx`, `ProposalSummaryModal.jsx`, `ConfirmDialog.jsx`
- API client : `apps/dashboard/src/api/runtimeDashboard.js`
- Route dans `App.jsx`
- Hook `usePolling.js`
- Pytest : `tests/test_runtime_dashboard_api.py` (20 cas)
- Vitest : `apps/dashboard/tests/RuntimeDashboardPage.test.jsx` (9 cas)

## Points validés

**Critères d'acceptance ticket :**
- Sandbox runs listés avec tous les champs requis (`id`, `status`, `started_at`, `worktree_path`, `ports`) ✅
- Proposal runs listés avec les champs requis ✅
- Logs accessibles depuis l'UI avec polling incrémental via `offset` ✅
- Santé runtime visible (supervisor, active_jobs, stale_pid_files, stale_locks) ✅
- `DELETE /sandbox-runs/{id}` retourne 409 si statut actif OU si `daemon.lock` tient un PID vivant ✅
- `DELETE /proposal-runs/{id}` retourne 409 si statut actif ✅
- Boutons Delete désactivés (`disabled`) côté UI pour les statuts `running`/`creating`/`active` ✅
- Drawer log ouvre, auto-scroll, poll toutes les 2s, s'arrête à la fermeture (cleanup `clearInterval` dans `usePolling`) ✅
- Aucune assumption projet-spécifique : lecture générique de `state.json` avec clés alternatives (`state`/`status`, `project_id`/`ticket_id`) ✅

**Sécurité :**
- Validation `re.fullmatch(r"[a-zA-Z0-9_\-]+", ...)` sur `sandbox_id` et `proposal_id` avant construction de path → traversal impossible ✅
- `pathlib.Path` pour construction des chemins, jamais de concaténation string ✅
- Safety check double (statut ET PID liveness via `os.kill(pid, 0)`) sur DELETE sandbox ✅
- Les paths `runs/` et `sandboxes/` en tant que répertoires racines ne sont jamais supprimés (seuls des sous-répertoires directs) ✅

**Conformité plan :**
- Rerun et stop sandbox : non implémentés ✅ (exclus V1)
- Cleanup global stale worktrees/dirs/orphans : non implémentés ✅ (exclus V1)
- Pas de WebSocket/SSE : polling 2s/5s ✅

**Tests :**
- Couverture pytest : vide/présent, 404, 204, 409 sur statut actif, 409 sur PID vivant, 204 sur PID stale, health keys, stale lock détecté, live lock compté comme actif, stale pid détecté ✅
- Couverture Vitest : 4 sections, empty state, delete disabled/enabled, dialog confirm, log drawer, modal proposal, health panel ✅

## Problèmes détectés

**Non-bloquants :**

1. **Import mort `urllib.error` (ligne 18)** — `import urllib.error  # noqa: F401 (kept for clarity)` : ce module n'est jamais utilisé dans le fichier. Le commentaire et le `noqa` masquent le linting. Doit être retiré.

2. **`ACTIVE_STATUSES` incohérent entre les deux tables frontend** — `SandboxRunsTable.jsx` inclut `'creating'` dans le set, `ProposalRunsTable.jsx` ne l'inclut pas. Si un proposal en statut `creating` existe, son bouton Delete sera activé côté UI alors que le backend le rejetterait en 409. Risque faible (statut inhabituel pour les proposals) mais incohérent.

3. **`shutil.rmtree(..., ignore_errors=True)` retourne 204 même en cas d'échec partiel** — Si la suppression échoue silencieusement (droits insuffisants, fichier verrouillé), le client reçoit quand même un 204. Pour un dashboard opérationnel V1, c'est tolérable, mais une vérification post-suppression ou la propagation de l'erreur serait plus correcte.

## Risques éventuels

- **`_check_supervisor_status` synchrone** : `urllib.request.urlopen` est bloquant. FastAPI exécute les routes sync dans un thread pool, ce qui est correct. Sous forte charge, cela pourrait épuiser les threads. Acceptable pour V1 avec faible trafic.
- **Offset log en caractères Python** : `len(tail)` compte des caractères Unicode, pas des octets. Cohérent si `read_text` est toujours utilisé côté backend. Aucun problème tant que le client renvoie les offsets reçus.

## Décision

APPROVED — les 3 observations sont non-bloquantes et n'affectent pas la correction, la sécurité ou les critères d'acceptance. L'import mort et l'inconsistance `ACTIVE_STATUSES` peuvent être nettoyés dans un ticket de polish ultérieur.

## Actions demandées

Aucune action bloquante. Suggestions pour un ticket de polish :
- Retirer `import urllib.error` ligne 18 de `runtime_dashboard.py`
- Aligner `ACTIVE_STATUSES` dans `ProposalRunsTable.jsx` avec `SandboxRunsTable.jsx` (ajouter `'creating'`)

---

IMPLEMENTATION_APPROVED
