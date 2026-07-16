from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from agent_skill_quality_gate.models import SkillParseError
from agent_skill_quality_gate.parser import parse_skill_tree

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "skills"


def test_parses_a_complete_skill_card_and_local_markdown_reference() -> None:
    result = parse_skill_tree(FIXTURE_ROOT / "valid")

    assert result.diagnostics == ()
    assert len(result.cards) == 1
    card = result.cards[0]
    assert card.name == "incident-triage"
    assert card.triggers == ("A production incident needs an initial response plan.",)
    assert card.review_by == date(2026, 12, 1)
    assert card.references[0].path == Path("incident-triage/references/decision-checklist.md")
    assert card.reference_character_count > 0
    assert card.context_character_count > card.main_character_count


def test_reports_missing_optional_skill_card_metadata_without_inventing_values() -> None:
    result = parse_skill_tree(FIXTURE_ROOT / "missing-manifest")

    assert len(result.cards) == 1
    assert result.cards[0].triggers == ()
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "missing-trigger",
        "missing-exclusions",
        "missing-required-inputs",
        "missing-approved-tools",
        "missing-expected-evidence",
        "missing-references",
    }


def test_rejects_malformed_front_matter() -> None:
    with pytest.raises(SkillParseError, match="malformed YAML"):
        parse_skill_tree(FIXTURE_ROOT / "malformed")


def test_rejects_references_that_escape_the_inspected_root() -> None:
    with pytest.raises(SkillParseError, match="escapes the inspected root"):
        parse_skill_tree(FIXTURE_ROOT / "unsafe-reference")


def test_does_not_read_raw_logs_or_non_markdown_references() -> None:
    result = parse_skill_tree(FIXTURE_ROOT / "non-markdown-reference")

    assert result.cards[0].references == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "missing-trigger",
        "missing-exclusions",
        "missing-required-inputs",
        "missing-approved-tools",
        "missing-expected-evidence",
        "missing-references",
        "unsupported-reference",
    ]
