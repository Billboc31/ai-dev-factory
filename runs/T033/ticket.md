# T033 — T033 — Automatic workflow checkpoint commits after daemon/intake steps

**Source**: GitHub Issue #37

## Description

# T033 — Automatic workflow checkpoint commits after daemon/intake steps

## Contexte

Les tests runtime réels du daemon ont révélé un invariant manquant dans le workflow.

Aujourd’hui, le système peut :

```text
issue intake
→ création branche
→ création runs/TXXX
→ génération artefacts
→ changement state.json
```

mais certains fichiers restent non commités avant l’étape suivante.

Le daemon se bloque alors lui-même avec :

```text
error: working tree is not clean — commit or stash changes first
```

Les causes observées pendant T032 :

- `runs/T032/workflow-status.md`
- `runs/T032/daemon.lock`
- artefacts runtime générés entre deux cycles daemon

Le workflow doit devenir auto-stabilisant.

---

## Objectif

Introduire des checkpoint commits automatiques après les mutations workflow importantes.

Le daemon ne doit jamais tenter de lancer une étape auto-runnable avec un working tree dirty causé par ses propres artefacts.

---

## Invariant cible

Le workflow cible devient :

```text
step success
→ persist artefacts
→ checkpoint commit
→ push
→ next daemon cycle allowed
```

Et pour intake :

```text
GitHub issue
→ intake
→ create branch
→ create runs/TXXX
→ bootstrap checkpoint commit
→ push
→ workflow execution
```

---

## Travail demandé

### 1. Ajouter bootstrap checkpoint après intake

Après succès de `run_issue_intake.py`, le système doit automatiquement :

```text
commit bootstrap artefacts
push branch
```

Artefacts concernés typiquement :

```text
runs/.issue-intake.json
runs/TXXX/
```

Le commit doit utiliser le système canonique existant.

Ne jamais utiliser :

```bash
git add .
```

---

### 2. Ajouter checkpoint automatique après étapes workflow

Quand une étape réussit et produit des artefacts persistants :

- PLAN_REVIEW_NEEDED
- IMPLEMENTATION_REVIEW_NEEDED
- TEST_COMPLETE
- approvals humaines
- transitions importantes

le système doit automatiquement :

```text
checkpoint commit
push
```

avant le prochain cycle daemon.

---

### 3. Ignorer les fichiers runtime transitoires

Ajouter à `.gitignore` :

```gitignore
runs/daemon.log
runs/daemon.pid
runs/*/daemon.lock
runs/*/workflow-status.md
```

Ces fichiers runtime ne doivent jamais bloquer le workflow Git.

---

### 4. Garantir working tree clean avant exécution auto

Avant chaque lancement automatique de :

```bash
run_ticket.py TXXX --auto
```

le daemon doit garantir :

```text
working tree clean
```

Si le dirty state provient d’artefacts workflow persistants :

→ checkpoint commit automatique

Si le dirty state provient de fichiers inconnus/utilisateur :

→ abort sécurisé

---

### 5. Ajouter logs explicites

Ajouter des logs du type :

```text
checkpoint commit for T033
checkpoint push for T033
bootstrap checkpoint completed
```

et logs explicites si abort sécurité.

---

## Contraintes

- `run_ticket.py` reste le moteur workflow canonique
- aucune duplication Git dans le dashboard
- aucune modification directe arbitraire de `state.json`
- ne jamais utiliser `git add .`
- respecter `COMMIT_SCOPE`
- conserver les guardrails humains

---

## Critères d’acceptation

- un ticket intake peut être exécuté entièrement par le daemon sans intervention Git manuelle
- les étapes workflow ne laissent pas le repo dirty entre deux cycles
- les fichiers runtime transitoires ne polluent plus Git
- le daemon peut enchaîner plusieurs cycles sans blocage working tree
- les commits/push automatiques utilisent les scripts canoniques existants
- aucun `git add .`
- les logs runtime rendent les checkpoints observables
