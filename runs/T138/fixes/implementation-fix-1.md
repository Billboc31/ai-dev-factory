# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T138/reviews/implementation-review.md
- generated at: 2026-05-22T15:51:59Z

---

I now have a complete picture of the implementation. Let me write the structured review.

---

# PR Review — T138 — Generic AI sandbox auto-fix loop

## Résumé

L'implémentation livre un système de **proposition de patches en lecture seule** : l'AI analyse un échec sandbox et propose des corrections visualisables dans le dashboard. Aucun fichier n'est modifié, aucun sandbox n'est relancé, aucune boucle de retry n'existe. C'est ce que le plan approuvé a spécifié — mais cela ne couvre pas les critères d'acceptance du ticket.

## Vérifications effectuées

- Lecture complète des 8 fichiers créés et des 3 modifiés
- Comparaison point par point avec les acceptance criteria du ticket
- Analyse de la sécurité (exec_cmd, path traversal, concurrence)
- Revue de la couverture de tests
- Traçage du lifecycle workflow (plan-review.md × 2, workflow-status.md)

## Points validés

**Architecture et patterns**
- `call_ai_runtime` suit fidèlement le pattern `_invoke_llm` de `run_scripts.py` : `shlex.split(exec_cmd) + ["--print"]`, subprocess, stdin prompt, stdout parsed — aucun SDK provider, aucune variable d'env hardcodée.
- Le découpage supervisor/control_api/dashboard respecte l'architecture en couches existante.
- `auto_fix_runner.py` est un proxy HTTP propre, miroir de `sandbox_runner.py`.
- Le background thread dans `supervisor/main.py` retourne immédiatement un `proposal_id`, le polling est correctement implémenté côté dashboard.

**Sécurité path**
- `validate_patches` rejette les path traversal (`..`) et tout chemin hors `.ai-dev-factory/scripts/`.
- Aucun secret hardcodé dans le code de production (hors valeur par défaut, voir ci-dessous).

**Qualité code**
- Code lisible, fonctions courtes, nommage explicite.
- Gestion d'erreurs explicite dans `_run_proposal_bg` (try/except sur collect, call, validate puis sur persist séparément).
- 16 tests passent, couvrant les cas unitaires du proposer et les routes.

**Généricité**
- `collect_failure_context` ne fait aucune hypothèse sur les noms de services, ports ou frameworks.
- Le contexte est construit depuis `deploy.yml`, `state.json`, `run.log` et les scripts — conformément au ticket.

## Problèmes détectés

### [BLOQUANT] Loop absente — 5 acceptance criteria non satisfaits

Le ticket T138 est intitulé **"Generic AI sandbox auto-fix loop"**. Les critères d'acceptance suivants ne sont pas satisfaits :

| Critère ticket | Statut |
|---|---|
| sandbox reruns after fixes | ❌ pas implémenté |
| retries are bounded and observable | ❌ aucune boucle |
| iteration history is persisted and visible | ❌ proposals sans notion d'itération |
| the system never enters infinite retry loops | ❌ N/A (pas de loop) |
| successful fixes result in sandbox success state | ❌ pas implémenté |
| failed retries result in clean terminal failed state | ❌ pas implémenté |

Le plan reviewer a intentionnellement réduit ce scope (plan-review.md : *"Do not automatically modify operational artifacts or rerun sandboxes yet"*). Le plan approuvé est conforme à ce qui a été livré. Mais les acceptance criteria du ticket restent la barre de l'implementation review — et 5 sur 9 ne sont pas atteints.

**Action requise** : soit compléter T138 avec les composants manquants (apply, rerun, loop), soit amender explicitement les acceptance criteria du ticket pour le scope proposal-only et ouvrir un ticket de suivi pour la boucle.

### [BLOQUANT] Tests requis par le ticket absents

Le ticket demande explicitement des tests pour :
- successful convergence after fix — ❌ absent
- retry limit reached — ❌ absent
- patch application failure — ❌ absent
- sandbox crashes — ❌ absent
- iteration history persistence — ❌ couvert partiellement (proposals, pas itérations)

Les tests présents couvrent le proposer unitaire et les routes — utiles, mais insuffisants au regard du ticket.

### [MINEUR] Bug dans `_is_allowed_path` — condition doublon

```python
# auto_fix_proposer.py
return normalized.startswith(_ALLOWED_PREFIX + "/") or normalized == _ALLOWED_PREFIX
```

La condition `normalized == _ALLOWED_PREFIX` autorise le chemin `.ai-dev-factory/scripts` lui-même (sans filename) comme `relative_path` valide. Écrire dans un répertoire sans nom de fichier serait rejeté à l'écriture disque, mais c'est une fuite de validation à corriger :

```python
# correct : seuls les chemins avec un fichier à l'intérieur sont valides
return normalized.startswith(_ALLOWED_PREFIX + "/")
```

### [MINEUR] `exec_cmd` default dangereux en deux points

```python
# routes/auto_fix.py et supervisor/main.py
exec_cmd: str = "claude --dangerously-skip-permissions"
```

`--dangerously-skip-permissions` ne devrait pas être la valeur par défaut. Forcer l'appelant à passer explicitement `exec_cmd` réduit le risque d'exécution accidentelle.

### [MINEUR] Race condition proposal "pending" permanente

Le proposal est persisté en `status=pending` avant le lancement du thread. Si le superviseur s'arrête pendant l'exécution du thread, le proposal reste `pending` indéfiniment — pas de mécanisme de timeout ni de recovery au redémarrage. Acceptable pour une V1 proposal-only mais à documenter.

### [MINEUR] `project_root` inutilisé dans `validate_patches`

```python
def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
```

Le paramètre est ignoré. Si l'intention est de permettre une validation filesystem future, c'est acceptable — mais le `noqa: ARG001` devrait s'accompagner d'un commentaire expliquant pourquoi il est conservé.

## Risques éventuels

- Absence de concurrency control sur le endpoint `POST /propose` : plusieurs proposals peuvent être lancées en parallèle pour le même sandbox, potentiellement avec des appels AI redondants et des écritures concurrentes.
- La regex `re.search(r"\[.*\]", output, re.DOTALL)` est greedy — si l'AI ajoute du texte après `]`, le match peut s'étendre à des `]` parasites. En pratique, le `json.loads` catchera l'erreur et propagera `ValueError` correctement, mais c'est fragile.

## Décision

- ~~APPROVED~~
- **REQUEST_CHANGES**

## Actions demandées

1. **[Obligatoire]** Résoudre l'écart avec les acceptance criteria du ticket — soit implémenter la boucle apply/rerun/retry, soit explicitement amender le ticket pour scope proposal-only et créer un ticket de suivi pour la loop. Sans cela, T138 n'est pas livré.

2. **[Obligatoire]** Ajouter les tests requis par le ticket (convergence, retry limit, patch application failure) — ou documenter formellement leur déplacement dans un ticket de suivi.

3. **[Mineur]** Corriger `_is_allowed_path` : supprimer la condition `normalized == _ALLOWED_PREFIX`.

4. **[Mineur]** Supprimer la valeur par défaut `"claude --dangerously-skip-permissions"` pour `exec_cmd`.

---

IMPLEMENTATION_FIX_REQUIRED
