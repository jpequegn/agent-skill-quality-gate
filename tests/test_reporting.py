from __future__ import annotations

from pathlib import Path

from agent_skill_quality_gate.analyzer import analyze_tree
from agent_skill_quality_gate.reporting import render_lint_summary, render_markdown_report

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "corpus"
SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "corpus_report.md"


def test_markdown_report_matches_the_stable_synthetic_snapshot() -> None:
    report = render_markdown_report(analyze_tree(FIXTURE_ROOT))

    assert report == SNAPSHOT_PATH.read_text(encoding="utf-8")


def test_report_redacts_value_like_secret_patterns() -> None:
    report = render_markdown_report(analyze_tree(FIXTURE_ROOT))

    assert "synthetic-only-value" not in report
    assert "api_key=[REDACTED]" in report
    assert "RAW_LOG_GUIDANCE_UNSAFE" in report


def test_lint_summary_lists_each_synthetic_skill() -> None:
    summary = render_lint_summary(analyze_tree(FIXTURE_ROOT))

    assert "Inspected 4 skill(s)" in summary
    assert "change-review: score 100" in summary
    assert "unsafe-retention:" in summary
