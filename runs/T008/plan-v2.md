Le plan v2 est écrit. Voici ce qui a changé par rapport à v1 :

**Correction principale** : `state.json` remplace `workflow-status.md` comme source de vérité canonique.

**Ce que le coder trouvera dans le plan :**

- **Structure `state.json`** : format JSON explicite avec `ticket_id`, `state`, `branch`, `updated_at`
- **Table de transitions complète** : chaque transition est listée explicitement — toute transition non listée bloque avec exit code 2
- **5 gates pré-exécution** dans l'ordre :
  1. `state.json` existe et est JSON valide
  2. État connu
  3. État ≠ `TEST_COMPLETE`
  4. Branche git cohérente avec `state["branch"]`
  5. Working tree propre
- **`workflow-status.md` devient journal append-only** : jamais lu, toujours écrit en append après une transition réussie
- **Détection mots-clés stricte** : regex `^KEYWORD$` sur les étapes review, warning + exit code 1 si aucun trouvé
- **`--auto-init` explicite** : création `state.json` protégée contre l'écrasement silencieux

**Statut** : `PLAN_REVIEW_NEEDED`
