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


# T025 — T025 — Daemon retry and cooldown policy

**Source**: GitHub Issue #19

## Description

# T025 — Daemon retry and cooldown policy

## Contexte

Le daemon peut maintenant :

- détecter des issues GitHub `ai-ready`
- créer des runs locaux
- lancer le workflow planner/coder/reviewer/tester
- orchestrer les étapes auto-runnable

Mais les erreurs runtime provider ne sont pas encore gérées intelligemment.

Exemple réel :

```text
Claude quota exceeded
→ daemon retry immédiat
→ boucle infinie
```

Le système doit maintenant supporter des politiques de retry et cooldown robustes.

## Objectif

Ajouter une politique de retry/cooldown pour les failures runtime détectées par T018.

Le daemon doit :

- classifier les failures
- appliquer un cooldown adapté
- éviter les retries infinis
- conserver les runs dans un état cohérent
- logguer clairement les décisions de retry/pause

## Inclus

- stockage local des retry states daemon
- cooldown provider quota
- retry exponentiel provider_error
- retry limité process_failed
- arrêt explicite sur write_permission_missing
- logs explicites
- tests ciblés

## Exemples attendus

```text
quota_exceeded
→ cooldown 1h
```

```text
provider_error
→ retry exponentiel
```

```text
write_permission_missing
→ stop + human attention
```

## Contraintes

- `run_ticket.py` reste le moteur workflow
- la classification runtime existante (T018) reste la source de vérité
- le daemon applique seulement des policies de retry
- aucun retry infini
- aucun état workflow cassé

## Hors scope

- model routing
- multi-provider balancing
- UI web
- notifications push
- PR automation
- distributed workers

## Critères d’acceptation

- un quota exceeded ne boucle pas infiniment
- les retries sont limités et traçables
- les cooldowns sont persistés
- les logs daemon sont explicites
- les tests couvrent les policies principales
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tests/
README.md
```