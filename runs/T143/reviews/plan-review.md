# Plan review — T143

Decision: PLAN_FIX_REQUIRED

The current T143 plan is too large and too risky for a first conflict-management implementation.

It combines:

- workflow state machine changes
- automatic conflict detection
- automatic rebases
- AI conflict resolution
- force-with-lease pushes
- dashboard changes
- API changes
- context orchestration
- review lifecycle changes

This should be split into smaller and safer runtime iterations.

The first implementation should focus on:

- conflict detection
- conflict workflow states
- dashboard visibility
- preserving ticket state

before introducing automatic AI-driven rebases and branch rewriting.

See `runs/T143/fixes/plan-fix-1.md`.
