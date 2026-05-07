# Plan T008 — mode `--auto` (v2)

## Contexte

T008 ajoute un mode `--auto` au runner `run_ticket.py` pour orchestrer un ticket étape par étape avec gates stricts et logs visibles. Chaque invocation exécute exactement une étape. L'humain re-invoque. Pas de boucle automatique, pas de merge.

Ce plan (v2) corrige le plan v1 : `workflow-status.md` n'est plus la source de vérité de l'état. `runs/TXXX/state.json` est le fichier canonique. `workflow-status.md` devient un journal humain append-only.

## Objectif

Ajouter `--auto` et `--auto-init` dans `run_ticket.py`, avec :
- `state.json` comme source de vérité canonique
- gates stricts bloquants avant chaque étape
- détection de mots-clés dans les sorties review
- `workflow-status.md` uniquement comme journal lisible par un humain

## Fichiers concernés

| Fichier | Action |
|---|---|
| `tools/agent_runner/run_ticket.py` | Modifier — ajouter `--auto`, `--auto-init`, state machine, gates |
| `README.md` | Modifier — documenter `--auto` et `--auto-init` |
| `tools/agent_runner/run_step.py` | Aucune modification |
| `runs/TXXX/state.json` | Créé à l'exécution de `--auto-init` (non versionné directement) |

## Structure de `state.json`

```json
{
  "ticket_id": "T008",
  "state": "PLAN_REVIEW_NEEDED",
  "branch": "ticket/T008-auto-workflow-runner",
  "updated_at": "2026-05-08T10:00:00Z"
}
```

## États valides

```
INIT
PLAN_REVIEW_NEEDED
PLAN_FIX_REQUIRED
PLAN_APPROVED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_FIX_REQUIRED
IMPLEMENTATION_APPROVED
TEST_COMPLETE
```

## Table des transitions autorisées

| État courant | Étape lancée | Déclencheur | État suivant |
|---|---|---|---|
| `INIT` | `planner` | déterministe | `PLAN_REVIEW_NEEDED` |
| `PLAN_REVIEW_NEEDED` | `review` | mot-clé `PLAN_APPROVED` | `PLAN_APPROVED` |
| `PLAN_REVIEW_NEEDED` | `review` | mot-clé `PLAN_FIX_REQUIRED` | `PLAN_FIX_REQUIRED` |
| `PLAN_FIX_REQUIRED` | `planner` | déterministe | `PLAN_REVIEW_NEEDED` |
| `PLAN_APPROVED` | `coder` | déterministe | `IMPLEMENTATION_REVIEW_NEEDED` |
| `IMPLEMENTATION_REVIEW_NEEDED` | `review` | mot-clé `IMPLEMENTATION_APPROVED` | `IMPLEMENTATION_APPROVED` |
| `IMPLEMENTATION_REVIEW_NEEDED` | `review` | mot-clé `IMPLEMENTATION_FIX_REQUIRED` | `IMPLEMENTATION_FIX_REQUIRED` |
| `IMPLEMENTATION_FIX_REQUIRED` | `coder` | déterministe | `IMPLEMENTATION_REVIEW_NEEDED` |
| `IMPLEMENTATION_APPROVED` | `tester` | déterministe | `TEST_COMPLETE` |
| `TEST_COMPLETE` | — | fin, pas de merge | — |

Toute transition non listée ci-dessus est invalide et bloque avec exit code 2.

## Étapes d'implémentation

### 1. `--auto-init` dans `run_ticket.py`

Nouveau flag `--auto-init` (accompagné de `--branch-slug`).

Comportement :
- Vérifie que la branche courante correspond à `ticket/TXXX-<slug>` (erreur si incohérente).
- Vérifie que `state.json` n'existe pas déjà (erreur si présent, pour éviter l'écrasement silencieux).
- Crée `runs/TXXX/state.json` avec `"state": "INIT"`, `"branch": <branche courante>`, `"ticket_id"`, `"updated_at"`.
- Affiche un message de confirmation.

### 2. Helpers `load_state()` / `save_state()` dans `run_ticket.py`

`load_state(ticket_id)` :
- Résout `runs/TXXX/state.json`.
- Erreur code 2 si absent : `"state.json not found — run --auto-init first"`.
- Erreur code 2 si JSON invalide : `"state.json is corrupted"`.
- Erreur code 2 si `state` absent ou inconnu : `"unknown state: {value}"`.
- Retourne le dict.

`save_state(ticket_id, state_dict)` :
- Met à jour `"updated_at"` avec l'heure courante ISO 8601.
- Écrit `state.json` de façon atomique (write + rename).

### 3. Gates pré-exécution dans `auto_run()`

Vérifications séquentielles, chacune bloque avec exit code 2 si elle échoue :

