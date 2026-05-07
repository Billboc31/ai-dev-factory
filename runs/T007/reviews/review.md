J'ai maintenant tous les éléments. Voici la review complète.

---

## Review T007 — Git Ticket Branch Workflow

### Résumé

T007 introduit deux corrections critiques dans `run_ticket.py` et crée la documentation `docs/ai/git-workflow.md`. Le code est techniquement solide sur les deux corrections. **Un problème de conformité majeur doit cependant être noté : T007 lui-même n'a pas suivi la convention qu'il implémente.**

---

### Points validés

**Convention `ticket/TXXX-*` — documentation**
- `docs/ai/git-workflow.md` l. 11–14 : convention nommée, exemples corrects, slug en kebab-case, règle générée par `slugify()`.
- `branch_name()` (run_ticket.py:39-41) : format `ticket/{ticket_id}-{suffix}`, cohérent avec la doc.

**Correction 1 — `checkout_branch()` (l. 87–93)**
- Avant : `git checkout -B` écrasait silencieusement une branche existante avec du travail non mergé.
- Après : `git show-ref --verify --quiet refs/heads/{name}` → `checkout` ou `checkout -b` selon existence.
- Comportement correct, sûr, non destructif.

**Correction 2 — `commit_ticket()` (l. 96–109)**
- Avant : `git add .` pouvait stager `.env`, artefacts de build, etc.
- Après : staging limité à `runs/{ticket_id}/` uniquement, avec message d'avertissement explicite à l'utilisateur.
- Comportement correct, périmètre maîtrisé.

**Documentation `docs/ai/git-workflow.md`**
- Workflow type en 7 étapes clair et complet.
- Invariants listés explicitement (pas de merge auto, pas de PR auto, push toujours explicite).
- Liens vers `pr-lifecycle.md` et `workflow.md`.
- Commandes exactes avec exemples copiables.

**Cohérence avec le workflow existant**
- `run_ticket.py` reste intentionnellement explicite — aucune automatisation cachée ajoutée.
- `validate_ticket_id` (l. 27-30) protège contre les IDs malformés.
- `push_branch()` (l. 112-115) : `git push -u origin <name>`, toujours explicite.

---

### Points à corriger

**[BLOQUANT] T007 n'a pas utilisé sa propre convention de branche**

Tous les commits T007 sont directement sur `main`. Il n'existe aucune branche `ticket/T007-*` dans le dépôt :

```
* 086161c T007: implement git ticket branch workflow  ← main
* 79ce526 Add minimal T007 tester prompt             ← main
* 6d71d98 Add simplified T007 review prompt          ← main
* 279a098 Add T007 coder prompt                      ← main
```

La règle documentée est : *"Un ticket = une branche = une PR."* T007 l'a violée en implémentant et en committant directement sur `main` sans branche dédiée ni PR. C'est un problème d'exemplarité — le premier ticket à introduire la convention aurait dû en être la démonstration.

**[MINEUR] `workflow-status.md` — doublon de `Last Update`**

```
## Last Update
PLAN_APPROVED — implementation started by Coder

## Last Update
IMPLEMENTATION_APPROVED
```

Deux sections `## Last Update`. Seule la dernière a du sens ; la première est un artefact de la mise à jour incrémentale.

**[MINEUR] Workflow type — step 1 non délégué au runner**

```
1. git checkout main && git pull
```

Cette étape est en commande brute. Si le runner doit être le point d'entrée unique du workflow, cette étape devrait soit être intégrée dans `--branch` (retour sur main + pull avant création), soit être documentée comme étape manuelle intentionnellement hors runner. La documentation ne justifie pas ce choix.

---

### Décision finale

**CHANGES_REQUESTED**

Les deux corrections de code et la documentation sont valides et prêtes. La review ne bloque pas le merge du contenu technique, mais exige deux actions avant clôture du ticket :

1. **Créer rétrospectivement la branche `ticket/T007-git-ticket-branch-workflow`** à partir du commit avant l'implémentation (ou ouvrir une PR depuis un squash), pour que T007 soit archivé conformément à sa propre règle.
2. **Corriger le doublon `## Last Update`** dans `runs/T007/workflow-status.md`.

Le point sur le step 1 du workflow type peut être documenté comme étape manuelle intentionnelle — c'est acceptable si c'est explicite.
