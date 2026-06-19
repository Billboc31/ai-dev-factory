The plan has been written to `runs/T196/plan.md`. Here is what it contains:

**## Objective** — One clear sentence: UI button on project detail page triggers AI repo analysis, generates dynamic `docs/`, creates standard agent layout, opens a PR without committing to default branch.

**## Included** — Eight concrete deliverables:
1. `docs_prompt_builder.py` — repo scanner + Claude prompt builder (10 required base docs + 14 conditional docs based on detected signals)
2. `install_agent_layout.py` — orchestrator: calls Claude, parses a variable number of FILE blocks, validates paths, reuses T195 bootstrap, creates PR
3. `InstallAgentLayoutResult` schema with `docs_paths: list[str]` and `docs_count: int`
4. Supervisor endpoint `POST /projects/{id}/install-agent-layout`
5. Control API endpoint proxying to supervisor
6. Dashboard API client function
7. UI button + result card showing dynamic doc count, path list, PR URL, warnings
8. Tests covering variable doc generation, conditional docs, path validation rejection, missing base docs, and idempotency

**## Excluded** — No re-importing, no batch operations, no scheduled re-analysis, no diff-merge of user edits.

**## Acceptance criteria** — 13 verifiable conditions, none of which mention "exactly six files."
