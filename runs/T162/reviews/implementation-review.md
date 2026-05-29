## Review T162 — Résumé

**Décision : IMPLEMENTATION_FIX_REQUIRED**

### Ce qui est correct

Le fix central est propre et minimal :
- `handle_test_complete()` capture maintenant la valeur de retour de `auto_merge_pr()` et appelle `detect_pr_conflict()` immédiatement quand le merge échoue — le ticket transite vers `CONFLICT_RESOLUTION_NEEDED` dans le même handler
- Le fallback de recherche PR par préfixe de branche (`ticket/{ticket_id}-`) couvre les cas de renommage
- 4 nouveaux tests couvrent correctement les cas ajoutés
- Aucun changement dashboard nécessaire (l'existant fonctionne déjà dès que l'état est positionné)

### Problème bloquant — Scope violation majeure

Le diff inclut **~928 lignes nettes supprimées** de fichiers sans rapport avec T162 :
- `environment_provision.py` (268 lignes), `environment_runner.py` (180 lignes), `sandbox_runtime_deploy.py` (480 lignes) — complètement supprimés
- `supervisor/main.py` — 184 lignes retirées
- `routes/environments.py` — refactorisé (~178 lignes)
- Tests environment et sandbox supprimés
- Composants dashboard environnement modifiés

Ces changements ne figurent **ni dans le ticket ni dans le plan approuvé**, dépassent largement le scope, et présentent un risque de régression réel pour d'autres workflows actifs.

### Problème mineur

Le message de log ligne 884 (`Failed to transition ticket ... to CONFLICT_RESOLUTION_NEEDED`) est émis même quand `auto_merge_pr()` échoue pour des raisons non-conflictuelles — le message est trompeur.

**Actions requises** : retirer les changements hors-scope et corriger le message de log. Le core fix peut être conservé tel quel.

IMPLEMENTATION_FIX_REQUIRED
