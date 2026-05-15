I have everything I need. Writing the review now.

---

# PR Review — T101 Runtime Hardening (Review 2)

## Résumé

Cette deuxième review fait suite au `IMPLEMENTATION_FIX_REQUIRED` de la review 1, qui avait identifié un seul problème bloquant : `_checkpoint_and_push_before_pr` retournait `None` et ne bloquait pas la création de PR en cas d'échec. Le coder a apporté la correction demandée. L'implémentation est désormais complète et correcte sur les 5 bugs du ticket.

---

## Vérifications effectuées

- Lecture de `services/control_api/services/artifact_reader.py` (timeline mapping, `_STATUS_MAP`, `_STEP_AGENTS`, `_build_steps`)
- Lecture de `tools/agent_runner/run_daemon.py` (dirty tree, ticket id, PR lifecycle, `AUTO_RUNNABLE_STATES`, `HUMAN_GATE_STATES`)
- Lecture de `.gitignore` complet
- Lecture de `tests/test_daemon_pr_lifecycle.py` (fix + test ajouté)
- Exécution des 4 suites de tests (`test_ticket_timeline`, `test_daemon_issue_polling`, `test_daemon_checkpoint`, `test_daemon_pr_lifecycle`) : **102 passed, 0 failed**
- Vérification de la cohérence entre `artifact_reader.py` et les constantes du daemon (`AUTO_RUNNABLE_STATES`, `HUMAN_GATE_STATES`)

---

## Correction du problème bloquant (Bug 4)

**`run_daemon.py:539-577`** — Le fix est correct et minimal.

`_checkpoint_and_push_before_pr` retourne désormais `bool` :
- `False` si `git commit` échoue (rc ∉ {0, 1})
- `False` si `git push` échoue (rc ≠ 0)
- `True` si push réussit ou s'il n'y avait rien à committer (rc == 1, skip push)

`handle_test_complete` conditionne maintenant `create_or_update_pr` et `check_and_close_issue` au retour de `_checkpoint_and_push_before_pr`. Si `False`, les deux sont sautées et le daemon loggue "pre-PR push failed — PR skipped". Le daemon repassera au prochain cycle tant que l'état reste `TEST_COMPLETE`.

Le test `test_handle_test_complete_skips_pr_when_push_fails` (`test_daemon_pr_lifecycle.py:197-204`) vérifie bien que `create_or_update_pr` et `check_and_close_issue` ne sont **pas** appelées quand `_checkpoint_and_push_before_pr` retourne `False`. Le critère d'acceptation "PR créée uniquement après push stable" est maintenant satisfait.

---

## État des 5 bugs — validation finale

### Bug 1 — Timeline mapping ✓

`artifact_reader.py:139-156` : tous les états mappés correctement.

| État | `human_gate` | step status | agent | Cohérence daemon |
|------|-------------|-------------|-------|-----------------|
| `PLAN_REVIEW_NEEDED` | `True` | `waiting_human` | — | `HUMAN_GATE_STATES` ✓ |
| `IMPLEMENTATION_REVIEW_NEEDED` | `False` | `running` | `reviewer` | `AUTO_RUNNABLE_STATES` ✓ |
| `IMPLEMENTATION_FIX_REQUIRED` | `False` | `running` (fix_loop) | `coder` | `AUTO_RUNNABLE_STATES` ✓ |
| `IMPLEMENTATION_APPROVED` | `False` | `running` (tests) | `tester` | `AUTO_RUNNABLE_STATES` ✓ |
| `TEST_COMPLETE` | `True` | `done` | — | `HUMAN_GATE_STATES` ✓ |

Aucune duplication de state machine. La timeline reste une projection pure de `state.json`.

### Bug 2 — Allocation ticket id ✓

`run_daemon.py:690-701` : parsing numérique via `re.match(r"T(\d+)$")` + `int()`. Format zero-padé `f"T{max_num + 1:03d}"`. Tous les cas du ticket sont couverts par les tests (T034→T035, T099→T100, T001/T010/T100→T101, gaps).

### Bug 3 — Dirty tree classification ✓

`run_daemon.py:235-331` : 3-bucket classification correcte. `_CODE_SCOPE_PREFIXES` couvre les fichiers des répertoires `services/` et `apps/` modifiés durant T100. Les inconnus bloquent toujours. Aucun `git add .`.

### Bug 4 — Checkpoint/push avant PR ✓ (corrigé dans ce cycle)

Voir section ci-dessus.

### Bug 5 — .gitignore ✓

`.gitignore` contient toutes les entrées demandées par le ticket : `runs/daemon.pid`, `runs/daemon.log`, `runs/*/daemon.lock`, `runs/*/workflow-status.md`, `apps/dashboard/node_modules/`, plus les `.tmp` et `retry-state` ajoutés. Aucun fichier runtime ne pollue Git.

---

## Observations mineures (non bloquantes)

**`_CODE_SCOPE_PREFIXES` duplique `COMMIT_SCOPE`** (`run_daemon.py:236`) : le commentaire "Mirrors COMMIT_SCOPE in run_ticket.py" documente le couplage. Acceptable pour ce ticket, mais si `run_ticket.py` évolue, le daemon devra être mis à jour manuellement. À surveiller.

**`IMPLEMENTATION_APPROVED` affiche fix_loop comme "skipped"** même si un cycle `IMPLEMENTATION_FIX_REQUIRED` s'est produit. L'état `IMPLEMENTATION_APPROVED` est transitoire (auto-runnable, transition immédiate vers tester), impact cosmétique seulement.

**`_classify_dirty_files` silencieux si `git status` échoue** (`run_daemon.py:267-268`) : retourne trois listes vides → daemon continue. Cas extrêmement rare (git indisponible). Comportement acceptable.

---

## Critères d'acceptation — vérification finale

| Critère | Statut |
|---------|--------|
| `IMPLEMENTATION_REVIEW_NEEDED` n'est plus affiché comme pause humaine | ✅ |
| Prochain ticket après T034 est T035, pas T100 | ✅ |
| Fichiers code dans `COMMIT_SCOPE` auto-checkpointés | ✅ |
| Vrais fichiers inconnus continuent à bloquer | ✅ |
| `TEST_COMPLETE` déclenche checkpoint/push avant PR | ✅ |
| PR créée/updated uniquement après push stable | ✅ |
| Fichiers runtime ne polluent plus Git | ✅ |
| Aucun `git add .` | ✅ |

---

## Tests

102 tests passent sur les 4 suites concernées. Le cas push-fail → PR skippée est couvert. Aucune régression détectée.

---

IMPLEMENTATION_APPROVED
