Le plan est écrit dans `runs/T018/plan.md`. Voici le résumé :

---

**Analyse de l'existant**

- `run_step.py` est le seul niveau avec accès aux stdout/stderr bruts du LLM via `execute_external_command()` — c'est le bon endroit pour la classification primaire.
- `run_ticket.py` loggue déjà `"step=X failed rc=Y"` mais sans qualifier le type d'échec.
- Les deux fichiers partagent le même `runtime.log`.
- L'invariant `state unchanged on failure` est déjà respecté (ligne 640 de `run_ticket.py`).

**Ce que le plan propose**

**Étape 1** — Ajouter `classify_runtime_failure(return_code, stdout, stderr) -> str` dans `run_step.py`, avec 7 catégories ordonnées par priorité : `quota_exceeded`, `write_permission_missing`, `provider_error`, `process_crashed`, `empty_output`, `process_failed`, `unknown`. Les patterns sont des constantes de module (`_QUOTA_PATTERNS`, etc.).

**Étape 2** — Appeler cette fonction dans `run_step.py` après `execute_external_command()` : log `"runtime failure: X"` sur rc != 0, warnings non-bloquants sur rc=0 avec output vide ou patterns de permission.

**Étape 3** — Importer `classify_runtime_failure` dans `run_ticket.py` (via le bloc importlib existant) et l'appeler dans `_call_run_step()` pour enrichir le log au niveau workflow.

**Étape 4** — Nouveau fichier `tests/test_runtime_failure_detection.py` avec ~11 tests couvrant chaque catégorie, les priorités, et l'invariant `state unchanged`.

**Décisions structurantes**

- Pas d'artefact dédié `runtime-failures/` — les entrées `runtime.log` suffisent et restent bornées.
- `write_permission_missing` avec rc=0 → warning non-bloquant (faux positifs possibles, workflow continue).
- Pas de détection "no filesystem changes" pour le coder — trop complexe, hors scope.
