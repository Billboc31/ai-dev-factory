# PR Review — T162: Repair PR conflict reviewer detection and state sync

## Résumé

L'implémentation corrige correctement le bug central du ticket (état `TEST_COMPLETE` non propagé vers `CONFLICT_RESOLUTION_NEEDED`), mais introduit une quantité importante de changements hors scope — suppression et refactoring de services environment/sandbox — qui ne figurent ni dans le ticket ni dans le plan approuvé.

---

## Vérifications effectuées

- Diff complet vs `main` (`git diff main --stat`)
- Lecture de `run_daemon.py` autour des zones modifiées (lignes 651–895, 1726–1730)
- Lecture du plan approuvé (`runs/T162/plan.md`)
- Lecture des nouveaux tests dans `tests/test_daemon_pr_lifecycle.py`
- Inspection de `auto_merge_pr()` pour identifier tous les cas de retour `False`
- Inspection des fichiers environment/sandbox supprimés/modifiés

---

## Points validés

### Fix principal — `handle_test_complete()` (run_daemon.py:879–887)

Le bug était précis : `auto_merge_pr()` était appelé sans capturer la valeur de retour. La correction est correcte et minimale :

```python
if not auto_merge_pr(ticket_id, run_dir, repo):
    state_data = _load_state_json(run_dir)
    pr_number = state_data.get("pr_number")
    if pr_number:
        if not detect_pr_conflict(ticket_id, pr_number, run_dir, repo):
            _log(f"{ticket_id}: Failed to transition ticket {ticket_id} to CONFLICT_RESOLUTION_NEEDED")
    else:
        _log(f"{ticket_id}: PR conflict detected but no PR number in state.json for ticket {ticket_id}")
    return
```

Le return anticipé empêche `check_and_close_issue()` d'être appelé quand le merge échoue.

### Fallback branch rename — `create_or_update_pr()` (run_daemon.py:654–672)

Correcte. Cherche les PRs ouvertes dont `headRefName` commence par `ticket/{ticket_id}-`, couvre le cas de renommage de branche. Persistance dans `state.json`.

### Observabilité (run_daemon.py:1726–1730)

Log ajouté pour `CONFLICT_RESOLUTION_NEEDED` dans `HUMAN_GATE_STATES` — utile.

### Tests

4 nouveaux tests couvrent les cas identifiés :
- `detect_pr_conflict` appelé quand merge retourne `False`
- `check_and_close_issue` non appelé en cas de conflit
- Gestion propre quand `pr_number` absent
- Fallback par prefix de branche

Les 3 tests existants mis à jour correctement pour le nouvel appel subprocess supplémentaire.

### Dashboard

Aucune modification nécessaire — `ConflictResolutionPanel` existant conditionne déjà son affichage sur `state === "CONFLICT_RESOLUTION_NEEDED"`.

---

## Problèmes détectés

### BLOQUANT — Violation de scope majeure

Le diff contient des changements sans rapport avec T162 :

| Fichier | Action | Lignes |
|---|---|---|
| `services/control_api/services/environment_provision.py` | SUPPRIMÉ | -268 |
| `services/control_api/services/environment_runner.py` | SUPPRIMÉ | -180 |
| `services/control_api/services/sandbox_runtime_deploy.py` | SUPPRIMÉ | -480 |
| `services/supervisor/main.py` | -184 lignes | |
| `services/control_api/routes/environments.py` | Refactorisé | 178 lignes |
| `services/control_api/models/sandbox.py` | Suppression enum `LifecyclePhase` | -22 |
| `services/control_api/services/sandbox_manager.py` | Simplifié | -142 |
| `tests/test_environment_supervisor.py` | SUPPRIMÉ | -161 |
| `tests/test_sandbox_runtime_deploy.py` | SUPPRIMÉ | -216 |
| `tests/test_environment_routes.py` | Réduit | -352 |
| `apps/dashboard/src/components/CreateEnvironmentModal.jsx` | Champ supprimé | |
| `apps/dashboard/src/components/EnvironmentCard.jsx` | Lifecycle display supprimé | |

Ces suppressions (~928 lignes nettes supprimées) :

1. **Ne figurent pas dans le plan approuvé.** Le plan n'inclut que `run_daemon.py` et `tests/test_daemon_pr_lifecycle.py`.
2. **Dépassent largement le scope du ticket.** T162 concerne exclusivement la détection de conflit PR et la propagation d'état.
3. **Constituent un risque réel** : d'autres tickets en cours pourraient dépendre de `environment_provision.py`, `environment_runner.py`, ou `sandbox_runtime_deploy.py`. Supprimer ces fichiers sans ticket dédié, sans plan validé, et sans review de l'impact transversal est dangereux.
4. **Contournent le workflow IA.** Ces changements d'architecture auraient besoin de leur propre ticket, plan, et validation.

### MINEUR — Message de log trompeur (run_daemon.py:884)

```python
_log(f"{ticket_id}: Failed to transition ticket {ticket_id} to CONFLICT_RESOLUTION_NEEDED")
```

Ce message est émis quand `auto_merge_pr()` retourne `False` ET que `detect_pr_conflict()` retourne `False`. Or `auto_merge_pr()` retourne `False` pour de nombreuses raisons non-conflictuelles (gh non trouvé, PR fermée, échec de la commande de merge pour CI, etc.). Dans ces cas, `detect_pr_conflict()` vérifie `mergeable == "CONFLICTING"`, constate l'absence de conflit, et retourne `False` — mais le log implique qu'un conflit existait et que la transition a échoué. Le message est donc trompeur dans ~50% des cas d'invocation.

Message suggéré : `"auto_merge_pr failed and no conflict detected — no state transition for {ticket_id}"`.

---

## Risques éventuels

- Suppression de `sandbox_runtime_deploy.py` pourrait casser des imports dans des agents ou scripts non testés
- Suppression de `environment_provision.py` / `environment_runner.py` pourrait briser des workflows environnements actifs
- `LifecyclePhase` supprimé de `sandbox.py` — tout code l'important en runtime échouerait silencieusement

---

## Décision

**IMPLEMENTATION_FIX_REQUIRED**

---

## Actions demandées

1. **Retirer tous les changements hors-scope** (`services/`, `tests/test_environment_*.py`, `tests/test_sandbox_runtime_deploy.py`, `apps/dashboard/`) de cette PR. Ces changements peuvent éventuellement faire l'objet d'un ticket dédié avec plan et review propres.

2. **Corriger le message de log ligne 884** pour ne pas impliquer qu'un conflit a été détecté quand `detect_pr_conflict()` retourne `False` sur un PR non-conflictuel.

Les corrections du core (handle_test_complete, fallback branch rename, tests, observabilité) sont correctes et peuvent être conservées telles quelles.

IMPLEMENTATION_FIX_REQUIRED
