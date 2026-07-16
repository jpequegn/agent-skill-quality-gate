"""Deterministic static checks for the shape and safety of reusable skills."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .models import (
    CategoryScore,
    LintFinding,
    LintRun,
    Severity,
    SkillCard,
    SkillLintResult,
)
from .parser import parse_skill_tree

_CATEGORY_ORDER = (
    "trigger clarity",
    "context hygiene",
    "instruction quality",
    "verification",
    "safety",
    "governance",
)
_PENALTIES = {"error": 25, "warning": 12}
_VAGUE_TRIGGER_PHRASES = (
    "when needed",
    "as appropriate",
    "any task",
    "all requests",
    "help with",
)
_STALE_PATTERNS = (
    re.compile(r"\b(todo|tbd|coming soon)\b", re.IGNORECASE),
    re.compile(r"\b(do the needful|be helpful|follow best practices)\b", re.IGNORECASE),
)
_VERIFICATION_PATTERN = re.compile(r"\b(verify|validate|test|check|assert)\b", re.IGNORECASE)
_PITFALL_PATTERN = re.compile(r"\b(pitfall|avoid|do not|warning)\b", re.IGNORECASE)
_UNSAFE_GUIDANCE_PATTERN = re.compile(
    r"\b(store|retain|save|upload|archive)\b.*\b(raw\s+)?(agent\s+)?(logs?|secrets?|credentials?)\b",
    re.IGNORECASE,
)
_OVERBROAD_PATTERN = re.compile(
    r"\b(all tasks|every request|any request|regardless of context|without exception)\b",
    re.IGNORECASE,
)
_BRANCH_PATTERN = re.compile(r"\b(if|when|otherwise)\b", re.IGNORECASE)


def _line_number(text: str, fragment: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if fragment.casefold() in line.casefold():
            return index
    return None


def _finding(
    card: SkillCard,
    *,
    rule_id: str,
    category: str,
    severity: Severity,
    message: str,
    evidence: str,
    remediation: str,
    line: int | None = None,
) -> LintFinding:
    return LintFinding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        message=message,
        evidence=evidence,
        remediation=remediation,
        source_path=card.source_path,
        line=line,
    )


def _instruction_lines(card: SkillCard) -> Iterable[tuple[int, str]]:
    return enumerate(card.instruction_text.splitlines(), start=1)


def _normalized_instruction(line: str) -> str:
    return re.sub(r"^[\s#>*\-\d.]+", "", line).strip().casefold()


def _trigger_findings(card: SkillCard) -> list[LintFinding]:
    if not card.triggers:
        return [
            _finding(
                card,
                rule_id="TRIGGER_MISSING",
                category="trigger clarity",
                severity="error",
                message="The skill has no declared trigger.",
                evidence="skill_card.trigger is absent",
                remediation=(
                    "Declare the concrete workflow condition that should select this skill."
                ),
                line=1,
            )
        ]

    findings: list[LintFinding] = []
    for trigger in card.triggers:
        trigger_text = trigger.casefold()
        vague = len(trigger.strip()) < 24 or any(
            phrase in trigger_text for phrase in _VAGUE_TRIGGER_PHRASES
        )
        if vague:
            findings.append(
                _finding(
                    card,
                    rule_id="TRIGGER_VAGUE",
                    category="trigger clarity",
                    severity="warning",
                    message="The trigger is too broad to route reliably.",
                    evidence=trigger,
                    remediation="Name the observable task, user intent, and required context.",
                    line=1,
                )
            )
    return findings


def _context_findings(card: SkillCard) -> list[LintFinding]:
    findings: list[LintFinding] = []
    if card.main_character_count > 3_500:
        findings.append(
            _finding(
                card,
                rule_id="MAIN_FILE_OVERSIZED",
                category="context hygiene",
                severity="warning",
                message="The main SKILL.md body exceeds the compact-context threshold.",
                evidence=f"{card.main_character_count} characters in the main file",
                remediation="Move branch-specific detail into linked Markdown references.",
            )
        )
    if card.context_character_count > 5_000:
        findings.append(
            _finding(
                card,
                rule_id="CONTEXT_LOAD_HIGH",
                category="context hygiene",
                severity="warning",
                message="The skill and its declared references exceed the context-load threshold.",
                evidence=f"{card.context_character_count} characters across the skill card",
                remediation=(
                    "Prune low-value instructions and load references only for relevant branches."
                ),
            )
        )
    return findings


def _instruction_quality_findings(card: SkillCard) -> list[LintFinding]:
    findings: list[LintFinding] = []
    first_occurrence: dict[str, int] = {}
    branch_line: int | None = None

    for line_number, line in _instruction_lines(card):
        normalized = _normalized_instruction(line)
        if len(normalized) >= 16:
            previous_line = first_occurrence.get(normalized)
            if previous_line is None:
                first_occurrence[normalized] = line_number
            else:
                findings.append(
                    _finding(
                        card,
                        rule_id="INSTRUCTION_DUPLICATED",
                        category="instruction quality",
                        severity="warning",
                        message="The same instruction appears more than once.",
                        evidence=f"lines {previous_line} and {line_number}: {line.strip()}",
                        remediation=(
                            "Keep one canonical instruction and link to detail only when needed."
                        ),
                        line=line_number,
                    )
                )
        if branch_line is None and _BRANCH_PATTERN.search(line):
            branch_line = line_number
        if any(pattern.search(line) for pattern in _STALE_PATTERNS):
            findings.append(
                _finding(
                    card,
                    rule_id="INSTRUCTION_STALE_OR_NOOP",
                    category="instruction quality",
                    severity="warning",
                    message="The instruction looks stale or non-actionable.",
                    evidence=line.strip(),
                    remediation=(
                        "Replace it with a concrete action, decision rule, or verification step."
                    ),
                    line=line_number,
                )
            )

    if branch_line is not None and not card.references:
        findings.append(
            _finding(
                card,
                rule_id="BRANCH_DETAIL_INLINE",
                category="instruction quality",
                severity="warning",
                message="Conditional workflow detail is not separated into a linked reference.",
                evidence=(
                    "A conditional instruction is present but no local reference was declared."
                ),
                remediation="Move branch-specific detail into a local Markdown reference.",
                line=branch_line,
            )
        )
    return findings


def _verification_findings(card: SkillCard) -> list[LintFinding]:
    has_verification = bool(_VERIFICATION_PATTERN.search(card.instruction_text))
    if has_verification:
        return []
    return [
        _finding(
            card,
            rule_id="VERIFICATION_MISSING",
            category="verification",
            severity="warning",
            message="The skill does not state how to verify its result.",
            evidence="No verify, validate, test, check, or assert instruction found",
            remediation="Add a concrete command, artifact, or assertion that proves completion.",
        )
    ]


def _safety_findings(card: SkillCard) -> list[LintFinding]:
    findings: list[LintFinding] = []
    has_pitfall = bool(_PITFALL_PATTERN.search(card.instruction_text)) or bool(card.exclusions)
    if not has_pitfall:
        findings.append(
            _finding(
                card,
                rule_id="PITFALLS_MISSING",
                category="safety",
                severity="warning",
                message="The skill has no documented exclusion, pitfall, or safety boundary.",
                evidence="No exclusions or cautionary language found",
                remediation=(
                    "Document the cases where the skill must not be used and its safety limits."
                ),
            )
        )

    for line_number, line in _instruction_lines(card):
        if _UNSAFE_GUIDANCE_PATTERN.search(line) and "do not" not in line.casefold():
            findings.append(
                _finding(
                    card,
                    rule_id="RAW_LOG_GUIDANCE_UNSAFE",
                    category="safety",
                    severity="error",
                    message="The skill instructs retention of raw logs, secrets, or credentials.",
                    evidence=line.strip(),
                    remediation=(
                        "Retain only curated evidence fields and never collect secrets or raw logs."
                    ),
                    line=line_number,
                )
            )
    return findings


def _governance_findings(card: SkillCard) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for line_number, line in _instruction_lines(card):
        if _OVERBROAD_PATTERN.search(line):
            findings.append(
                _finding(
                    card,
                    rule_id="RULE_OVERBROAD",
                    category="governance",
                    severity="warning",
                    message="The instruction applies beyond a bounded workflow context.",
                    evidence=line.strip(),
                    remediation=(
                        "Limit the rule to named conditions and declare explicit exclusions."
                    ),
                    line=line_number,
                )
            )
    return findings


def _category_scores(findings: Iterable[LintFinding]) -> tuple[CategoryScore, ...]:
    penalties: dict[str, int] = defaultdict(int)
    for finding in findings:
        penalties[finding.category] += _PENALTIES[finding.severity]
    return tuple(
        CategoryScore(category=category, score=max(0, 100 - penalties[category]))
        for category in _CATEGORY_ORDER
    )


def analyze_skill(card: SkillCard) -> SkillLintResult:
    """Apply stable rules to one card and return deterministic findings and scores."""

    findings = [
        *_trigger_findings(card),
        *_context_findings(card),
        *_instruction_quality_findings(card),
        *_verification_findings(card),
        *_safety_findings(card),
        *_governance_findings(card),
    ]
    findings.sort(key=lambda finding: (finding.rule_id, finding.line or 0, finding.evidence))
    category_scores = _category_scores(findings)
    score = sum(category.score for category in category_scores) // len(category_scores)
    return SkillLintResult(
        skill_name=card.name,
        source_path=card.source_path,
        score=score,
        category_scores=category_scores,
        findings=tuple(findings),
    )


def analyze_tree(root: Path) -> LintRun:
    """Parse and analyze every permitted skill below a local root directory."""

    parsed = parse_skill_tree(root)
    results = tuple(
        sorted((analyze_skill(card) for card in parsed.cards), key=lambda result: result.skill_name)
    )
    return LintRun(results=results, diagnostics=parsed.diagnostics)
