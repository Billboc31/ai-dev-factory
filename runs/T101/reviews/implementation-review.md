---

# PR Review — T101 Runtime Hardening

## Résumé

Implémentation solide sur 4 des 5 bugs. Un problème bloquant sur le Bug 4.

---

## Points validés

**Bug 1 — Timeline mapping** : `artifact_reader.py:151-156` corrige correctement tous les états. `IMPLEMENTATION_REVIEW_NEEDED` → `human_gate=False`, reviewer en "running". Tous les autres états correspondent au spec.

**Bug 2 — Ticket IDs** : `run_daemon.py:687-698` parse numériquement avec `re.match(r"T(\d+)$")`. Format zero-padé 3 digits. Tous les cas du ticket couverts par les tests : T034→T035, T099→T100, T001/T010/T100→T101 (piège lexicographique évité), gaps.

**Bug 3 — Dirty tree** : `run_daemon.py:235-331` classifie en 3 buckets corrects. Les fichiers coder (services/, apps/) tombent dans `code_scope_files` (auto-checkpointés). Les vrais inconnus bloquent toujours. Aucun `git add .`.

**Bug 5 — .gitignore** : tmp files ajoutés. Suppression de `apps/dashboard/node_modules/.vite/` acceptable — couvert par le dossier parent.

---

## Problème bloquant

**`_checkpoint_and_push_before_pr` est non-bloquante** (`run_daemon.py:539-574`).

La fonction retourne `None` dans tous les cas. `handle_test_complete` appelle `create_or_update_pr` **inconditionnellement**, même si push a échoué :

```python
def handle_test_complete(...):
    _checkpoint_and_push_before_pr(ticket_id)   # None toujours
    create_or_update_pr(...)                     # appelé même si push échoué
```

**Impact** : si `git push` échoue, la PR est créée sur un remote branch incomplet (test-report.md, state.json final absents). C'est exactement le bug T100 que ce ticket vise à corriger.

**Critère violé** : "la PR est créée/updated uniquement après push stable"

**Correction minimale demandée** (`run_daemon.py:539-574`) :

```python
def _checkpoint_and_push_before_pr(ticket_id: str) -> bool:
    # ... mêmes logs
    if commit_result.returncode not in (0, 1):
        return False
    if commit_result.returncode == 0:
        push_result = ...
        if push_result.returncode != 0:
            return False
    return True

def handle_test_complete(...):
    if not _checkpoint_and_push_before_pr(ticket_id):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(...)
    check_and_close_issue(...)
```

Ajouter un test couvrant le cas push échoué → PR non créée dans `test_daemon_pr_lifecycle.py`.

---

## Risques mineurs

- `_CODE_SCOPE_PREFIXES` (`run_daemon.py:236`) duplique `COMMIT_SCOPE` de `run_ticket.py` — drift possible si l'un évolue sans l'autre.
- `IMPLEMENTATION_APPROVED` affiche fix_loop comme "skipped" même si un fix loop a tourné — cosmétique, état transitoire.

---

IMPLEMENTATION_FIX_REQUIRED
