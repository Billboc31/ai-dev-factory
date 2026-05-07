En attente de votre approbation pour écrire `runs/T007/plan.md`.

Voici le plan complet que je propose :

---

## Plan T007 — Git ticket branch workflow

### Constat

Le runner `tools/agent_runner/run_ticket.py` a été produit lors d'un cycle chat-driven sans plan formel. Il implémente déjà `--branch`, `--commit`, `--push` avec la convention `ticket/TXXX-*`. **Deux risques non traités** et **une documentation manquante** sont identifiés.

### Fichiers concernés

| Fichier | Action |
|---------|--------|
| `tools/agent_runner/run_ticket.py` | Corriger 2 risques |
| `docs/ai/git-workflow.md` | Créer (manquant) |
| `runs/T007/plan.md` | Ce plan |
| `runs/T007/workflow-status.md` | Remettre en état gate plan |

### Étapes

1. **Corriger `checkout_branch`** — `git checkout -B` écrase silencieusement une branche existante non mergée. Remplacer par : vérifier si la branche existe → `git checkout <name>` si oui, `git checkout -b <name>` sinon.

2. **Corriger `commit_ticket`** — `git add .` trop large (inclut `.env`, build, hors scope). Restreindre au staging explicite ou ajouter un avertissement visible.

3. **Créer `docs/ai/git-workflow.md`** — documenter la convention `ticket/TXXX-*`, les trois commandes du runner, les invariants (pas de merge auto, pas de PR auto, push explicite).

4. **Remettre `runs/T007/workflow-status.md`** — supprimer les statuts `IMPLEMENTATION_APPROVED` / `MEMORY_APPROVED` posés prématurément, remettre le pipeline au gate plan.

### Risques

- `git checkout -B` : destruction silencieuse d'une branche existante
- `git add .` : commit de fichiers hors scope
- Documentation absente : workflow non reproductible

### Hors scope

Ouverture automatique de PR, merge automatique, review distante, GitHub Actions, modification de `run_step.py`, changement de convention de branche.

---

Dois-je écrire ce plan dans `runs/T007/plan.md` ?
