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
from pathlib import Path

logger = logging.getLogger(__name__)

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


def _invoke_llm(exec_cmd: str, prompt: str, cwd: Path) -> str:
    import shlex
    parts = shlex.split(exec_cmd) + ["--print"]
    result = subprocess.run(
        parts,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=360,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode != 0:
        snippet = (result.stderr or "")[:500]
        raise RuntimeError(f"LLM execution failed (exit {result.returncode}): {snippet}")
    return result.stdout


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
) -> dict:
    """Install or regenerate the agent layout and AI-generated docs in a project.

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

    repo_url = _get_remote_url(project_path) or ""
    default_branch = _get_default_branch(project_path)

    # Create or checkout the working branch
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
        prompt = scan_and_build_prompt(project_path)
        llm_output = _invoke_llm(exec_cmd, prompt, project_path)
    except Exception as exc:
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": [], "docs_count": 0,
            "analysis_summary": None, "warnings": [],
            "error": f"LLM invocation failed: {exc}",
        }

    generated = _parse_file_blocks(llm_output)
    analysis_summary = _extract_analysis_summary(generated)

    # Validate and write generated docs
    docs_path = project_path / "docs"
    docs_path.mkdir(exist_ok=True)
    written_paths: list[str] = []

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
        written_paths.append(rel_path)
        logger.info("wrote %s", rel_path)

    # Check all required base docs were generated
    missing = [d for d in REQUIRED_BASE_DOCS if d not in written_paths]
    if missing:
        warnings.append(f"missing required base docs: {', '.join(missing)}")

    # Commit
    _run_git(["add", "-A"], project_path)
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
    result = _run_git(["push", "-u", "origin", branch], project_path)
    if result.returncode != 0:
        return {
            "branch": branch, "pr_url": None, "pr_number": None,
            "docs_paths": written_paths, "docs_count": len(written_paths),
            "analysis_summary": analysis_summary, "warnings": warnings,
            "error": f"git push failed: {result.stderr.strip()}",
        }

    # Create PR (check for existing open PR on this branch first)
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
