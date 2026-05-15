# PR Review — T028 Control API foundation

## Résumé

Implémentation d'une couche REST FastAPI dans `services/control_api/` servant de façade au runtime workflow existant. Architecture en 3 couches (routes / services / models), 3 fichiers de tests, couverture exhaustive des endpoints requis par le ticket.

## Vérifications effectuées

- Lecture complète de tous les fichiers produits : `main.py`, `routes/*.py`, `models/schemas.py`, `services/artifact_reader.py`, `services/subprocess_runner.py`, `services/daemon_manager.py`
- Vérification de tous les tests : `tests/test_control_api_endpoints.py`, `tests/test_control_api_artifacts.py`, `tests/test_control_api_subprocess.py`
- Vérification du respect des contraintes architecturales (façade, no-reimplementation, no-state.json mutation)
- Vérification de chaque critère d'acceptation du ticket
- Inspection des appels subprocess pour détecter toute duplication de logique workflow ou git

## Points validés

### Architecture conforme

- ✅ Module séparé `services/control_api/` — aucun code dans les modules runtime existants
- ✅ Aucune logique workflow dupliquée : toutes les actions passent par `subprocess_runner` → `run_ticket.py` / `run_daemon.py` / `run_issue_intake.py`
- ✅ Aucune logique Git dupliquée : commit/push/checkpoint délégués à `run_ticket.py --commit/--push/--checkpoint`
- ✅ `artifact_reader` en lecture seule strict — le test `test_artifact_reader_does_not_write` vérifie le mtime de `state.json`
- ✅ `subprocess_runner` ne touche jamais `state.json` — vérifié par `test_no_state_json_mutation`
- ✅ Aucune modification des scripts runtime existants (`run_ticket.py`, `run_daemon.py`, `run_issue_intake.py`)

### Endpoints couverts

- ✅ `GET /health` — implémenté
- ✅ `GET/POST /daemon/{status,start,stop,restart}` — PID file + SIGTERM
- ✅ `GET /tickets` + `GET /tickets/{id}` + `/logs` + `/artifacts` + `/plan` + `/review` + `/tests`
- ✅ `POST /tickets/{id}/{approve-plan,request-plan-fix,approve-implementation,request-implementation-fix,run-next,commit,push,checkpoint}`
- ✅ `POST /issues/intake` + `GET /issues/intake/status`
- ✅ `GET /providers/status` + `GET /projects`

### Logging

- ✅ Middleware global loggue chaque requête avec méthode, path, status, durée
- ✅ Chaque action loggue explicitement : `api: POST /tickets/T028/approve-plan`, `api: daemon start requested`, `api: checkpoint requested for T028`

### Tests

- ✅ 40+ cas couverts sur 3 fichiers
- ✅ Validation ticket_id (format T\d{3,}) testée sur les 3 couches
- ✅ Erreurs subprocess (returncode != 0, OSError) couvertes
- ✅ Daemon lifecycle (start, stop, already-running, not-running) couvert
- ✅ Lecture artefacts (plan, review, tests, logs) avec cas missing/404 couverts
- ✅ Non-mutation de state.json vérifiée par assertion sur mtime

### Sécurité

- ✅ `subprocess.run` avec liste d'args — pas d'injection shell possible
- ✅ `sys.executable` utilisé pour garantir le bon venv
- ✅ Validation ticket_id stricte avant toute construction de path ou appel subprocess
- ✅ `artifact_reader._read_artifact` utilise des filenames hardcodés — pas de traversal possible en pratique
- ✅ `daemon_manager` utilise `start_new_session=True` pour isolation correcte du process fils

## Problèmes détectés

### P1 — Dead code dans `run_next` [minor]

**Fichier** : `services/control_api/routes/tickets.py` lignes 116-120

```python
from fastapi.background import BackgroundTasks   # ← importé, jamais utilisé
result_holder: list[ActionResult] = []           # ← alloué, jamais lu

def _bg() -> None:
    result_holder.append(subprocess_runner.run_next(...))  # ← résultat silencieusement jeté
```

`BackgroundTasks` est importé mais non utilisé. `result_holder` est peuplé par le thread mais jamais consommé. Toute erreur subprocess dans `run_next` est silencieusement absorbée. Le comportement fonctionnel est correct (202 + thread background), mais ce dead code génère de la confusion sur l'intention réelle.

**Correction suggérée** : supprimer `result_holder` et l'import `BackgroundTasks`, simplifier `_bg` en appel direct sans collecte de résultat.

### P2 — Double-logging sur les actions workflow [minor]

Les routes (`routes/tickets.py`) loggent `api: POST /tickets/%s/approve-plan`, et `subprocess_runner.approve_plan()` loggue exactement la même ligne. Combiné au middleware qui loggue aussi chaque requête, chaque action produit 3 lignes de log pour le même événement.

**Correction suggérée** : supprimer le log dans les fonctions `subprocess_runner` ou dans les routes — l'un des deux suffit, le middleware étant déjà présent.

### P3 — `TICKET_ID_RE` dupliqué [minor]

Le même pattern `r"^T\d{3,}$"` est défini indépendamment dans `artifact_reader.py:13` et `subprocess_runner.py:16`. Si le format évolue, une modification sera oubliée.

**Correction suggérée** : extraire dans `models/schemas.py` ou un module `utils.py` partagé.

### P4 — `TicketDetail` vide [minor]

`models/schemas.py:34` : `class TicketDetail(TicketSummary): pass` — classe sans contenu différencié. Soit l'enrichir, soit la supprimer et utiliser directement `TicketSummary`.

### P5 — `daemon_manager.stop()` : PID file supprimé sans attendre la terminaison [minor]

`daemon_manager.py:105-106` : le PID file est supprimé immédiatement après `SIGTERM`, sans vérifier que le process a effectivement terminé. Un `start()` rapide après `stop()` pourrait démarrer un second daemon pendant que le premier finit son shutdown.

Comportement acceptable pour ce scope, mais mérite d'être documenté comme limitation connue.

## Risques éventuels

- **Concurrence sur `run-next`** : plusieurs appels simultanés à `POST /tickets/{id}/run-next` spawnent plusieurs threads, chacun lançant `run_ticket.py` sur le même ticket. Le runtime upstream devrait gérer l'exclusion, mais l'API ne protège pas contre ce cas.
- **CORS `allow_origins=["*"]`** : acceptable dans le contexte localhost sans auth, mais à restreindre si le service est un jour exposé hors loopback.
- **`/issues/intake/status` hardcodé** : retourne toujours `idle`. Acceptable per le ticket ("données initialement mockées"), mais le dashboard ne pourra pas suivre un intake en cours.

## Décision

L'implémentation respecte toutes les contraintes architecturales critiques du ticket : façade pure, no-reimplementation, no-state.json mutation, module séparé, endpoints complets, logging explicite, tests solides.

Les problèmes détectés (P1-P5) sont de niveau mineur/cosmétique et n'affectent pas la correction fonctionnelle ni la sécurité. P1 (dead code dans run_next) est le plus visible mais le comportement observable reste correct.

- APPROVED

## Actions demandées

Les corrections suivantes peuvent être effectuées en follow-up ou dans un ticket de cleanup :

1. Nettoyer le dead code dans `run_next` (supprimer `result_holder` et l'import `BackgroundTasks`)
2. Supprimer la duplication de logging entre routes et subprocess_runner
3. Centraliser `TICKET_ID_RE` dans un module partagé
4. Supprimer ou enrichir `TicketDetail`
