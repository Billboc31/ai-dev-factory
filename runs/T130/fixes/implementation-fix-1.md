# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T130/reviews/implementation-review.md
- generated at: 2026-05-21T21:29:35Z

---

I now have enough information to write the review.

---

# Review — T130: AI-assisted operational project analysis and deploy profile generation

## Summary

The implementation is architecturally clean and covers the majority of ticket requirements: the "Analyze Project" button is present, LLM invocation is environment-driven, file generation follows the specified schema, git branching and PR creation/update are implemented, and the dashboard surfaces status and logs. The layering (worker → supervisor → control API → frontend) mirrors the existing deployer pattern correctly.

However, there are two blocking issues that prevent approval.

---

## Blocking Issues

### 1. Missing required tests — AI execution orchestration and file generation

The ticket explicitly requires:
> Add tests for: prompt generation, **AI execution orchestration**, **file generation**, Git branch workflow, PR creation/update

The implementation provides:
- ✅ `test_analysis_prompt_builder.py` — prompt generation (4 tests)
- ✅ `test_analysis_git_service.py` — git branch, PR create, PR update
- ✅ `test_analysis_manager.py` — HTTP proxy

But **no tests exist** for `run_analysis.py`, which contains:
- `_extract_files(llm_output)` — the regex file block parser, which is the most critical parsing logic
- `_scan_project(path)` — project scanner
- `_build_file_tree(path)` — tree generator
- The orchestration flow in `main()` (state machine: scan → prompt → LLM → parse → validate → write → commit)

`_extract_files` in particular is non-trivial: it's a regex over LLM output that the whole workflow depends on. A test like "given a well-formed LLM response, returns the three expected files" and "given a response missing deploy.yml, raises RuntimeError" is straightforward to write and directly covers a ticket acceptance criterion.

These tests were explicitly named in the ticket scope and are absent.

### 2. Path traversal in `run_analysis.py` via LLM-generated file paths

In `run_analysis.py:186-189`:

```python
for rel_path, content in generated_files.items():
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

The `rel_path` comes directly from LLM output regex capture groups. If the LLM (or a prompt injection via the file tree) returns a path like `../../sensitive_file`, `target` resolves outside `project_root`. The `required` check only validates that two specific paths are present — it does not prevent arbitrary additional paths from being written anywhere.

Fix: validate all extracted paths stay within `.ai-dev-factory/` before writing:

```python
for rel_path, content in generated_files.items():
    if not rel_path.startswith(".ai-dev-factory/"):
        raise RuntimeError(f"LLM returned unexpected path outside .ai-dev-factory/: {rel_path}")
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

---

## Important Observation (Non-Blocking)

### `--print` flag hardcoded in `_invoke_llm()`

`run_analysis.py:115`:
```python
cmd_parts = shlex.split(exec_cmd) + ["--print"]
```

The ticket states: *"use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider."* Appending `--print` unconditionally ties the implementation to the Claude CLI interface. A different `exec_cmd` (e.g., an OpenAI proxy or a local model) would need to accept `--print`. This is an architectural tension with the ticket's stated intent.

This is non-blocking because the existing daemon already uses Claude CLI exclusively, and the `exec_cmd` is a Claude CLI invocation in practice. But it should be noted in runtime documentation or addressed if multi-provider support is a real near-term requirement.

---

## Minor Observations (Non-Blocking)

- `analysis_git_service.py`: `git checkout -b {branch}` runs from whatever branch the project is currently on, with no prior `git fetch` or `git checkout main`. If the managed repo is mid-operation or on a non-default branch, the analysis branch will diverge from the wrong base. Low-risk in current usage; worth a note.

- `analysis_git_service.py`: `gh pr create` has no `--base` argument. Defaults to the repo's default branch, which is correct in nearly all cases.

- `supervisor/main.py:283`: `from fastapi.responses import JSONResponse` imported inside the endpoint function body. Functional, but inconsistent with module-level imports used elsewhere.

- `AnalysisStatusPanel` returns `null` for `idle` state, so there's no visual indication that analysis has never run, unlike the deploy status panel which is always visible. Minor UX inconsistency.

---

## Acceptance Criteria Check

| Criterion | Status |
|---|---|
| "Analyze Project" button in dashboard | ✅ |
| LLM analyzes repo via configured runtime | ✅ |
| Generates deploy.yml compatible with deployer runtime | ✅ |
| Generated documentation covers build/start/restart/check | ✅ |
| Files committed to dedicated branch | ✅ |
| PR created or updated automatically | ✅ |
| Dashboard shows progress, logs, failures | ✅ |
| Existing deployer workflows remain functional | ✅ |
| Tests: prompt generation | ✅ |
| Tests: AI execution orchestration | ❌ |
| Tests: file generation | ❌ |
| Tests: Git branch workflow | ✅ |
| Tests: PR creation/update | ✅ |

---

## Required Fixes

1. Add unit tests for `run_analysis.py`:
   - `_extract_files()` — at minimum: valid multi-file response, missing required file raises error, malformed delimiter handling
   - `main()` orchestration — with mocked `_invoke_llm`, `_scan_project`, `commit_and_push`

2. Add path validation in `run_analysis.py` before writing extracted files to prevent path traversal.

IMPLEMENTATION_FIX_REQUIRED