1. `state.json` existe et est valide (via `load_state()`).
2. `state` est un état connu.
3. `state` est différent de `TEST_COMPLETE` (si `TEST_COMPLETE` → exit 0 avec message "workflow complete — no automatic merge").
4. Branche git courante correspond à `state["branch"]` — `git rev-parse --abbrev-ref HEAD`.
5. Working tree propre — `git status --porcelain` doit être vide.

### 4. `auto_run()` — orchestration d'une étape

Logique principale :

```
state = load_state(ticket_id)
pre_flight_checks(state)
step, is_deterministic = resolve_step(state["state"])
stdout = call_run_step(ticket_id, step, exec_cmd)   # via run_step.py --exec-cmd
next_state = determine_next_state(state["state"], is_deterministic, stdout)
save_state(ticket_id, {**state, "state": next_state})
append_workflow_journal(ticket_id, state["state"], step, next_state)
```

`determine_next_state()` pour les étapes review :
- Cherche les mots-clés exacts dans stdout (ex. `PLAN_APPROVED`, `PLAN_FIX_REQUIRED`).
- Si aucun mot-clé → warning visible, état inchangé, exit code 1.
- Si plusieurs mots-clés → warning (premier trouvé utilisé).

`append_workflow_journal()` :
- Ajoute une entrée datée à `workflow-status.md` : état précédent, étape, état suivant.
- Ne lit jamais `workflow-status.md` pour décider de l'état.

### 5. Ajout du flag `--auto` dans `parse_args()` et `main()`

```python
parser.add_argument("--auto", action="store_true", help="Execute next workflow step (reads state.json)")
parser.add_argument("--auto-init", action="store_true", help="Initialize state.json for --auto mode")
```

Dans `main()` :
- `--auto-init` → `init_auto(ticket_id, args.branch_slug)`
- `--auto` sans `--exec-cmd` → exit code 2 : `"--exec-cmd is required with --auto"`
- `--auto` avec `--exec-cmd` → `auto_run(ticket_id, args.exec_cmd)`

### 6. README — section `--auto`

Ajouter une section documentant :
- `--auto-init --branch-slug <slug>` : prérequis, crée `state.json`
- `--auto --exec-cmd <cmd>` : exécute une étape, lit/écrit `state.json`
- Exemple de session complète (7 invocations pour INIT → TEST_COMPLETE)
- Invariants : pas de merge, pas de boucle, exit non-zéro sur gate bloquant

## Risques

| Risque | Mitigation |
|---|---|
| `state.json` écrasé silencieusement lors de `--auto-init` | Vérification d'existence avant création, exit code 2 si présent |
| Keyword review détecté à tort (ex. dans un commentaire ou extrait de code) | Cherche le mot-clé seul sur une ligne (regex `^KEYWORD$` multilignes) |
| Working tree dirty après une étape partielle | Gate 5 bloque la prochaine invocation jusqu'à commit/stash |
| Branche divergente (checkout manuel entre deux invocations) | Gate 4 détecte l'incohérence branche et bloque |
| `run_step.py` modifie `workflow-status.md` en parallèle | `run_step.py` n'est pas modifié ; son écriture dans `workflow-status.md` reste présente mais n'est jamais lue par `--auto` |

## Hors scope

- Merge automatique
- Ouverture automatique de PR
- Review distante via API
- Watcher permanent ou boucle automatique
- Modification de `run_step.py`
- Migration de l'existant `workflow-status.md` vers `state.json`

## Vérifications prévues

1. `--auto-init` crée `state.json` valide avec état `INIT`.
2. `--auto-init` refuse de réinitialiser si `state.json` existe déjà.
3. `--auto` sans `state.json` → exit code 2 avec message clair.
4. `--auto` avec `state.json` corrompu → exit code 2.
5. `--auto` sur mauvaise branche → exit code 2.
6. `--auto` avec working tree sale → exit code 2.
7. `--auto` depuis `TEST_COMPLETE` → exit code 0, message "workflow complete".
8. `--auto` sans `--exec-cmd` → exit code 2.
9. Séquence complète INIT → TEST_COMPLETE (7 étapes) produit les états attendus.
10. Absence de mot-clé dans sortie review → warning + état inchangé + exit code 1.

## Critères d'acceptation

- `run_ticket.py --auto` et `--auto-init` existent
- `state.json` est l'unique source de vérité de l'état courant
- `workflow-status.md` est append-only journal (jamais lu pour décider l'état)
- Gates pré-exécution stricts : 5 vérifications, chacune bloque avec exit code non-zéro
- Pas de merge automatique
- Pas de boucle automatique (une étape par invocation)
- README mis à jour avec exemples d'utilisation
