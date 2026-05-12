I need write permission for `runs/T014/reviews/implementation-review.md`. Please grant it and I'll write the review.

Here is the review content for your preview:

---

# PR Review — T014 : Stabiliser le validator planner flexible

## Résumé

L'implémentation proposée est conceptuellement correcte et bien ciblée, mais **elle n'a jamais été appliquée**. `implementation-output.md` contient uniquement des diffs en attente de permission d'écriture. Le code réel dans `run_step.py` est identique à l'état pré-T014. Le répertoire `tests/` n'existe pas.

## Vérifications effectuées

### État réel de `run_step.py`

| Groupe | Attendu | État |
|---|---|---|
| `contexte` | inclure `"## contexte technique"` | **absent** |
| `inclus` | retirer doublon `"## étapes d'implémentation"` | **doublon présent** (lignes 87–88) |
| `critères d'acceptation` | inclure `"## acceptance criteria"` | **absent** |

`validate_planner_output()` utilise `if phrase in lower` sans filtrage de blocs de code — fausse positive non corrigée.

`tests/` : répertoire inexistant. Aucun test unitaire.

### Diffs proposés dans `implementation-output.md`

Tous trois sont valides et bien ciblés — le problème est qu'ils n'ont jamais été écrits sur disque.

## Points validés

- Architecture validator en place, validation par groupes de synonymes ✅
- Import `subprocess` correct ✅
- Compatibilité `run_ticket.py` / `--auto` préservée ✅
- Logs runtime conservés ✅
- Scope borné au ticket ✅

## Problèmes détectés

- **P1 (bloquant)** : `run_step.py` inchangé — les diffs n'ont jamais été appliqués
- **P2 (bloquant)** : `tests/` inexistant — aucun test unitaire

## Décision

**IMPLEMENTATION_FIX_REQUIRED**

## Actions demandées

1. Appliquer Diff 1 : ajouter `"## contexte technique"` et `"## acceptance criteria"`, retirer le doublon
2. Appliquer Diff 2 : stripping code-fence avant `_FORBIDDEN_PHRASES`
3. Créer `tests/test_validate_planner_output.py` avec les six tests du Diff 3
4. Confirmer `pytest tests/` passe sans erreur
