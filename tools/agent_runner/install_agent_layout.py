"""Install or regenerate the AI Dev Factory agent layout in an existing project.

Scans the repository, calls an LLM to generate docs/, ensures the standard
ai/prompts/runs/tickets layout exists, commits to a branch, and opens a PR.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Optional progress sink: the supervisor passes a callback that appends to the
# per-job log file so the dashboard can tail progress live. When absent we fall
# back to the module logger so standalone/CLI behaviour is unchanged.
LogCb = Callable[[str], None]


def _emit(log_cb: "LogCb | None", message: str) -> None:
    if log_cb is not None:
        log_cb(message)
    else:
        logger.info("%s", message)

INSTALL_BRANCH = "ai-dev-factory/install-agent-layout"
UPDATE_BRANCH = "ai-dev-factory/update-agent-docs"
INSTALL_COMMIT_MSG = "chore: add AI Dev Factory agent layout and docs"
UPDATE_COMMIT_MSG = "chore: regenerate AI Dev Factory agent docs"
INSTALL_PR_TITLE = "Add AI Dev Factory agent layout"
UPDATE_PR_TITLE = "Update AI Dev Factory agent docs"

REQUIRED_BASE_DOCS = [
    "docs/project-overview.md",
    "docs/architecture.md",
    "docs/local-development.md",
    "docs/validation.md",
    "docs/configuration.md",
    "docs/dependencies.md",
    "docs/testing-strategy.md",
    "docs/deployment.md",
    "docs/agent-guidelines.md",
    "docs/known-risks-and-todos.md",
]

_FILE_BLOCK_RE = re.compile(
    r"--- BEGIN FILE: (.+?) ---\n(.*?)--- END FILE ---",
    re.DOTALL,
)


def _factory_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _get_remote_url(project_path: Path) -> str | None:
    result = _run_git(["remote", "get-url", "origin"], project_path)
    return result.stdout.strip() if result.returncode == 0 else None


def _get_default_branch(project_path: Path) -> str:
    for cmd in [
        ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        ["symbolic-ref", "--short", "HEAD"],
    ]:
        result = _run_git(cmd, project_path)
        if result.returncode == 0:
            return result.stdout.strip().removeprefix("origin/")
    return "main"


def _layout_exists(project_path: Path) -> bool:
    return (project_path / "ai").is_dir()


def _invoke_llm(exec_cmd: str, prompt: str, cwd: Path, log_cb: "LogCb | None" = None) -> str:
    import shlex
    parts = shlex.split(exec_cmd) + ["--print"]
    env = {**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"}

    if log_cb is None:
        result = subprocess.run(
            parts,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=360,
            env=env,
        )
        if result.returncode != 0:
            snippet = (result.stderr or "")[:500]
            raise RuntimeError(f"LLM execution failed (exit {result.returncode}): {snippet}")
        return result.stdout

    # Streaming mode: tee the LLM stdout to the job log as it arrives so the
    # dashboard sees live progress. A writer thread feeds stdin to avoid a
    # pipe deadlock on large prompts.
    proc = subprocess.Popen(
        parts,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd),
        env=env,
    )

    def _feed() -> None:
        try:
            if proc.stdin is not None:
                proc.stdin.write(prompt)
                proc.stdin.close()
        except Exception:  # noqa: BLE001 - best-effort stdin feed
            pass

    writer = threading.Thread(target=_feed, daemon=True)
    writer.start()

    out_lines: list[str] = []
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                out_lines.append(line)
                log_cb(line.rstrip("\n"))
        proc.wait(timeout=360)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("LLM execution timed out")

    stderr = proc.stderr.read() if proc.stderr is not None else ""
    if proc.returncode != 0:
        snippet = (stderr or "")[:500]
        raise RuntimeError(f"LLM execution failed (exit {proc.returncode}): {snippet}")
    return "".join(out_lines)


def _parse_file_blocks(llm_output: str) -> dict[str, str]:
    return {
        m.group(1).strip(): m.group(2)
        for m in _FILE_BLOCK_RE.finditer(llm_output)
    }


def _validate_doc_path(rel_path: str, project_path: Path) -> str | None:
    """Return an error string if the path is unsafe, else None."""
    if rel_path.startswith("/"):
        return f"absolute path rejected: {rel_path}"
    resolved = (project_path / rel_path).resolve()
    docs_root = (project_path / "docs").resolve()
    try:
        resolved.relative_to(docs_root)
    except ValueError:
        return f"path escapes docs/ directory: {rel_path}"
    if not rel_path.endswith(".md"):
        return f"non-markdown path rejected: {rel_path}"
    return None


def _ensure_layout_dirs(project_path: Path, factory: Path, project_id: str, repo_url: str) -> None:
    """Ensure ai/, prompts/, runs/, tickets/ exist (idempotent). Does not touch docs/."""
    for subdir in ("roles", "skills", "templates"):
        src = factory / "ai" / subdir
        dst = project_path / "ai" / subdir
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and not (dst / f.name).exists():
                    shutil.copy2(f, dst / f.name)

    generic_src = factory / "prompts" / "generic"
    generic_dst = project_path / "prompts" / "generic"
    if generic_src.is_dir():
        generic_dst.mkdir(parents=True, exist_ok=True)
        for f in generic_src.iterdir():
            if f.is_file() and not (generic_dst / f.name).exists():
                shutil.copy2(f, generic_dst / f.name)

    for folder in ("runs", "tickets"):
        d = project_path / folder
        d.mkdir(exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    docs_ai = project_path / "docs" / "ai"
    docs_ai.mkdir(parents=True, exist_ok=True)
    ctx = docs_ai / "global-context.md"
    if not ctx.exists():
        project_name = project_id.replace("-", " ").title()
        ctx.write_text(
            f"# Global Context — {project_name}\n\n"
            f"- project_id: {project_id}\n"
            f"- repo: {repo_url}\n",
            encoding="utf-8",
        )


def _extract_analysis_summary(generated: dict[str, str]) -> str | None:
    for key in ("docs/analysis-summary.md", "analysis-summary.md"):
        if key in generated:
            return generated[key].strip()
    return None


def _read_analysis_summary_from_disk(project_path: Path) -> str | None:
    """Fallback when the LLM wrote analysis-summary.md directly (no FILE block)."""
    path = project_path / "docs" / "analysis-summary.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _staged_doc_paths(project_path: Path) -> list[str]:
    """Top-level ``docs/<name>.md`` files created/modified in the index.

    Counts the *actual* documentation changes from git rather than the parsed
    FILE blocks, so the result is correct whether the LLM returned FILE blocks
    on stdout or (as agentic CLIs do) wrote the files to disk itself. Excludes
    deletions, the internal ``analysis-summary.md`` helper, and the ``docs/ai/``
    scaffolding so the count reflects user-facing docs only.
    """
    res = _run_git(["diff", "--cached", "--name-status"], project_path)
    if res.returncode != 0:
        return []
    paths: list[str] = []
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0].strip(), parts[-1].strip()
        if status.startswith("D"):
            continue
        if not path.startswith("docs/") or not path.endswith(".md"):
            continue
        rel = path[len("docs/"):]
        if "/" in rel or rel == "analysis-summary.md":
            continue
        paths.append(path)
    return sorted(paths)


def _build_pr_body(
    project_name: str,
    is_update: bool,
    docs_paths: list[str],
    analysis_summary: str | None,
    warnings: list[str],
) -> str:
    action = "Updated" if is_update else "Added"
    docs_list = "\n".join(f"- `{p}`" for p in sorted(docs_paths))
    warnings_section = (
        "\n".join(f"- {w}" for w in warnings) if warnings else "None"
    )
    summary_section = analysis_summary or "_Not available_"
    return f"""## {action} AI Dev Factory agent layout

