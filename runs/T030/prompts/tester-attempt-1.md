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


# T030 — T030 — Live daemon activity feed and auto-refresh

**Source**: GitHub Issue #30

## Description

# T030 — Live daemon activity feed and auto-refresh

## Contexte

Le système dispose maintenant :

- d’un daemon d’orchestration
- d’une Control API REST
- d’un dashboard UI React
- de tickets pilotables depuis l’UI

Mais l’UI reste principalement statique.

Les tickets ne se mettent pas à jour automatiquement et les logs/runtime nécessitent des refresh manuels.

Le prochain cap est d’obtenir une expérience “runtime vivant” permettant de suivre l’activité du daemon en quasi temps réel.

Architecture cible :

```text
Daemon runtime
↓
Control API
↓
Dashboard auto-refresh
```

## Objectif

Ajouter un système de rafraîchissement automatique et un feed d’activité daemon.

Le dashboard doit montrer les changements runtime sans nécessiter de refresh manuel.

## Inclus

### 1. Auto-refresh tickets list

`TicketsPage` doit se rafraîchir automatiquement.

Exemple :

```text
polling 5s
```

Les changements d’état doivent apparaître automatiquement :

```text
PLANNER_RUNNING
→ PLAN_REVIEW_NEEDED
→ CODER_RUNNING
→ IMPLEMENTATION_REVIEW_NEEDED
```

### 2. Auto-refresh TicketDetailPage

Quand un ticket est ouvert :

- refresh automatique de `state.json`
- refresh automatique des logs
- refresh automatique des reviews/tests/artefacts si le ticket change

### 3. Daemon activity feed

Ajouter un panneau montrant les dernières activités daemon.

Exemples :

```text
[10:41:02] daemon started
[10:41:18] T030 planner started
[10:41:44] T030 PLAN_REVIEW_NEEDED
[10:42:01] T030 coder started
```

Le feed peut être basé sur :

```text
runtime.log
ou
un nouveau daemon.log
```

### 4. Live daemon status

Le statut daemon doit être rafraîchi automatiquement.

Exemple :

```text
running
stopped
last heartbeat
current ticket
```

### 5. Polling management

Le polling doit être proprement nettoyé :

- `clearInterval`
- pas de memory leak
- pas de polling multiple accidentel

### 6. UX minimale

Ajouter :

- indicateurs loading subtils
- badges runtime plus vivants
- indication “updated X seconds ago” si simple à implémenter

Pas de design avancé requis.

### 7. Tests

Ajouter des tests pour :

- polling lifecycle
- cleanup interval
- refresh automatique
- daemon feed rendering
- changement d’état runtime

## Hors scope

- websocket
- SSE
- push realtime serveur
- auth
- multi-user
- notifications push
- mobile app
- animations avancées
- terminal intégré

## Critères d’acceptation

- les tickets se rafraîchissent automatiquement
- TicketDetailPage se met à jour automatiquement
- le statut daemon est live
- un feed daemon existe
- les changements runtime apparaissent sans refresh manuel
- aucun polling zombie
- les tests couvrent les mécanismes de polling
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
apps/dashboard/
services/control_api/
tests/
README.md
```