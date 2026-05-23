"""Unit tests for ``tools.agent_runner.compose_utils``.

These tests pin the contract of ``normalize_compose_project_name`` so a
future refactor cannot silently bring back the production failure that
prompted this module:

    invalid project name "sandbox-ai-dev-factory-20260522T204456"
    must consist only of lowercase alphanumeric characters, hyphens,
    and underscores as well as start with a letter or number
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.agent_runner.compose_utils import normalize_compose_project_name  # noqa: E402

# Compose's own validation regex, so we can assert outputs are accepted.
_COMPOSE_VALID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ── The exact production failure ──────────────────────────────────────────────


def test_normalises_the_observed_production_failure():
    """Regression: this is the literal name Docker Compose rejected."""
    raw = "sandbox-ai-dev-factory-20260522T204456"
    out = normalize_compose_project_name(raw)
    assert out == "sandbox-ai-dev-factory-20260522t204456"
    assert _COMPOSE_VALID.match(out), out


# ── Rule-by-rule coverage ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MyApp", "myapp"),
        ("SANDBOX-Test", "sandbox-test"),
        ("Foo_Bar_Baz", "foo_bar_baz"),
    ],
)
def test_uppercase_is_lowercased(raw, expected):
    assert normalize_compose_project_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("foo bar baz", "foo-bar-baz"),
        ("foo.bar.baz", "foo-bar-baz"),
        ("foo/bar:baz", "foo-bar-baz"),
        ("café", "caf"),  # accented chars are not in [a-z0-9_-]
        ("hello!world", "hello-world"),
        ("a@b#c$d", "a-b-c-d"),
    ],
)
def test_invalid_chars_replaced_with_dash(raw, expected):
    assert normalize_compose_project_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("foo--bar", "foo-bar"),
        ("foo___bar", "foo-bar"),
        ("foo--__--bar", "foo-bar"),
        ("foo!!bar", "foo-bar"),
        ("foo  bar", "foo-bar"),
    ],
)
def test_repeated_separators_are_collapsed(raw, expected):
    assert normalize_compose_project_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("-foo", "foo"),
        ("_foo", "foo"),
        ("--__foo", "foo"),
        (".foo", "foo"),
        ("123foo", "123foo"),  # leading digit is valid
    ],
)
def test_leading_non_alphanumerics_are_stripped(raw, expected):
    assert normalize_compose_project_name(raw) == expected


@pytest.mark.parametrize("raw", ["foo-", "foo_", "foo--", "foo-_-"])
def test_trailing_separators_are_stripped(raw):
    out = normalize_compose_project_name(raw)
    assert not out.endswith("-")
    assert not out.endswith("_")


# ── Already-valid names pass through unchanged ────────────────────────────────


@pytest.mark.parametrize(
    "valid",
    [
        "sandbox-ai-dev-factory-20260522t204456",
        "myproject",
        "myproject_v2",
        "1abc",
        "a",
        "a_b-c-d_e",
        "sandbox-a1b2c3d4e5f6",  # the uuid-hex pattern from SandboxManager
    ],
)
def test_valid_names_pass_through_unchanged(valid):
    assert normalize_compose_project_name(valid) == valid
    assert _COMPOSE_VALID.match(valid), "fixture itself must be a valid name"


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_empty_input_falls_back_to_hashed_name():
    out = normalize_compose_project_name("")
    assert _COMPOSE_VALID.match(out)
    assert out.startswith("s")


def test_all_invalid_input_falls_back_to_hashed_name():
    out = normalize_compose_project_name("!!!")
    assert _COMPOSE_VALID.match(out)


def test_non_string_input_raises():
    with pytest.raises(TypeError):
        normalize_compose_project_name(None)  # type: ignore[arg-type]


# ── Output is always Compose-valid ────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        "sandbox-ai-dev-factory-20260522T204456",
        "Project Name With Spaces",
        "héllo-wörld",
        "../etc/passwd",
        "FOO  BAR  ",
        "sandbox-XYZ_123-T204456",
    ],
)
def test_output_always_satisfies_compose_regex(raw):
    out = normalize_compose_project_name(raw)
    assert _COMPOSE_VALID.match(out), (
        f"normalize({raw!r}) -> {out!r} does not match {_COMPOSE_VALID.pattern}"
    )


# ── Idempotence + uniqueness ──────────────────────────────────────────────────


def test_idempotent():
    """Normalising twice must equal normalising once. Required so callers
    can safely persist the normalised name and re-read it later."""
    for raw in [
        "Foo Bar",
        "sandbox-ai-dev-factory-20260522T204456",
        "FOO__BAR",
        "_-leading",
        "trailing-",
    ]:
        once = normalize_compose_project_name(raw)
        twice = normalize_compose_project_name(once)
        assert once == twice, f"{raw!r}: {once!r} != {twice!r}"


def test_distinct_sandbox_ids_produce_distinct_compose_names():
    """The bug we're fixing manifests on names that differ only by
    timestamp seconds. Make sure normalisation doesn't accidentally
    collapse them onto the same compose name."""
    raws = [
        "sandbox-ai-dev-factory-20260522T204456",
        "sandbox-ai-dev-factory-20260522T204457",
        "sandbox-ai-dev-factory-20260523T000000",
        "sandbox-other-project-20260522T204456",
    ]
    outs = {normalize_compose_project_name(r) for r in raws}
    assert len(outs) == len(raws), "uniqueness was lost: %s" % outs


def test_uniqueness_for_degenerate_inputs():
    """Degenerate inputs (all-invalid) fall back to a hash-based name,
    which must still be unique per distinct input."""
    a = normalize_compose_project_name("!!!")
    b = normalize_compose_project_name("???")
    assert a != b
