"""Tests for ticket dependency extraction and worktree ticket.md resolution."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))

from ticket_readiness_evaluator import (  # noqa: E402
    _extract_dependencies,
    collect_dependency_ticket_ids,
    read_ticket_markdown,
)


def test_extract_dependencies_inline_marker():
    content = "This ticket depends on T010 before we can ship."
    assert _extract_dependencies(content) == ["T010"]


def test_extract_dependencies_markdown_section_list():
    content = """# T011

## Depends on
- T010 - foundation ticket
- T005 - shared config

## Scope
Implement the feature.
"""
    assert _extract_dependencies(content) == ["T010", "T005"]


def test_extract_dependencies_combines_inline_and_section():
    content = """# T012

Blocked by T001.

## Depends on
- T010 - prerequisite
"""
    assert _extract_dependencies(content) == ["T001", "T010"]


def test_extract_dependencies_deduplicates():
    content = """Depends on T010.

## Depends on
- T010 - same ticket again
"""
    assert _extract_dependencies(content) == ["T010"]


def test_extract_dependencies_ignores_arrow_example_lines():
    content = """# T218

Examples:

→ T010 depends on T001
→ T011 depends on T010
→ T016 depends on T015

This ticket depends on T042 before shipping.
"""
    assert _extract_dependencies(content) == ["T042"]


def test_extract_dependencies_ignores_fenced_code_blocks():
    content = """Depends on T999 in prose.

```
→ T010 depends on T001
Blocked by T001
```
"""
    assert _extract_dependencies(content) == ["T999"]


def test_extract_dependencies_t218_spec_excerpt_has_no_false_deps():
    content = """Examples:

T001 - Define architecture
T010 - Bootstrap project

→ T010 depends on T001

T011 - Backend foundation
→ T011 depends on T010
→ T012 depends on T010

→ T016 depends on T015
"""
    assert _extract_dependencies(content) == []


def test_collect_dependency_ticket_ids_merges_intelligence_hints():
    content = "Create the frontend foundation."
    intelligence = {"dependency_hints": '["T001"]'}
    assert collect_dependency_ticket_ids(content, intelligence) == ["T001"]


def test_collect_dependency_ticket_ids_deduplicates_body_and_hints():
    content = "## Depends on\n- T001\n"
    intelligence = {"dependency_hints": ["T001", "T002"]}
    assert collect_dependency_ticket_ids(content, intelligence) == ["T001", "T002"]


def test_collect_dependency_ticket_ids_ignores_hints_from_fenced_examples_only():
    content = """# T219

Example graph:

```text
T001
└── T010
    └── T011
```

Dispatcher examples:

```text
T015 blocked by T011
T020 conflicts with T021
```
"""
    intelligence = {
        "dependency_hints": ["T001", "T010", "T011", "T015", "T020", "T021"],
    }
    assert collect_dependency_ticket_ids(content, intelligence) == []


def test_collect_dependency_ticket_ids_keeps_hints_not_in_ticket_body():
    content = "Create the frontend foundation."
    intelligence = {"dependency_hints": '["T001"]'}
    assert collect_dependency_ticket_ids(content, intelligence) == ["T001"]


def test_read_ticket_markdown_prefers_worktree(tmp_path: Path):
    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / "runs" / "T011").mkdir(parents=True)
    (project_root / "runs" / "T011" / "ticket.md").write_text(
        "# T011\n\nfrom project root\n",
        encoding="utf-8",
    )

    worktrees_dir = tmp_path / "worktrees"
    wt_ticket = worktrees_dir / "T011" / "runs" / "T011" / "ticket.md"
    wt_ticket.parent.mkdir(parents=True)
    wt_ticket.write_text(
        "# T011\n\n## Depends on\n- T010 - from worktree\n",
        encoding="utf-8",
    )

    content = read_ticket_markdown(project_root, "T011", worktrees_dir=worktrees_dir)
    assert "from worktree" in content
    assert _extract_dependencies(content) == ["T010"]
