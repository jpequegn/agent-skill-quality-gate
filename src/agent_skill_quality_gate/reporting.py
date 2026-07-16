"""Privacy-safe renderers for deterministic lint results."""

from __future__ import annotations

import re
from collections import defaultdict

from .models import LintRun, PruneProposal, SelectionEvaluation, SkillLintResult

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|password|secret|token)\s*([:=])\s*[^\s,;]+"
)


def _redact(text: str) -> str:
    return _SENSITIVE_VALUE_PATTERN.sub(r"\1\2[REDACTED]", text)


def _location(path: str, line: int | None) -> str:
    return f"{path}:{line}" if line is not None else path


def render_lint_summary(run: LintRun) -> str:
    """Render a compact CLI summary without exposing instruction bodies."""

    lines = [f"Inspected {len(run.results)} skill(s)"]
    for result in run.results:
        error_count = sum(finding.severity == "error" for finding in result.findings)
        warning_count = sum(finding.severity == "warning" for finding in result.findings)
        lines.append(
            f"{result.skill_name}: score {result.score} | errors {error_count} "
            f"| warnings {warning_count}"
        )
    if run.diagnostics:
        lines.append(f"Completeness diagnostics: {len(run.diagnostics)}")
    return "\n".join(lines)


def _dashboard_rows(run: LintRun) -> list[str]:
    scores_by_category: dict[str, list[int]] = defaultdict(list)
    for result in run.results:
        for category in result.category_scores:
            scores_by_category[category.category].append(category.score)

    rows = ["| Category | Average score |", "| --- | ---: |"]
    for category in sorted(scores_by_category):
        scores = scores_by_category[category]
        rows.append(f"| {category} | {sum(scores) // len(scores)} |")
    return rows


def _skill_row(result: SkillLintResult) -> str:
    errors = sum(finding.severity == "error" for finding in result.findings)
    warnings = sum(finding.severity == "warning" for finding in result.findings)
    return f"| {result.skill_name} | {result.score} | {errors} | {warnings} |"


def render_markdown_report(run: LintRun) -> str:
    """Render an auditable report with redacted finding evidence."""

    average_score = sum(result.score for result in run.results) // max(1, len(run.results))
    lines = [
        "# Agent Skill Quality Report",
        "",
        "## Summary",
        "",
        f"- Skills inspected: {len(run.results)}",
        f"- Average score: {average_score}",
        f"- Completeness diagnostics: {len(run.diagnostics)}",
        "",
        "## Category Dashboard",
        "",
        *_dashboard_rows(run),
        "",
        "## Skill Scores",
        "",
        "| Skill | Score | Errors | Warnings |",
        "| --- | ---: | ---: | ---: |",
        *(_skill_row(result) for result in run.results),
    ]

    if run.diagnostics:
        lines.extend(["", "## Completeness Diagnostics", ""])
        for diagnostic in run.diagnostics:
            lines.append(
                f"- {diagnostic.code} at {diagnostic.source_path}: {_redact(diagnostic.message)}"
            )

    lines.extend(["", "## Findings", ""])
    for result in run.results:
        lines.extend([f"### {result.skill_name}", ""])
        if not result.findings:
            lines.extend(["No static findings.", ""])
            continue
        lines.extend(
            [
                "| Severity | Rule | Location | Evidence | Review-safe remediation |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for finding in result.findings:
            location = _location(str(finding.source_path), finding.line)
            lines.append(
                "| "
                f"{finding.severity} | {finding.rule_id} | {location} | "
                f"{_redact(finding.evidence)} "
                f"| {finding.remediation} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_prune_review_packet(proposals: tuple[PruneProposal, ...]) -> str:
    """Render a dry-run packet; callers never receive a file-writing operation."""

    lines = [
        "# Skill Prune Review Packet",
        "",
        "Read-only dry run. No inspected skill files were changed.",
        "",
        "| Action | Skill | Source | Finding | Rationale | Proposed change |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for proposal in proposals:
        location = _location(str(proposal.source_path), proposal.line)
        lines.append(
            "| "
            f"{proposal.action} | {proposal.skill_name} | {location} | "
            f"{proposal.finding_rule_id} | {_redact(proposal.rationale)} | "
            f"{_redact(proposal.proposed_change)} |"
        )
    if not proposals:
        lines.extend(["| none | - | - | - | No prune candidates were found. | - |"])
    return "\n".join(lines) + "\n"


def _percent(value: float) -> str:
    return f"{value * 100:.0f}%"


def render_selection_evaluation(evaluation: SelectionEvaluation) -> str:
    """Render synthetic evaluation evidence without exposing request content or traces."""

    lines = [
        "# Skill Trigger Evaluation",
        "",
        (
            "Deterministic local fixture evaluation; no LLM judge, external API, or raw trace "
            "retention."
        ),
        "",
        "## Split Metrics",
        "",
        "| Split | Precision | Recall | False-positive rate | TP | FP | FN | TN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metrics in evaluation.metrics:
        lines.append(
            f"| {metrics.split} | {_percent(metrics.precision)} | {_percent(metrics.recall)} | "
            f"{_percent(metrics.false_positive_rate)} | {metrics.true_positives} | "
            f"{metrics.false_positives} | {metrics.false_negatives} | {metrics.true_negatives} |"
        )

    lines.extend(
        [
            "",
            "## Selection Outcomes",
            "",
            "| Split | Case | Expected | Selected | Result |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for outcome in evaluation.outcomes:
        expected = outcome.skill_name if outcome.should_trigger else "must not trigger"
        selected = outcome.selected_skill or "none"
        result = "pass" if outcome.is_correct else "flagged"
        lines.append(
            f"| {outcome.split} | {outcome.case_id} | {expected} | {selected} | {result} |"
        )

    lines.extend(["", "## Contract Checks", ""])
    if not evaluation.contract_violations:
        lines.append("All required artifacts, approved tools, and forbidden instructions passed.")
    else:
        lines.extend(
            [
                "| Case | Skill | Violation | Details |",
                "| --- | --- | --- | --- |",
            ]
        )
        for violation in evaluation.contract_violations:
            lines.append(
                "| "
                f"{violation.case_id} | {violation.skill_name} | {violation.code} | "
                f"{_redact(violation.message)} |"
            )
    return "\n".join(lines) + "\n"
