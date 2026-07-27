"""Tests for the doc-integrity gate.

Two jobs: prove the checker actually catches a rotted reference (so a green run
means something), and prove the repo's own docs pass right now (so the gate is
enforceable, not aspirational).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_docs", _ROOT / "tools" / "check_docs.py")
assert _spec and _spec.loader
check_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_docs)


def test_slug_matches_github():
    assert check_docs.slug("Naming") == "naming"
    assert check_docs.slug("Provenance and confidence") == "provenance-and-confidence"
    # backticks, em dash, and a colon all vanish; spaces become hyphens
    assert check_docs.slug("Break 1 — the `queue`: split") == "break-1--the-queue-split"


def test_anchors_disambiguate_repeats():
    text = "# Check\n\n## Check\n\n### Notes\n"
    assert check_docs.anchors_of(text) == {"check", "check-1", "notes"}


def test_repo_docs_are_clean():
    # The shipped docs must have no dangling internal links or anchors.
    assert check_docs.check(_ROOT) == []


def test_missing_file_is_caught(tmp_path):
    (tmp_path / "a.md").write_text("see [b](b.md)\n", encoding="utf-8")
    errors = check_docs.check(tmp_path)
    assert any("link target 'b.md' does not exist" in e for e in errors)


def test_broken_anchor_is_caught(tmp_path):
    (tmp_path / "a.md").write_text("jump to [x](b.md#nope)\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Real Heading\n", encoding="utf-8")
    errors = check_docs.check(tmp_path)
    assert any("anchor '#nope' not found" in e for e in errors)


def test_same_file_anchor_resolves(tmp_path):
    (tmp_path / "a.md").write_text("# Top\n\nback to [top](#top)\n", encoding="utf-8")
    assert check_docs.check(tmp_path) == []


def test_external_and_code_spans_are_ignored(tmp_path):
    (tmp_path / "a.md").write_text(
        "[site](https://example.com/missing) and `repo/path.py:12` and "
        "[m](mailto:x@y.z)\n",
        encoding="utf-8",
    )
    assert check_docs.check(tmp_path) == []
