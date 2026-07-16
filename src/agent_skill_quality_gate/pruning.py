"""Read-only, finding-linked prune suggestions for reusable skills."""

from __future__ import annotations

from .models import LintRun, PruneProposal

_PROPOSAL_DETAILS = {
    "INSTRUCTION_DUPLICATED": (
        "consolidate",
        "This line duplicates an instruction already present in the same skill.",
        "Keep the earlier canonical instruction and remove this duplicate.",
    ),
    "INSTRUCTION_STALE_OR_NOOP": (
        "delete",
        "This instruction is stale or does not describe a verifiable action.",
        "Delete it until a concrete replacement is ready for review.",
    ),
    "BRANCH_DETAIL_INLINE": (
        "move-to-reference",
        "Conditional detail increases the main skill's context load.",
        "Move the branch-specific procedure to a declared local Markdown reference.",
    ),
    "MAIN_FILE_OVERSIZED": (
        "move-to-reference",
        "The main skill body exceeds the compact-context threshold.",
        "Move low-frequency branches or background detail to local Markdown references.",
    ),
    "CONTEXT_LOAD_HIGH": (
        "consolidate",
        "The combined skill and reference context is larger than the review threshold.",
        "Consolidate repeated guidance before expanding the skill's loaded context.",
    ),
}


def propose_pruning(run: LintRun) -> tuple[PruneProposal, ...]:
    """Derive deterministic review proposals without touching inspected files."""

    proposals: list[PruneProposal] = []
    for result in run.results:
        for finding in result.findings:
            details = _PROPOSAL_DETAILS.get(finding.rule_id)
            if details is None:
                continue
            action, rationale, proposed_change = details
            proposals.append(
                PruneProposal(
                    action=action,
                    finding_rule_id=finding.rule_id,
                    skill_name=result.skill_name,
                    source_path=finding.source_path,
                    line=finding.line,
                    rationale=rationale,
                    proposed_change=proposed_change,
                )
            )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (
                proposal.skill_name,
                proposal.source_path.as_posix(),
                proposal.line or 0,
                proposal.finding_rule_id,
            ),
        )
    )
