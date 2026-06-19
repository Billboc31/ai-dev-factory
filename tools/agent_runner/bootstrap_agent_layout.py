"""Bootstrap the standard AI Dev Factory agent workspace into a managed project."""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

SETUP_BRANCH = "ai-dev-factory/bootstrap-agent-layout"
COMMIT_MESSAGE = "chore: add AI Dev Factory agent workspace"
PR_TITLE = "Add AI Dev Factory agent workspace"

_VALIDATION_COMMANDS: dict[str, list[str]] = {
    "python": ["pytest"],
    "node": ["npm test"],
    "go": ["go test ./..."],
    "rust": ["cargo test"],
}


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


def _detect_validation_commands(stack: str) -> list[str]:
    return _VALIDATION_COMMANDS.get(stack, [])


def _generate_global_context(project_id: str, project_name: str, repo_url: str) -> str:
    return f"""# Global Context — {project_name}

## Project

- project_id: {project_id}
- repo: {repo_url}

## AI Dev Factory

This project uses AI Dev Factory for AI-assisted development.

Agent context folders:
- `ai/` — roles and skills
- `docs/` — project documentation
- `prompts/` — ticket-specific and generic prompts
- `runs/` — per-ticket runtime artifacts
- `tickets/` — ticket definitions
"""


def _build_pr_body(
    project_name: str,
    validation_commands: list[str],
) -> str:
    commands_section = (
        "\n".join(f"- `{c}`" for c in validation_commands)
        if validation_commands
        else "- None detected"
    )
    return f"""## Add AI Dev Factory agent workspace

This PR installs the standard AI Dev Factory agent layout into **{project_name}**.

### Folders added

| Folder | Purpose |
|--------|---------|
| `ai/` | Agent roles and skills |
| `docs/` | Project documentation and global context |
| `prompts/` | Generic and ticket-specific prompts |
| `runs/` | Per-ticket runtime artifacts (created at run time) |
| `tickets/` | Ticket definitions |

### How agents use these folders

- **run-ticket**: uses `tickets/` and `runs/` for project context
- **planner**: reads `prompts/` and `docs/`
- **coder / reviewer**: reads `prompts/`, `docs/`, and project conventions from `ai/`
- **tester**: uses `docs/`, `prompts/`, and detected validation commands

### Detected validation commands

{commands_section}

### TODOs requiring human review

- [ ] Review `docs/ai/global-context.md` and fill in project-specific details
"""


def _generate_workspace(
    project_path: Path,
    factory: Path,
    project_id: str,
    project_name: str,
    repo_url: str,
) -> None:
    for subdir in ("roles", "skills", "templates"):
        src = factory / "ai" / subdir
        dst = project_path / "ai" / subdir
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file():
                    shutil.copy2(f, dst / f.name)

    docs_ai = project_path / "docs" / "ai"
    docs_ai.mkdir(parents=True, exist_ok=True)
    (docs_ai / "global-context.md").write_text(
        _generate_global_context(project_id, project_name, repo_url),
        encoding="utf-8",
    )

    generic_src = factory / "prompts" / "generic"
    generic_dst = project_path / "prompts" / "generic"
    if generic_src.is_dir():
        generic_dst.mkdir(parents=True, exist_ok=True)
        for f in generic_src.iterdir():
            if f.is_file():
                shutil.copy2(f, generic_dst / f.name)

    for folder in ("runs", "tickets"):
        d = project_path / folder
        d.mkdir(exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")


def bootstrap_agent_layout(
    project_path: Path,
    project_id: str,
    stack: str = "unknown",
) -> dict:
    """Create the standard AI Dev Factory agent workspace in a target project.

    Returns dict with keys: branch, pr_url, pr_number, error.
    """
    if _layout_exists(project_path):
        logger.info("bootstrap_agent_layout: layout already exists in %s — skipping", project_path)
        return {"branch": None, "pr_url": None, "pr_number": None, "error": None}

    repo_url = _get_remote_url(project_path) or ""
    default_branch = _get_default_branch(project_path)
    project_name = project_id.replace("-", " ").title()
    validation_commands = _detect_validation_commands(stack)

    result = _run_git(["checkout", "-b", SETUP_BRANCH], project_path)
    if result.returncode != 0:
        if "already exists" in result.stderr:
            _run_git(["checkout", SETUP_BRANCH], project_path)
        else:
            error = f"git checkout failed: {result.stderr.strip()}"
            logger.warning("bootstrap_agent_layout: %s", error)
            return {"branch": None, "pr_url": None, "pr_number": None, "error": error}

    factory = _factory_root()

    try:
        _generate_workspace(project_path, factory, project_id, project_name, repo_url)
    except Exception as exc:
        error = f"workspace generation failed: {exc}"
        logger.warning("bootstrap_agent_layout: %s", error)
        return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": error}

    _run_git(["add", "-A"], project_path)
    result = _run_git(["commit", "-m", COMMIT_MESSAGE], project_path)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "nothing to commit" in combined:
            logger.info("bootstrap_agent_layout: nothing to commit — layout already in tree")
            return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": None}
        error = f"git commit failed: {result.stderr.strip()}"
        logger.warning("bootstrap_agent_layout: %s", error)
        return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": error}

    if not repo_url:
        logger.info("bootstrap_agent_layout: no remote — skipping push/PR")
        return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": None}

    result = _run_git(["push", "-u", "origin", SETUP_BRANCH], project_path)
    if result.returncode != 0:
        error = f"git push failed: {result.stderr.strip()}"
        logger.warning("bootstrap_agent_layout: %s", error)
        return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": error}

    pr_body = _build_pr_body(project_name, validation_commands)
    gh_result = subprocess.run(
        [
            "gh", "pr", "create",
            "--title", PR_TITLE,
            "--body", pr_body,
            "--base", default_branch,
            "--head", SETUP_BRANCH,
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
    )

    if gh_result.returncode != 0:
        error = f"gh pr create failed: {gh_result.stderr.strip()}"
        logger.warning("bootstrap_agent_layout: %s", error)
        return {"branch": SETUP_BRANCH, "pr_url": None, "pr_number": None, "error": error}

    pr_url = gh_result.stdout.strip()
    pr_number: int | None = None
    m = re.search(r"/pull/(\d+)", pr_url)
    if m:
        pr_number = int(m.group(1))

    return {"branch": SETUP_BRANCH, "pr_url": pr_url, "pr_number": pr_number, "error": None}
