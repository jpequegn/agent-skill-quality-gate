from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_skill_quality_gate.evaluation import (
    check_contract,
    evaluate_selection,
    load_workflow_cases,
    select_skill,
)
from agent_skill_quality_gate.parser import parse_skill_tree
from agent_skill_quality_gate.reporting import render_selection_evaluation

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "evaluation"
SKILL_ROOT = FIXTURE_ROOT / "skills"
CASES_PATH = FIXTURE_ROOT / "cases.yaml"


def _cards_and_cases():
    return parse_skill_tree(SKILL_ROOT).cards, load_workflow_cases(CASES_PATH)


def test_synthetic_cases_have_three_positive_three_negative_and_two_splits() -> None:
    _, cases = _cards_and_cases()

    assert len(cases) == 6
    assert sum(case.should_trigger for case in cases) == 3
    assert {case.split for case in cases} == {"development", "held-out"}


def test_selection_routes_positive_cases_and_rejects_negative_cases() -> None:
    cards, cases = _cards_and_cases()

    for case in cases:
        selected = select_skill(cards, case.request)
        assert (selected == case.skill_name) is case.should_trigger


def test_evaluation_separates_held_out_metrics_and_flags_negative_triggers() -> None:
    cards, cases = _cards_and_cases()
    passing = evaluate_selection(cards, cases)
    metrics_by_split = {metrics.split: metrics for metrics in passing.metrics}

    assert metrics_by_split["development"].precision == 1.0
    assert metrics_by_split["held-out"].recall == 1.0
    assert "## Split Metrics" in render_selection_evaluation(passing)
    assert "held-out" in render_selection_evaluation(passing)

    broad_card = replace(cards[0], triggers=("Production billing",))
    flagged = evaluate_selection((broad_card,), cases)
    billing = next(
        outcome
        for outcome in flagged.outcomes
        if outcome.case_id == "held-out-production-billing"
    )
    assert billing.selected_skill == "incident-triage"
    assert not billing.is_correct


def test_contract_checks_cover_artifacts_tools_and_forbidden_instructions() -> None:
    cards, cases = _cards_and_cases()
    positive_case = next(case for case in cases if case.should_trigger)
    violating_card = replace(
        cards[0],
        expected_evidence=(),
        approved_tools=(),
        instruction_text="Store raw logs before completing the handoff.",
    )

    violations = check_contract(violating_card, positive_case)

    assert {violation.code for violation in violations} == {
        "FORBIDDEN_INSTRUCTION_PRESENT",
        "REQUIRED_ARTIFACT_MISSING",
        "UNAPPROVED_TOOL",
    }
