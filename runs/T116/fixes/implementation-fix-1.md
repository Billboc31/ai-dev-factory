# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T116/reviews/implementation-review.md
- generated at: 2026-05-19T17:05:13Z

---

I have all the information I need. Let me write the review.

---

# Review — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Résumé exécutif

L'implémentation corrige les problèmes critiques en production (board DB path, workers registry, daemon logging) et maintient la compatibilité descendante. Elle est correcte pour le cas Docker/production. Trois défauts structurels nécessitent des corrections avant approbation.

---

## Scope compliance

L'implémentation est bornée au ticket. Pas de dérive de scope observée. Le plan approuvé est intégralement implémenté.

Les livrables couverts :
- ✅ Runtime ownership spec (décisions-log.md, runtime-layout.md)
- ✅ Migration bootstrap runtime (deploy/bootstrap.sh)
- ✅ Séparation state_dir / runs_dir
- ✅ Board stable après restart (board_service.py)
- ✅ File logging daemon vers RUNTIME_ROOT/logs/daemon.log
- ⚠️ Invariant checks runtime — **livrable explicite du ticket, absent**
- ⚠️ Suppression DB locales — migration uniquement, pas de cleanup (acceptable per contrainte "migration progressive")

---

## Problème #1 — BLOQUANT : `resolve_state_dir()` / `resolve_logs_dir()` sont du dead code

**Fichier :** `services/control_api/services/runtime_resolver.py:28-41`

Les deux fonctions ajoutées à l'étape 6 du plan ne sont jamais importées ni appelées. `board_service.py` et `run_daemon.py` dupliquent la logique de résolution en ligne chacun de leur côté :

```python
# board_service.py — inline, non extrait
runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
if runtime_root:
    db_path = Path(runtime_root) / ".runtime" / "ai-dev-factory.sqlite"

# run_daemon.py — inline, non extrait
if runtime_root:
    rt = Path(runtime_root)
    state_dir = rt / "state"
```

Résultat : l'abstraction "canonical resolver" existe mais n'est pas utilisée. Si le nom de l'env var change ou si la logique de résolution évolue, elle devra être corrigée à 3 endroits au lieu d'un.

**Correction attendue :** soit utiliser `resolve_state_dir()` dans `board_service.py` et `run_daemon.py`, soit supprimer ces helpers s'ils ne sont pas encore prêts à être intégrés.

---

## Problème #2 — BLOQUANT : `runtime_db.py` — le nouveau fallback crée des DB dans les worktrees

**Fichier :** `tools/agent_runner/runtime_db.py:80-83`

```python
# Dev fallback: this module lives at tools/agent_runner/runtime_db.py,
# so parent.parent.parent resolves to the repo root deterministically.
return Path(__file__).resolve().parent.parent.parent / _DB_FILENAME
```

Ce raisonnement est faux pour les processus workers. Quand `run_ticket.py` est exécuté depuis un worktree, Python charge `runtime_db.py` depuis la copie locale du worktree. `Path(__file__).resolve()` retourne alors `<worktree>/tools/agent_runner/runtime_db.py`, et `.parent.parent.parent` est la racine du worktree — pas le repo principal.

L'**ancien comportement** via `git rev-parse --git-common-dir` renvoyait toujours le common git dir (celui du clone principal), garantissant que tous les processus — y compris ceux lancés depuis des worktrees — partageaient **une seule DB**. Le nouveau fallback brise cette propriété en dev mode.

En Docker (RUNTIME_ROOT set), ce chemin n'est jamais atteint — le bug est donc invisible en production. Mais en dev local, il peut recréer exactement le problème décrit dans le ticket : DB fragmentées par worktree.

Le docstring du module (ligne 5-6) dit encore "resolved from the git common dir so all worktrees share one DB" — il est désormais incorrect.

**Correction attendue :** rétablir le fallback `git common-dir` (supprimer le subprocess uniquement si RUNTIME_ROOT est set, et conserver git common-dir en fallback dev), ou imposer explicitement RUNTIME_ROOT en dev (avec une erreur claire), ou conserver le fallback module-location **uniquement** en documentant qu'il est réservé à des invocations depuis le clone principal.

---

## Problème #3 — MOYEN : Invariant checks absents (livrable explicite du ticket)

Le ticket liste explicitement `invariant checks runtime` comme livrable. Aucun check n'est présent dans l'implémentation.

Un check minimal acceptable serait un avertissement au démarrage du daemon si `AI_DEV_FACTORY_RUNTIME_ROOT` n'est pas set (`_log("WARNING: AI_DEV_FACTORY_RUNTIME_ROOT not set — using dev fallback path")`), ou une assertion dans `bootstrap.sh` vérifiant que la DB canonique existe après migration.

---

## Observations non-bloquantes

**`runtime_resolver.py:64` — `_load_workers` lit depuis `runs_dir`, pas `state_dir`**

La fonction `resolve_ticket_run_dir()` charge le workers registry depuis `runs_dir` (inchangé). Désormais que `workers.json` vit dans `state_dir`, cette lookup peut rater si le registry a migré. Cohérence à vérifier.

**`board_service.py:_load_runtime_db` — double résolution RUNTIME_ROOT**

`get_board` résout déjà `rt = Path(runtime_root)` puis passe `project_root` à `_load_runtime_db`, qui relit RUNTIME_ROOT en interne. Doublon sans conséquence fonctionnelle, mais incohérent.

**`bootstrap.sh` — migration sans cleanup**

Le ticket énonce des "interdictions" dures (aucune DB dans worktree/clone). La migration copie vers la cible mais ne supprime pas les sources. En l'absence de cleanup, les anciennes DBs continuent d'exister — leur présence ne cause pas de régression immédiate grâce aux fix code, mais viole la lettre du ticket. Acceptable per la contrainte "migration progressive" mais à documenter comme dette.

---

## Bilan par livrable

| Livrable | Statut |
|---|---|
| Runtime ownership spec (docs) | ✅ |
| Migration bootstrap | ✅ |
| Suppression DB locales | ⚠️ Migration sans cleanup (acceptable) |
| Cleanup runtime artifacts | ⚠️ Non implémenté |
| Runtime hydration Docker | ✅ (bootstrap.sh copie la DB) |
| Board stable après restart | ✅ |
| Invariant checks runtime | ❌ Absent |
| Documentation architecture | ✅ |

---

## Corrections requises avant approbation

1. **Utiliser `resolve_state_dir()` / `resolve_logs_dir()`** dans `board_service.py` et `run_daemon.py`, ou supprimer ces fonctions du resolver — elles ne doivent pas rester du dead code.
2. **Corriger le fallback `runtime_db.py`** pour éviter la création de DB dans les worktrees en dev mode. Rétablir `git common-dir` comme fallback dev, ou imposer RUNTIME_ROOT avec une erreur explicite.
3. **Ajouter un invariant check minimal** au démarrage du daemon (warning ou error si RUNTIME_ROOT absent en contexte non-dev, ou log explicite du path résolu au démarrage).

IMPLEMENTATION_FIX_REQUIRED
