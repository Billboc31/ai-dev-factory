Il me faut l'autorisation pour écrire le fichier. En attendant, voici le plan complet :

---

## Plan — T014 : Stabiliser le validator planner flexible

### Contexte

Après lecture de `run_step.py` et `run_ticket.py`, la migration vers la validation souple est déjà structurellement en place :

- `import subprocess` présent (ligne 10), aucun `import subprocessf`
- `_REQUIRED_SECTION_GROUPS` défini (lignes 76–96) et utilisé dans `validate_planner_output()`
- `run_ticket.py` importe et appelle `validate_planner_output` dans `auto_run()` (lignes 551–558)

**Trois gaps résiduels identifiés après lecture du code :**

1. `"## contexte technique"` n'est pas un synonyme reconnu du groupe `contexte`
2. `"## acceptance criteria"` n'est pas un synonyme reconnu du groupe `critères d'acceptation`
3. `"## étapes d'implémentation"` est dupliqué dans le groupe `inclus` (ligne 87)
4. Aucun test unitaire — `tests/` est vide

Ces gaps causent le rejet du plan d'exemple explicite du ticket.

---

### Objectif

Corriger les lacunes dans `_REQUIRED_SECTION_GROUPS`, supprimer le doublon, créer des tests unitaires ciblés.

---

### Fichiers concernés

```
tools/agent_runner/run_step.py              # correction des groupes (~3 lignes)
tests/test_validate_planner_output.py       # nouveau — 5 tests unitaires
```

`run_ticket.py` n'est **pas** modifié.

---

### Étapes

**Étape 1 — Corriger `_REQUIRED_SECTION_GROUPS` dans `run_step.py`**

- Groupe `contexte` : ajouter `"## contexte technique"`
- Groupe `critères d'acceptation` : ajouter `"## acceptance criteria"`
- Groupe `inclus` : retirer la seconde occurrence de `"## étapes d'implémentation"` (doublon ligne 87)

**Étape 2 — Créer `tests/test_validate_planner_output.py`**

Cinq tests unitaires :
1. Plan valide avec titres canoniques → `reasons == []`
2. Plan valide avec synonymes (`## contexte technique`, `## objectifs`, `## scope`, `## non inclus`, `## acceptance criteria`) → `reasons == []`
3. Plan trop court (< 100 mots) → raison `"plan trop court"` présente
4. Plan sans section `hors scope` → raison `"section manquante: «hors scope»"` présente
5. Plan contenant `"implémentation terminée"` → raison `"phrase interdite"` présente

**Étape 3 — Vérification runtime (manuelle)**

Confirmer `INIT → PLAN_REVIEW_NEEDED` via `--auto`. Documenté comme étape manuelle.

---

### Risques

- Faible — changements locaux au dictionnaire et à un fichier de test
- Aucune interface publique modifiée
- `run_ticket.py` inchangé

---

### Hors scope

Memory workflow, GitHub, watcher, daemon, dashboard, auto-merge, PR automation, multi-agent, refactor `run_ticket.py`, nouveaux groupes de sections non demandés.

---

### Critères d'acceptation

Le plan suivant est accepté sans erreur :
```
## contexte technique
## objectifs
## scope
## non inclus
## acceptance criteria
```

Les cinq tests unitaires sont présents et verts. Le validator continue à rejeter les plans trop courts, sans groupe obligatoire, ou avec phrase interdite. Aucun impact sur le workflow `--auto`.

---

Le plan est prêt à être écrit dans `runs/T014/plan.md` dès que vous accordez la permission d'écriture.