### AI analysis summary

{summary_section}

### Generated docs ({len(docs_paths)} files)

{docs_list}

### Folders added/updated

| Folder | Purpose |
|--------|---------|
| `ai/` | Agent roles and skills |
| `docs/` | AI-generated project documentation |
| `prompts/` | Generic and ticket-specific prompts |
| `runs/` | Per-ticket runtime artifacts |
| `tickets/` | Ticket definitions |

### Warnings

{warnings_section}

### TODOs requiring human review

- [ ] Review generated `docs/` for accuracy
- [ ] Fill in any "TODO: verify" sections
- [ ] Update `docs/known-risks-and-todos.md` with project-specific risks
"""


def install_agent_layout(
    project_path: Path,
    project_id: str,
    stack: str = "unknown",
    exec_cmd: str = "claude --dangerously-skip-permissions",
    log_cb: "LogCb | None" = None,
) -> dict:
    """Install or regenerate the agent layout and AI-generated docs in a project.

    ``log_cb`` is an optional callback receiving human-readable progress lines
    (used by the supervisor to stream into a per-job log). When omitted, progress
    is sent to the module logger and behaviour/return value are unchanged.

    Returns dict with: branch, pr_url, pr_number, docs_paths, docs_count,
    analysis_summary, warnings, error.
    """
    _runner_dir = Path(__file__).resolve().parent
    if str(_runner_dir) not in sys.path:
        sys.path.insert(0, str(_runner_dir))

    from docs_prompt_builder import scan_and_build_prompt  # noqa: PLC0415

    is_update = _layout_exists(project_path)
    branch = UPDATE_BRANCH if is_update else INSTALL_BRANCH
    commit_msg = UPDATE_COMMIT_MSG if is_update else INSTALL_COMMIT_MSG
    pr_title = UPDATE_PR_TITLE if is_update else INSTALL_PR_TITLE
    project_name = project_id.replace("-", " ").title()
    warnings: list[str] = []

    _emit(log_cb, f"{'Updating' if is_update else 'Installing'} agent layout for '{project_id}' (stack={stack})")

    repo_url = _get_remote_url(project_path) or ""
    default_branch = _get_default_branch(project_path)

    # Create or checkout the working branch
    _emit(log_cb, f"Preparing working branch '{branch}'")
    result = _run_git(["checkout", "-b", branch], project_path)
    if result.returncode != 0:
        if "already exists" in result.stderr:
            co = _run_git(["checkout", branch], project_path)
            if co.returncode != 0:
                return {
                    "branch": None, "pr_url": None, "pr_number": None,
                    "docs_paths": [], "docs_count": 0,
                    "analysis_summary": None, "warnings": [],
                    "error": f"git checkout failed: {co.stderr.strip()}",
                }
        else:
            return {
                "branch": None, "pr_url": None, "pr_number": None,
                "docs_paths": [], "docs_count": 0,
                "analysis_summary": None, "warnings": [],
                "error": f"git checkout -b failed: {result.stderr.strip()}",
            }

    factory = _factory_root()

    # Ensure layout dirs (idempotent — does not overwrite existing files)
    _emit(log_cb, "Ensuring standard ai/ layout directories")
    try:
        _ensure_layout_dirs(project_path, factory, project_id, repo_url)
    except Exception as exc:
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": [], "docs_count": 0,
            "analysis_summary": None, "warnings": [],
            "error": f"layout dir creation failed: {exc}",
        }

    # Run AI analysis and generate docs
    try:
        _emit(log_cb, "Scanning repository and building analysis prompt")
        prompt = scan_and_build_prompt(project_path)
        _emit(log_cb, "Invoking LLM to generate documentation (this can take a few minutes)…")
        llm_output = _invoke_llm(exec_cmd, prompt, project_path, log_cb=log_cb)
        _emit(log_cb, "LLM analysis complete")
    except Exception as exc:
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": [], "docs_count": 0,
            "analysis_summary": None, "warnings": [],
            "error": f"LLM invocation failed: {exc}",
        }

    generated = _parse_file_blocks(llm_output)
    analysis_summary = _extract_analysis_summary(generated)

    # Write any docs the LLM returned as FILE blocks. NOTE: when the exec_cmd is
    # an agentic CLI (e.g. `claude --dangerously-skip-permissions`), the model
    # writes the files to disk itself and prints a prose summary instead of FILE
    # blocks — so `generated` may be empty even though docs were produced. We
    # reconcile the real set of changes from git below rather than trusting the
    # parsed blocks alone.
    docs_path = project_path / "docs"
    docs_path.mkdir(exist_ok=True)

    for rel_path, content in generated.items():
        # Skip the analysis-summary helper doc — it's used internally
        if "analysis-summary" in rel_path:
            continue

        err = _validate_doc_path(rel_path, project_path)
        if err:
            warnings.append(f"skipped: {err}")
            continue

        if not content.strip():
            warnings.append(f"skipped empty file: {rel_path}")
            continue

        target = (project_path / rel_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        _emit(log_cb, f"wrote {rel_path}")

    # Stage everything (parser-written docs, agent-written docs, and the ai/
    # layout scaffolding), then derive the real documentation changes from git
    # so the count is accurate regardless of how the LLM emitted its output.
    _run_git(["add", "-A"], project_path)
    written_paths = _staged_doc_paths(project_path)
    for rel_path in written_paths:
        _emit(log_cb, f"doc changed: {rel_path}")

    # Fall back to the on-disk analysis summary when the LLM wrote it directly.
    if analysis_summary is None:
        analysis_summary = _read_analysis_summary_from_disk(project_path)

    # Check required base docs exist on disk (independent of how they were
    # written) so an empty/new project is still fully initialised.
    missing = [d for d in REQUIRED_BASE_DOCS if not (project_path / d).exists()]
    if missing:
        warnings.append(f"missing required base docs: {', '.join(missing)}")

    # Commit
    _emit(log_cb, f"Committing {len(written_paths)} doc change(s)")
    result = _run_git(["commit", "-m", commit_msg], project_path)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "nothing to commit" in combined:
            logger.info("install_agent_layout: nothing to commit")
            return {
                "branch": branch, "pr_url": None, "pr_number": None,
                "docs_paths": written_paths, "docs_count": len(written_paths),
                "analysis_summary": analysis_summary, "warnings": warnings,
                "error": None,
            }
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": written_paths, "docs_count": len(written_paths),
            "analysis_summary": analysis_summary, "warnings": warnings,
            "error": f"git commit failed: {result.stderr.strip()}",
        }

    if not repo_url:
        logger.info("install_agent_layout: no remote — skipping push/PR")
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": written_paths, "docs_count": len(written_paths),
            "analysis_summary": analysis_summary, "warnings": warnings,
            "error": None,
        }

    # Push
    _emit(log_cb, f"Pushing branch '{branch}' to origin")
    result = _run_git(["push", "-u", "origin", branch], project_path)
    if result.returncode != 0:
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": written_paths, "docs_count": len(written_paths),
            "analysis_summary": analysis_summary, "warnings": warnings,
            "error": f"git push failed: {result.stderr.strip()}",
        }

    # Create PR (check for existing open PR on this branch first)
    _emit(log_cb, "Opening pull request")
    pr_url: str | None = None
    pr_number: int | None = None

    existing = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--json", "url,number", "--state", "open"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0:
        import json
        try:
            prs = json.loads(existing.stdout)
            if prs:
                pr_url = prs[0]["url"]
                pr_number = prs[0].get("number")
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    if pr_url is None:
        pr_body = _build_pr_body(project_name, is_update, written_paths, analysis_summary, warnings)
        gh_result = subprocess.run(
            ["gh", "pr", "create",
             "--title", pr_title,
             "--body", pr_body,
             "--base", default_branch,
             "--head", branch],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if gh_result.returncode != 0:
            return {
                "branch": branch, "pr_url": None, "pr_number": None,
                "docs_paths": written_paths, "docs_count": len(written_paths),
                "analysis_summary": analysis_summary, "warnings": warnings,
                "error": f"gh pr create failed: {gh_result.stderr.strip()}",
            }
        pr_url = gh_result.stdout.strip()
        m = re.search(r"/pull/(\d+)", pr_url)
        if m:
            pr_number = int(m.group(1))

    _emit(log_cb, f"Done — PR: {pr_url or '(none)'}")
    return {
        "branch": branch,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "docs_paths": written_paths,
        "docs_count": len(written_paths),
        "analysis_summary": analysis_summary,
        "warnings": warnings,
        "error": None,
    }
