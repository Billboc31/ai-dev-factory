# PR Review — T101 Runtime Hardening

## Résumé

Implémentation solide qui corrige 4 des 5 bugs décrits dans le ticket. Les fixes pour le mapping timeline, l'allocation numérique des ticket ids, la classification dirty tree, et le nettoyage .gitignore sont corrects et bien testés (101 tests). Un problème bloquant est détecté sur le Bug 4 (checkpoint/push avant PR) : la fonction `_checkpoint_and_push_before_pr` est non-bloquante, ce qui viole directement le critère d'acceptation "la PR est créée/updated uniquement après push stable".

---

## Vérifications effectuées

- Lecture complète de `services/control_api/services/artifact_reader.py` (timeline mapping)
- Lecture complète de `tools/agent_runner/run_daemon.py` (dirty tree, ticket id, PR lifecycle)
- Lecture de `.gitignore` et diff vs main
- Lecture de tous les fichiers de tests : `test_ticket_timeline.py`, `test_daemon_issue_polling.py`, `test_daemon_checkpoint.py`, `test_daemon_pr_lifecycle.py`
- Vérification des `AUTO_RUNNABLE_STATES` et `HUMAN_GATE_STATES`
- Vérification des `_STATUS_MAP` et `_STEP_AGENTS` dans `artifact_reader.py`
- Vérification de `next_ticket_id()` et de son regex numérique
- Vérification de `_classify_dirty_files()` et `_ensure_clean_working_tree()`
- Vérification de `_checkpoint_and_push_before_pr()` et `handle_test_complete()`

---

## Points validés

### Bug 1 — Timeline mapping ✓

`artifact_reader.py:151-156` corrige correctement tous les états :

| État | human_gate | status step | agent |
|------|-----------|-------------|-------|
| `PLAN_REVIEW_NEEDED` | True | waiting_human | — |
| `IMPLEMENTATION_REVIEW_NEEDED` | **False** | running | reviewer |
| `IMPLEMENTATION_FIX_REQUIRED` | False | running (fix_loop) | coder |
| `IMPLEMENTATION_APPROVED` | False | running (tests) | tester |
| `TEST_COMPLETE` | True | done | — |

Le mapping correspond exactement au spec du ticket. Aucune duplication de state machine (la timeline reste une projection de `state.json`). Tests couverts dans `test_ticket_timeline.py`.

### Bug 2 — Allocation ticket id ✓

`run_daemon.py:687-698` : parsing numérique robuste via `re.match(r"T(\d+)$", p.name)` + `int(m.group(1))`. Format de sortie `f"T{max_num + 1:03d}"` zero-padé à 3 chiffres minimum.

Tous les cas du ticket testés :
- T034 → T035 ✓
- T099 → T100 ✓
- T001/T010/T100 → T101 (piège lexicographique évité) ✓
- gaps (T001/T005/T020 → T021) ✓
- `reserved` set pris en compte ✓

### Bug 3 — Classification dirty tree ✓

