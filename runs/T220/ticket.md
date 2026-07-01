# T220 — Improve Global Dependency Analyzer to produce coherent execution phases and foundation ordering

**Source**: GitHub Issue #297

## Description

# Context

The Global Dependency Analyzer is now responsible for building a dependency graph for a backlog batch.

During testing on the `test-ai-dev` repository, the analyzer produced an inconsistent graph:

- T001 (project vision / architecture) was placed in the same execution phase as T010.
- At the same time, the analyzer reported `T001 conflicts with T010`.

Those two statements cannot both be true.

The analyzer must produce a coherent dependency graph that can be consumed safely by the Dispatcher.

# Goal

Improve the Global Dependency Analyzer prompt, reasoning process, and output consistency.

The objective is to generate a dependency graph that reflects how an experienced software architect would plan implementation work.

# Improvements

## 1. Detect foundation tickets

Detect tickets whose purpose is to:

- define product vision
- define architecture
- define technical stack
- define conventions
- bootstrap the project

Classify them as foundation/bootstrap tickets.

These tickets should naturally appear before implementation tickets.

## 2. Improve dependency inference

Infer implicit dependencies such as:

- architecture → bootstrap
- bootstrap → backend/frontend foundations
- backend API → frontend consuming the API
- infrastructure → features
- features → integration
- implementation → testing

The analyzer should propose dependencies even when they are not explicitly written in GitHub.

## 3. Produce coherent execution phases

Execution phases represent tickets that may safely execute in parallel.

Rules:

- if A depends on B then phase(A) > phase(B)
- tickets in the same phase must be parallel compatible
- foundation tickets should normally occupy the earliest phases

## 4. Resolve conflicts consistently

If two tickets are marked as conflicting:

- they must not be placed in the same execution phase
- or the analyzer must remove the conflict if they are actually parallel compatible

The output must never simultaneously state:

- same execution phase
- conflicting tickets

for the same ticket pair.

## 5. Strengthen prompting

Update the analyzer prompt to reason globally over the entire backlog before assigning:

- dependencies
- conflicts
- execution phases
- parallel groups

The model should first build a conceptual implementation plan, then derive the graph.

# Acceptance criteria

- Foundation tickets are detected reliably.
- Execution phases respect dependency ordering.
- No conflicting tickets appear in the same parallel phase.
- Implicit architectural dependencies are inferred when appropriate.
- The dependency graph is internally consistent and suitable for Dispatcher scheduling.
- Existing dependency analysis tests are updated and extended with realistic project scenarios (including the `test-ai-dev` backlog).
