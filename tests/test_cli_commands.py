from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "corpus"


def test_lint_command_inspects_a_complete_synthetic_corpus() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent_skill_quality_gate", "lint", str(FIXTURE_ROOT)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Inspected 4 skill(s)" in result.stdout
    assert "Completeness diagnostics: 6" in result.stdout


def test_report_command_emits_markdown_without_secret_values() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent_skill_quality_gate", "report", str(FIXTURE_ROOT)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("# Agent Skill Quality Report")
    assert "synthetic-only-value" not in result.stdout