`run_daemon.py:235-331` : classification en 3 buckets corrects :
- `workflow_artifacts` (runs/*) → auto-checkpointable
- `code_scope_files` (_CODE_SCOPE_PREFIXES) → auto-checkpointable avec `--include-code`
- `unknown_files` → abort sécurisé

Les fichiers du cas T100 (`services/`, `apps/`) tombent bien dans `code_scope_files`, plus dans `unknown_files`. Les vrais fichiers inconnus continuent à bloquer. Aucun `git add .`. Tests complets dans `test_daemon_checkpoint.py`.

### Bug 5 — .gitignore ✓

Ajouts corrects : `runs/*/state.json.tmp`, `runs/*/retry-state.json`, `runs/*/retry-state.json.tmp`, `runs/.issue-intake.json.tmp`. Suppression de `apps/dashboard/node_modules/.vite/` acceptable car entièrement couvert par `apps/dashboard/node_modules/` (le dossier parent déjà ignoré couvre récursivement son contenu).

---

## Problèmes détectés

### [BLOQUANT] Bug 4 — `_checkpoint_and_push_before_pr` non-bloquante

**Fichier** : `run_daemon.py:539-574`

**Critère violé** : "la PR est créée/updated uniquement après push stable"

La fonction `_checkpoint_and_push_before_pr` retourne `None` dans tous les cas :

```python
def _checkpoint_and_push_before_pr(ticket_id: str) -> None:
    # ... logs failure but does not abort
    if commit_result.returncode not in (0, 1):
        _log(f"{ticket_id}: pre-PR checkpoint failed rc={commit_result.returncode}")
        return   # <-- returns None, caller proceeds anyway
```

Et `handle_test_complete` appelle `create_or_update_pr` inconditionnellement :

```python
def handle_test_complete(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    _checkpoint_and_push_before_pr(ticket_id)
    create_or_update_pr(ticket_id, run_dir, repo)  # <-- toujours appelé
    check_and_close_issue(ticket_id, run_dir, repo)
```

**Impact concret** : si `git push` échoue (réseau, remote rejeté, etc.), la PR est quand même créée ou mise à jour. Le remote branch ne contient pas les derniers artefacts (test-report.md, state.json final). La PR pointe sur un état incomplet. Ce cas s'est produit dans T100 — c'est exactement le bug que ce ticket vise à corriger.

**Correction demandée** :

Faire retourner un `bool` à `_checkpoint_and_push_before_pr` et conditionner la création de PR à son succès :

```python
def _checkpoint_and_push_before_pr(ticket_id: str) -> bool:
    """Returns True if push succeeded or nothing to commit. False blocks PR creation."""
    commit_result = subprocess.run(...)
    if commit_result.returncode not in (0, 1):
        _log(f"{ticket_id}: pre-PR checkpoint failed rc={commit_result.returncode}")
        return False
    if commit_result.returncode == 0:
        push_result = subprocess.run(...)
        if push_result.returncode != 0:
            _log(f"{ticket_id}: pre-PR push failed rc={push_result.returncode} — PR skipped")
            return False
        _log(f"{ticket_id}: pre-PR push ok")
    else:
        _log(f"{ticket_id}: pre-PR checkpoint — nothing to commit, skipping push")
    return True


def handle_test_complete(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    _log(f"{ticket_id}: TEST_COMPLETE PR lifecycle")
    if not _checkpoint_and_push_before_pr(ticket_id):
        _log(f"{ticket_id}: pre-PR checkpoint/push failed — PR creation skipped")
        return
    create_or_update_pr(ticket_id, run_dir, repo)
    check_and_close_issue(ticket_id, run_dir, repo)
```

Le daemon repassera au prochain cycle et retentера si l'état reste `TEST_COMPLETE`.

---

## Risques éventuels

### [Mineur] `_CODE_SCOPE_PREFIXES` duplique `COMMIT_SCOPE`

`run_daemon.py:236-249` : la liste `_CODE_SCOPE_PREFIXES` est une copie manuelle de `COMMIT_SCOPE` défini dans `run_ticket.py`. Si `run_ticket.py` évolue (ajout d'un préfixe), le daemon ne sera pas automatiquement mis à jour. Acceptable pour ce ticket, mais à surveiller. Un commentaire `# keep in sync with COMMIT_SCOPE in run_ticket.py` serait utile.

### [Mineur] `IMPLEMENTATION_APPROVED` — fix_loop toujours "skipped"

`artifact_reader.py:155-156` : pour l'état `IMPLEMENTATION_APPROVED`, le step fix_loop affiche toujours "skipped". Si le workflow a traversé `IMPLEMENTATION_FIX_REQUIRED` avant d'atteindre `IMPLEMENTATION_APPROVED`, le fix_loop a bien tourné mais sera affiché comme skipped. État transitoire (auto-runnable, transition immédiate), impact cosmétique négligeable. Pas bloquant.

### [Mineur] `_classify_dirty_files` silencieux sur git failure

`run_daemon.py:267-268` : si `git status --porcelain` retourne un exit code non-zéro, la fonction retourne trois listes vides, et `_ensure_clean_working_tree` laisse passer (retourne `True`). Si git est indisponible ou corrompu, le daemon continue sans le savoir. Cas extrêmement rare, comportement acceptable.

---

## Décision

- REQUEST_CHANGES

Un problème bloquant unique : `_checkpoint_and_push_before_pr` est non-bloquante et ne peut pas empêcher la création de PR en cas d'échec du push. Ceci viole directement le critère d'acceptation "la PR est créée/updated uniquement après push stable".

La correction est minimale et localisée à `run_daemon.py:539-574`.

## Actions demandées

1. Faire retourner `bool` à `_checkpoint_and_push_before_pr` (True = push stable ou rien à pusher, False = échec).
2. Conditionner l'appel à `create_or_update_pr` dans `handle_test_complete` au retour `True`.
3. Mettre à jour le test `test_handle_test_complete_checkpoints_before_pr` dans `test_daemon_pr_lifecycle.py` pour couvrir le cas échec push → PR non créée.
