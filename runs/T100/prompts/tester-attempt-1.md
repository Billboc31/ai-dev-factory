# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

The ticket follows.


# T100 — T034 — Visual workflow timeline in dashboard

**Source**: GitHub Issue #38

## Description

# T034 — Visual workflow timeline in dashboard

## Contexte

Après T032/T033, le daemon commence à exécuter réellement le workflow depuis les issues GitHub.

Le dashboard affiche déjà les logs, mais en runtime réel ils deviennent difficiles à lire.

Aujourd’hui, pour comprendre ce qu’il se passe entre les étapes, il faut lire :

```text
runs/daemon.log
runs/TXXX/runtime.log
runs/TXXX/state.json
runs/TXXX/retry-state.json
```

Ce n’est pas assez lisible pour piloter le workflow depuis l’IHM.

---

## Objectif

Ajouter dans le dashboard une vue visuelle du workflow d’un ticket.

L’utilisateur doit voir rapidement :

- l’étape courante
- l’agent en cours ou attendu
- les étapes terminées
- les gates humaines
- les erreurs éventuelles
- les checkpoints Git/push/PR
- le dernier événement important

---

## Vue cible

Dans la page détail d’un ticket, ajouter une timeline visuelle du type :

```text
Issue intake ✅
Plan ✅
Plan review ✅
Implementation ⚙️ running coder
Implementation review ⏸ waiting human
Fix loop
Tests
Checkpoint / push
PR
Done
```

La vue doit permettre de comprendre l’état sans lire les logs bruts.

---

## Travail demandé

### 1. Ajouter un endpoint API timeline

Ajouter un endpoint :

```text
GET /tickets/{ticket_id}/timeline
```

Il doit retourner une structure simple et stable, par exemple :

```json
{
  "ticket_id": "T034",
  "current_state": "PLAN_APPROVED",
  "current_agent": "coder",
  "human_gate": false,
  "last_event": "Launching coder",
  "steps": [
    {
      "id": "issue_intake",
      "label": "Issue intake",
      "status": "done"
    },
    {
      "id": "plan",
      "label": "Plan",
      "status": "done"
    },
    {
      "id": "implementation",
      "label": "Implementation",
      "status": "running",
      "agent": "coder"
    }
  ]
}
```

Statuses possibles :

```text
pending
running
done
waiting_human
failed
skipped
```

---

### 2. Déduire la timeline depuis les artefacts existants

La timeline doit être dérivée uniquement des artefacts existants :

```text
runs/TXXX/state.json
runs/TXXX/plan.md
runs/TXXX/review.md
runs/TXXX/tests.md
runs/TXXX/runtime.log
runs/TXXX/retry-state.json
runs/TXXX/fixes/
runs/.issue-intake.json
```

Ne pas introduire une deuxième state machine.

La timeline est une projection de l’état runtime, pas une nouvelle source de vérité.

---

### 3. Ajouter le composant UI

Dans le dashboard, sur la page détail ticket, ajouter un composant du type :

```text
WorkflowTimeline
```

Il doit afficher :

- les étapes sous forme de timeline ou stepper
- l’étape courante mise en évidence
- l’agent courant si connu
- les gates humaines
- les erreurs récentes
- le dernier checkpoint si disponible

---

### 4. Garder les logs accessibles

Les logs restent disponibles, mais deviennent une vue secondaire de diagnostic.

La timeline devient la vue principale pour comprendre l’avancement.

---

### 5. Tests

Ajouter des tests API pour :

- ticket INIT
- PLAN_REVIEW_NEEDED
- PLAN_APPROVED
- IMPLEMENTATION_REVIEW_NEEDED
- IMPLEMENTATION_FIX_REQUIRED
- TEST_COMPLETE
- état avec retry-state/error

Ajouter si possible un test UI léger ou au minimum vérifier que le composant supporte les statuts attendus.

---

## Contraintes

- Ne pas dupliquer la state machine de `run_ticket.py`
- Ne pas modifier directement `state.json`
- L’API doit seulement lire les artefacts
- Le dashboard reste client de la Control API
- Ne pas masquer les logs existants
- Garder une structure JSON simple et stable

---

## Critères d’acceptation

- `GET /tickets/{ticket_id}/timeline` existe
- la page détail ticket affiche une timeline visuelle
- l’utilisateur peut identifier rapidement l’étape courante
- les gates humaines sont visibles
- les erreurs/retries sont visibles si présents
- les logs restent accessibles
- aucun nouveau moteur workflow n’est introduit dans l’API ou l’UI