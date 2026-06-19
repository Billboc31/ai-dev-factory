# Test Report — T196

**Date**: 2026-06-19  
**Branch**: ticket/T196-t196-add-ui-action-to-install-agent-layout-on-exis  
**Tester**: Claude (Sonnet 4.6)

---

## Summary

**VALIDATION: PASS**

All 8 acceptance criteria are met. 28 unit/integration tests pass. No regressions introduced.

---

## Acceptance Criteria

### AC1 — Existing imported projects have a UI button to install/regenerate the agent layout

**PASS**

`ProjectDashboardPage.jsx:196-201` renders an `ActionButton` labelled "Install agent layout" on the project detail page. It calls `installAgentLayout(projectId)` on click.

**Minor (non-blocking):** The button label is always "Install agent layout" regardless of whether the layout already exists. The ticket suggests switching to "Regenerate agent layout / docs" when `ai/` is already present. This is a UX improvement, not a blocking defect.

---

### AC2 — The action creates or updates `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/`

**PASS**

`install_agent_layout.py:116-152` (`_ensure_layout_dirs`) creates all five directories idempotently:
- `ai/roles/`, `ai/skills/`, `ai/templates/` — copied from factory, existing files preserved
- `prompts/generic/` — copied from factory, existing files preserved
- `runs/`, `tickets/` — created with `.gitkeep`
- `docs/` — created by the doc-writing loop

Test coverage: `test_install_creates_layout_dirs`, `test_install_creates_docs_folder`.

---

### AC3 — `docs/` is generated from AI repository analysis, not empty placeholders

**PASS**

`scan_and_build_prompt()` (docs_prompt_builder.py) builds a rich context by scanning README, package.json, pyproject.toml, Dockerfile, docker-compose files, src/, services/, tests/ and more, with a 4 KB cap per file and a 4-level file tree. The prompt is then passed to Claude via `_invoke_llm()`.

10 required base docs are mandated and 14 conditional docs are generated when evidence is found. Empty LLM outputs are skipped with a warning rather than written as empty files.

Test coverage: `test_install_creates_all_required_base_docs`, `test_scan_and_build_prompt_contains_required_doc_names`, `test_install_generates_conditional_docs_when_present`.

---

### AC4 — The action creates a branch and opens a PR in the target project

**PASS**

`install_agent_layout.py:235-393`:
- Creates branch `ai-dev-factory/install-agent-layout` (new layout) or `ai-dev-factory/update-agent-docs` (existing layout)
- Pushes branch to origin
- Checks for existing open PR on that branch (`gh pr list --head`)
- Creates a new PR via `gh pr create` with a structured body including analysis summary, doc list, warnings, and human review TODOs

Test coverage: `test_install_commits_on_setup_branch`, `test_install_no_remote_returns_no_pr_url`.

---

### AC5 — It does not commit directly to the default branch

**PASS**

The code always checks out a feature branch (`INSTALL_BRANCH` or `UPDATE_BRANCH`) before making any changes. The default branch is only used as the `--base` for the PR. There is no code path that commits to main/master.

Test coverage: `test_install_commits_on_setup_branch`, `test_install_uses_install_branch_for_new_project`, `test_install_uses_update_branch_when_layout_exists`.

---

### AC6 — It reuses the existing project runtime and registration

**PASS**

`control_api/routes/projects.py:200-202`:
```python
registry = request.app.state.project_registry
project_root = registry.resolve(project_id)
```
Uses the existing project registry without re-importing or re-bootstrapping. The supervisor maps the path using `mapper.map()` and calls `install_agent_layout()` with the resolved path.

---

### AC7 — It is safe/idempotent for projects where the layout already exists

**PASS**

- `_layout_exists()` detects an existing layout (`ai/` directory) and switches to `UPDATE_BRANCH`
- `_ensure_layout_dirs()` uses `if not (dst / f.name).exists()` guards — never overwrites existing files
- `docs/ai/global-context.md` is only written if it doesn't exist
- If nothing to commit, the function returns early with a success result (no error)
- Path validation (`_validate_doc_path`) rejects absolute paths and traversal attempts from LLM output

Test coverage: `test_install_is_idempotent_no_remote`, `test_install_rejects_path_traversal`, `test_install_rejects_absolute_paths`.

---

### AC8 — UI shows PR URL, warnings, and analysis summary

**PASS**

`ProjectDashboardPage.jsx:222-279` renders a result card with:
- PR URL as a clickable external link (`layoutResult.pr_url`)
- Branch name in monospace (`layoutResult.branch`)
- Analysis summary in italic (`layoutResult.analysis_summary`)
- Doc count and list of generated file paths
- Warnings list in orange when non-empty
- Error message in red when the operation fails

---

## Regressions

**None introduced by T196.**

119 pre-existing failures across `test_sandbox_worktree`, `test_ticket_timeline`, `test_traefik_separation`, and `test_runtime_db` are present identically on `main` and are unrelated to this ticket.

---

## Test Suite Results

```
tests/test_install_agent_layout.py — 28/28 PASSED (2.36s)
```

Tests cover:
- Helper unit tests: `_layout_exists`, `_validate_doc_path`, `_parse_file_blocks`
- Prompt builder: required docs coverage, file scanning, directory listing
- Integration: layout dir creation, doc generation, branch selection, idempotency
- Security: path traversal rejection, absolute path rejection, non-markdown rejection
- Edge cases: no remote, LLM failure, nothing-to-commit

---

## Minor Observations (non-blocking)

| # | Observation | Impact |
|---|-------------|--------|
| 1 | Button label is always "Install agent layout" even when layout exists | UX: missing "Regenerate" label variant |
| 2 | `exec_cmd` is not forwarded from control API to supervisor (uses default) | Benign: default is correct; no customisation path from UI |
| 3 | `docs/ai/global-context.md` is not included in `docs_paths` / `docs_count` | Minor: reported count understates actual files written by 1 |
| 4 | File tree has cosmetic rendering issue when last entry is a skipped dir | No functional impact |

None of these are blocking for merge.
