from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_skill_quality_gate.analyzer import analyze_skill
from agent_skill_quality_gate.models import SkillCard
from agent_skill_quality_gate.parser import parse_skill_tree

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "skills"


def _clean_card() -> SkillCard:
    return parse_skill_tree(FIXTURE_ROOT / "valid").cards[0]


def test_clean_skill_scores_perfectly_and_has_no_findings() -> None:
    result = analyze_skill(_clean_card())

    assert result.score == 100
    assert result.findings == ()
    assert all(category.score == 100 for category in result.category_scores)


def test_flags_vague_trigger_and_missing_verification() -> None:
    card = replace(
        _clean_card(),
        triggers=("Use when needed.",),
        instruction_text="Record the result.",
        exclusions=(),
    )

    result = analyze_skill(card)

    assert {finding.rule_id for finding in result.findings} == {
        "PITFALLS_MISSING",
        "TRIGGER_VAGUE",
        "VERIFICATION_MISSING",
    }
    assert result.findings == tuple(sorted(result.findings, key=lambda item: item.rule_id))


def test_flags_oversized_duplicate_and_stale_instruction_content() -> None:
    repeated = "Verify the incident evidence before continuing."
    card = replace(
        _clean_card(),
        instruction_text="\n".join([repeated, repeated, "TODO: replace this step.", "x" * 3_600]),
    )

    result = analyze_skill(card)

    assert {finding.rule_id for finding in result.findings} == {
        "INSTRUCTION_DUPLICATED",
        "INSTRUCTION_STALE_OR_NOOP",
        "MAIN_FILE_OVERSIZED",
    }


def test_flags_unsafe_raw_log_guidance_and_overbroad_rules() -> None:
    card = replace(
        _clean_card(),
        instruction_text=(
            "Store raw agent logs with every request.\n"
            "Verify the evidence after every request regardless of context."
        ),
    )

    result = analyze_skill(card)

    findings = {finding.rule_id: finding for finding in result.findings}
    assert findings["RAW_LOG_GUIDANCE_UNSAFE"].severity == "error"
    assert findings["RULE_OVERBROAD"].line == 2
    assert findings["RAW_LOG_GUIDANCE_UNSAFE"].remediation.startswith("Retain only curated")


def test_requires_reference_separation_for_conditional_detail() -> None:
    card = replace(
        _clean_card(),
        references=(),
        instruction_text="If the incident is high severity, verify the escalation record.",
    )

    result = analyze_skill(card)

    assert [finding.rule_id for finding in result.findings] == ["BRANCH_DETAIL_INLINE"]
