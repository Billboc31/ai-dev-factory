"""Tests for install_agent_layout and docs_prompt_builder."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

from install_agent_layout import (
    INSTALL_BRANCH,
    UPDATE_BRANCH,
    REQUIRED_BASE_DOCS,
    _layout_exists,
    _validate_doc_path,
    _parse_file_blocks,
    inspect_layout,
    install_agent_layout,
)
from docs_prompt_builder import scan_and_build_prompt, _build_file_tree


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test project\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)
    return path


def _fake_llm_output(paths: list[str], extra: dict[str, str] | None = None) -> str:
    """Build a fake LLM output with FILE blocks for the given paths."""
    blocks = []
    for p in paths:
        content = f"# {p}\n\nGenerated content for {p}.\n"
        blocks.append(f"--- BEGIN FILE: {p} ---\n{content}--- END FILE ---")
    if extra:
        for p, content in extra.items():
            blocks.append(f"--- BEGIN FILE: {p} ---\n{content}--- END FILE ---")
    return "\n\n".join(blocks)


# ── unit tests — helpers ──────────────────────────────────────────────────────


def test_layout_exists_when_ai_dir_present(tmp_path):
    (tmp_path / "ai").mkdir()
    assert _layout_exists(tmp_path) is True


def test_layout_exists_false_when_no_ai_dir(tmp_path):
    assert _layout_exists(tmp_path) is False


def test_validate_doc_path_accepts_valid(tmp_path):
    assert _validate_doc_path("docs/project-overview.md", tmp_path) is None


def test_validate_doc_path_rejects_absolute():
    from pathlib import Path
    err = _validate_doc_path("/etc/passwd", Path("/tmp"))
    assert err is not None
    assert "absolute" in err


def test_validate_doc_path_rejects_traversal(tmp_path):
    err = _validate_doc_path("docs/../../../etc/passwd", tmp_path)
    assert err is not None


def test_validate_doc_path_rejects_non_markdown(tmp_path):
    err = _validate_doc_path("docs/evil.sh", tmp_path)
    assert err is not None
    assert "non-markdown" in err


def test_parse_file_blocks_extracts_all():
    raw = (
        "--- BEGIN FILE: docs/a.md ---\nContent A\n--- END FILE ---\n\n"
        "--- BEGIN FILE: docs/b.md ---\nContent B\n--- END FILE ---"
    )
    parsed = _parse_file_blocks(raw)
    assert "docs/a.md" in parsed
    assert "docs/b.md" in parsed
    assert parsed["docs/a.md"] == "Content A\n"


def test_parse_file_blocks_empty_output():
    assert _parse_file_blocks("no blocks here") == {}


def test_build_file_tree_returns_string(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    tree = _build_file_tree(tmp_path)
    assert "src" in tree
    assert "main.py" in tree


# ── docs_prompt_builder tests ────────────────────────────────────────────────


def test_scan_and_build_prompt_contains_required_doc_names(tmp_path):
    (tmp_path / "README.md").write_text("# hello", encoding="utf-8")
    prompt = scan_and_build_prompt(tmp_path)
    for doc in REQUIRED_BASE_DOCS:
        assert doc in prompt


def test_scan_and_build_prompt_includes_readme_content(tmp_path):
    (tmp_path / "README.md").write_text("# my awesome project\n", encoding="utf-8")
    prompt = scan_and_build_prompt(tmp_path)
    assert "my awesome project" in prompt


def test_scan_and_build_prompt_includes_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "my-app"}', encoding="utf-8")
    prompt = scan_and_build_prompt(tmp_path)
    assert "my-app" in prompt


def test_scan_and_build_prompt_shows_directory_listing(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("", encoding="utf-8")
    prompt = scan_and_build_prompt(tmp_path)
    assert "src" in prompt


# ── integration tests — real git repo ────────────────────────────────────────


def _make_base_docs_output() -> str:
    return _fake_llm_output(
        REQUIRED_BASE_DOCS,
        extra={
            "docs/analysis-summary.md": "This is a test project using Python.\n",
        },
    )


def test_install_creates_docs_folder(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is None
    assert (repo / "docs").is_dir()


def test_install_creates_all_required_base_docs(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is None
    for doc in REQUIRED_BASE_DOCS:
        assert (repo / doc).exists(), f"missing: {doc}"


def test_install_creates_layout_dirs(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is None
    for folder in ("ai", "prompts", "runs", "tickets"):
        assert (repo / folder).is_dir(), f"missing layout dir: {folder}"


def test_install_uses_install_branch_for_new_project(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["branch"] == INSTALL_BRANCH


def test_install_uses_update_branch_when_layout_exists(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    (repo / "ai").mkdir()
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add ai dir"], cwd=repo, capture_output=True)

    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["branch"] == UPDATE_BRANCH


def test_install_returns_docs_count_and_paths(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["docs_count"] == len(REQUIRED_BASE_DOCS)
    assert set(result["docs_paths"]) == set(REQUIRED_BASE_DOCS)


def test_install_captures_analysis_summary(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["analysis_summary"] == "This is a test project using Python."


def test_install_generates_conditional_docs_when_present(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    # Include conditional docs: docker.md and api.md
    llm_output = _fake_llm_output(
        REQUIRED_BASE_DOCS + ["docs/docker.md", "docs/api.md"],
        extra={"docs/analysis-summary.md": "Has Docker and an API.\n"},
    )

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is None
    assert "docs/docker.md" in result["docs_paths"]
    assert "docs/api.md" in result["docs_paths"]
    assert (repo / "docs" / "docker.md").exists()
    assert (repo / "docs" / "api.md").exists()


def test_install_rejects_path_traversal(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    # LLM output includes a traversal attempt
    bad_block = (
        "--- BEGIN FILE: docs/../evil.md ---\nevil content\n--- END FILE ---\n\n"
    )
    llm_output = _make_base_docs_output() + "\n\n" + bad_block

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert not (repo / "evil.md").exists()
    traversal_warnings = [w for w in result["warnings"] if "escapes" in w]
    assert traversal_warnings


def test_install_rejects_absolute_paths(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    bad_block = "--- BEGIN FILE: /etc/hosts ---\nevil\n--- END FILE ---\n\n"
    llm_output = _make_base_docs_output() + "\n\n" + bad_block

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    absolute_warnings = [w for w in result["warnings"] if "absolute" in w]
    assert absolute_warnings


def test_install_warns_when_base_docs_missing(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    # Only generate half the required docs
    partial_docs = REQUIRED_BASE_DOCS[:5]
    llm_output = _fake_llm_output(partial_docs)

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    missing_warnings = [w for w in result["warnings"] if "missing required base docs" in w]
    assert missing_warnings


def test_install_is_idempotent_no_remote(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            r1 = install_agent_layout(repo, "test-project")

    # Second call: layout now exists, uses UPDATE_BRANCH
    llm_output2 = _make_base_docs_output()
    with patch("install_agent_layout._invoke_llm", return_value=llm_output2):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            r2 = install_agent_layout(repo, "test-project")

    assert r1["error"] is None
    assert r2["branch"] == UPDATE_BRANCH


def test_install_no_remote_returns_no_pr_url(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["pr_url"] is None
    assert result["pr_number"] is None
    assert result["error"] is None


def test_install_llm_failure_returns_error(tmp_path):
    repo = _init_git_repo(tmp_path / "target")

    with patch("install_agent_layout._invoke_llm", side_effect=RuntimeError("claude not found")):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is not None
    assert "LLM invocation failed" in result["error"]


def test_install_commits_on_setup_branch(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["branch"] == INSTALL_BRANCH
    log = subprocess.run(
        ["git", "log", "--oneline", INSTALL_BRANCH],
        cwd=repo, capture_output=True, text=True,
    )
    assert "AI Dev Factory" in log.stdout


def test_install_log_cb_receives_progress_without_changing_result(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()
    messages: list[str] = []

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(
                repo, "test-project", log_cb=messages.append,
            )

    # Result shape/behaviour is unchanged by the presence of log_cb.
    assert result["error"] is None
    assert result["branch"] == INSTALL_BRANCH
    # Progress was streamed to the callback.
    assert messages, "log_cb should have received progress lines"
    joined = "\n".join(messages)
    assert "Scanning repository" in joined
    assert any("wrote" in m for m in messages)


def test_inspect_layout_reports_absent(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    status = inspect_layout(repo)
    assert status["layout_exists"] is False
    assert status["docs_present"] == []
    assert status["base_docs_present"] == 0
    assert all(v is False for v in status["memory_files"].values())


def test_inspect_layout_reports_present_after_install(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            install_agent_layout(repo, "test-project")

    status = inspect_layout(repo)
    assert status["layout_exists"] is True
    assert status["base_docs_present"] == status["base_docs_total"] == len(REQUIRED_BASE_DOCS)
    assert status["memory_files"]["docs/ai/global-context.md"] is True
    assert all(d.startswith("docs/") for d in status["docs_present"])


def test_install_seeds_memory_triad(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            install_agent_layout(repo, "test-project")

    assert (repo / "docs" / "ai" / "global-context.md").exists()
    assert (repo / "docs" / "ai" / "project-life.md").exists()
    assert (repo / "docs" / "ai" / "decisions-log.md").exists()


def test_install_writes_global_context_from_llm_block(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    llm_output = _make_base_docs_output() + (
        "\n\n--- BEGIN FILE: docs/ai/global-context.md ---\n"
        "# Global Context\n\nRich evidence-based content.\n--- END FILE ---\n"
    )

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            install_agent_layout(repo, "test-project")

    assert "Rich evidence-based content." in (repo / "docs" / "ai" / "global-context.md").read_text()


def test_update_preserves_existing_global_context(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    # First install (creates ai/ → subsequent runs are "update").
    with patch("install_agent_layout._invoke_llm", return_value=_make_base_docs_output()):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            install_agent_layout(repo, "test-project")

    # Simulate the memory-updater enriching the project memory over time.
    ctx = repo / "docs" / "ai" / "global-context.md"
    ctx.write_text("# Global Context\n\n## Decisions\n- important accumulated memory\n", encoding="utf-8")

    # Re-run agent layout: the LLM tries to overwrite global-context.md.
    llm2 = _make_base_docs_output() + (
        "\n\n--- BEGIN FILE: docs/ai/global-context.md ---\nOVERWRITTEN\n--- END FILE ---\n"
    )
    with patch("install_agent_layout._invoke_llm", return_value=llm2):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    content = ctx.read_text()
    assert "important accumulated memory" in content
    assert "OVERWRITTEN" not in content
    assert any("preserved" in w for w in result["warnings"])


def test_install_counts_docs_written_directly_by_agentic_llm(tmp_path):
    """Agentic CLIs (e.g. `claude --dangerously-skip-permissions`) write files to
    disk themselves and print a prose summary instead of FILE blocks. The count
    must still reflect reality (derived from git), not the 0 parsed blocks."""
    repo = _init_git_repo(tmp_path / "target")

    def _fake_agentic_llm(exec_cmd, prompt, cwd, log_cb=None):
        docs = Path(cwd) / "docs"
        docs.mkdir(exist_ok=True)
        for rel in REQUIRED_BASE_DOCS:
            target = Path(cwd) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {rel}\n\ncontent\n", encoding="utf-8")
        (docs / "analysis-summary.md").write_text("Empty project, scaffolded.\n", encoding="utf-8")
        return "All documentation files have been written to docs/."  # prose, no FILE blocks

    with patch("install_agent_layout._invoke_llm", side_effect=_fake_agentic_llm):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            result = install_agent_layout(repo, "test-project")

    assert result["error"] is None
    assert result["docs_count"] == len(REQUIRED_BASE_DOCS)
    assert set(result["docs_paths"]) == set(REQUIRED_BASE_DOCS)
    # analysis summary recovered from disk even without a FILE block
    assert result["analysis_summary"] == "Empty project, scaffolded."
    # the docs/ai scaffolding is not counted as a user-facing doc
    assert "docs/ai/global-context.md" not in result["docs_paths"]


def test_install_log_cb_and_no_cb_produce_same_result(tmp_path):
    repo_a = _init_git_repo(tmp_path / "a")
    repo_b = _init_git_repo(tmp_path / "b")
    llm_output = _make_base_docs_output()

    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            res_no_cb = install_agent_layout(repo_a, "test-project")
    with patch("install_agent_layout._invoke_llm", return_value=llm_output):
        with patch("install_agent_layout._get_remote_url", return_value=None):
            res_cb = install_agent_layout(repo_b, "test-project", log_cb=lambda _m: None)

    for key in ("branch", "docs_count", "docs_paths", "error"):
        assert res_no_cb[key] == res_cb[key]
