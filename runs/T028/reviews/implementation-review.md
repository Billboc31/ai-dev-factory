---

# PR Review — T028 Control API foundation

## Résumé

Implémentation solide d'une façade REST FastAPI dans `services/control_api/`. Architecture en 3 couches proprement séparées, tous les endpoints du ticket présents, tests exhaustifs sur 3 fichiers. Les contraintes architecturales critiques sont strictement respectées.

## Vérifications effectuées

- Lecture complète de `main.py`, `routes/*.py`, `models/schemas.py`, `services/artifact_reader.py`, `services/subprocess_runner.py`, `services/daemon_manager.py`
- Inspection des 3 fichiers de tests (40+ cas)
- Vérification endpoint par endpoint contre la liste du ticket
- Vérification de non-mutation de `state.json` (assertions mtime dans les tests)
- Audit sécurité des appels subprocess et construction de paths

## Points validés

**Architecture conforme aux contraintes critiques :**
- Aucune logique workflow dupliquée — toutes les actions passent par `subprocess_runner` → scripts existants
- Aucune logique Git dupliquée — commit/push/checkpoint délégués via `run_ticket.py --commit/--push/--checkpoint`
- `artifact_reader` strictement en lecture seule — vérifié par assertion mtime dans les tests
- Aucune modification des scripts runtime existants

**Endpoints :** tous les 23 endpoints du ticket sont implémentés.

**Sécurité :** `subprocess.run` avec liste d'args (pas d'injection shell), validation ticket_id stricte sur toutes les couches, `sys.executable` pour garantir le bon venv.

**Tests :** validation ticket_id, erreurs subprocess, daemon lifecycle, lecture artefacts, non-mutation `state.json` — tous couverts.

## Problèmes détectés

### P1 — Dead code dans `run_next` [minor]
`routes/tickets.py:116-120` : `BackgroundTasks` importé mais jamais utilisé, `result_holder` alloué et peuplé par le thread background mais jamais lu. Le résultat subprocess de `run-next` est silencieusement jeté. Le comportement observable (202 + thread) est correct, mais le dead code est trompeur.

### P2 — Double-logging sur les actions workflow [minor]
`routes/tickets.py` et `subprocess_runner.py` loggent la même ligne pour chaque action (ex. `api: POST /tickets/T028/approve-plan`), en plus du middleware. 3 lignes par requête pour le même événement.

### P3 — `TICKET_ID_RE` dupliqué [minor]
Même regex définie indépendamment dans `artifact_reader.py:13` et `subprocess_runner.py:16`.

### P4 — `TicketDetail` vide [minor]
`models/schemas.py:34` : `class TicketDetail(TicketSummary): pass` — à supprimer ou enrichir.

### P5 — `daemon stop()` sans attente de terminaison [minor]
PID file supprimé immédiatement après SIGTERM, sans vérifier que le process a terminé. Limitation documentable.

## Décision

Tous les critères d'acceptation du ticket sont remplis. Les problèmes détectés sont mineurs et n'affectent pas la correction fonctionnelle ni la sécurité. P1 est le plus visible mais le comportement observable reste correct.

La review est écrite dans `runs/T028/reviews/review.md`.

IMPLEMENTATION_APPROVED
