from __future__ import annotations

from pathlib import Path

from agent_skill_quality_gate.pruning import propose_pruning

from agent_skill_quality_gate.analyzer import analyze_tree
from agent_skill_quality_gate.reporting import render_prune_review_packet

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "corpus"


def test_prune_proposals_cover_each_review_action_and_link_to_findings() -> None:
    proposals = propose_pruning(analyze_tree(FIXTURE_ROOT))

    assert {proposal.action for proposal in proposals} == {
        "consolidate",
        "delete",
        "move-to-reference",
    }
    assert {proposal.finding_rule_id for proposal in proposals} == {
        "BRANCH_DETAIL_INLINE",
        "INSTRUCTION_DUPLICATED",
        "INSTRUCTION_STALE_OR_NOOP",
    }
    assert all(proposal.source_path.name == "SKILL.md" for proposal in proposals)


def test_prune_review_packet_is_explicitly_read_only() -> None:
    packet = render_prune_review_packet(propose_pruning(analyze_tree(FIXTURE_ROOT)))

    assert "Read-only dry run" in packet
    assert "INSTRUCTION_DUPLICATED" in packet
    assert "move-to-reference" in packet
