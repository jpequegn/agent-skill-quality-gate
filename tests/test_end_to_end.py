from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parent.parent
CORPUS_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "corpus"
EVALUATION_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "evaluation"
ABLATION_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "ablation"


def _run(*arguments: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_skill_quality_gate",
            *(str(argument) for argument in arguments),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_documented_fixture_workflow_runs_end_to_end() -> None:
    lint = _run("lint", CORPUS_ROOT)
    report = _run("report", CORPUS_ROOT)
    prune = _run("suggest-prune", CORPUS_ROOT)
    selection = _run("skill-eval", EVALUATION_ROOT / "skills", EVALUATION_ROOT / "cases.yaml")
    ablation = _run(
        "skill-eval",
        "--variants",
        ABLATION_ROOT / "variants.yaml",
        "--case-fixture",
        ABLATION_ROOT / "cases.yaml",
        "--strict",
    )

    assert lint.returncode == report.returncode == prune.returncode == 0
    assert selection.returncode == ablation.returncode == 0
    assert "Inspected 4 skill(s)" in lint.stdout
    assert report.stdout.startswith("# Agent Skill Quality Report")
    assert "Read-only dry run" in prune.stdout
    assert "## Split Metrics" in selection.stdout
    assert "Recommendation: promote" in ablation.stdout
