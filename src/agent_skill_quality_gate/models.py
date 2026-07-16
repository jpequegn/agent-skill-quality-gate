"""Typed, privacy-safe representations of inspected skill files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ParseDiagnostic:
    code: str
    message: str
    source_path: Path


@dataclass(frozen=True)
class ReferenceDocument:
    """A permitted local Markdown reference, represented without its contents."""

    path: Path
    character_count: int


@dataclass(frozen=True)
class SkillCard:
    """Normalized metadata and instructions for a single reusable procedure."""

    name: str
    description: str
    source_path: Path
    instruction_text: str
    triggers: tuple[str, ...]
    exclusions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    approved_tools: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    references: tuple[ReferenceDocument, ...]
    version: str | None
    review_by: date | None

    @property
    def main_character_count(self) -> int:
        return len(self.instruction_text)

    @property
    def reference_character_count(self) -> int:
        return sum(reference.character_count for reference in self.references)

    @property
    def context_character_count(self) -> int:
        return self.main_character_count + self.reference_character_count


@dataclass(frozen=True)
class ParseResult:
    cards: tuple[SkillCard, ...]
    diagnostics: tuple[ParseDiagnostic, ...]


Severity = Literal["error", "warning"]
PruneAction = Literal["delete", "consolidate", "move-to-reference"]


@dataclass(frozen=True)
class LintFinding:
    rule_id: str
    category: str
    severity: Severity
    message: str
    evidence: str
    remediation: str
    source_path: Path
    line: int | None


@dataclass(frozen=True)
class CategoryScore:
    category: str
    score: int


@dataclass(frozen=True)
class SkillLintResult:
    skill_name: str
    source_path: Path
    score: int
    category_scores: tuple[CategoryScore, ...]
    findings: tuple[LintFinding, ...]


@dataclass(frozen=True)
class LintRun:
    results: tuple[SkillLintResult, ...]
    diagnostics: tuple[ParseDiagnostic, ...]


@dataclass(frozen=True)
class PruneProposal:
    """A review-only change suggestion derived from a static lint finding."""

    action: PruneAction
    finding_rule_id: str
    skill_name: str
    source_path: Path
    line: int | None
    rationale: str
    proposed_change: str


@dataclass(frozen=True)
class WorkflowCase:
    """A synthetic request with explicit selection and contract expectations."""

    case_id: str
    split: Literal["development", "held-out"]
    request: str
    skill_name: str
    should_trigger: bool
    required_artifacts: tuple[str, ...]
    requested_tools: tuple[str, ...]
    forbidden_instructions: tuple[str, ...]


@dataclass(frozen=True)
class ContractViolation:
    case_id: str
    skill_name: str
    code: str
    message: str


@dataclass(frozen=True)
class SelectionOutcome:
    case_id: str
    split: Literal["development", "held-out"]
    skill_name: str
    should_trigger: bool
    selected_skill: str | None

    @property
    def is_correct(self) -> bool:
        if self.should_trigger:
            return self.selected_skill == self.skill_name
        return self.selected_skill is None


@dataclass(frozen=True)
class SelectionMetrics:
    split: Literal["development", "held-out"]
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def false_positive_rate(self) -> float:
        denominator = self.false_positives + self.true_negatives
        return self.false_positives / denominator if denominator else 0.0


@dataclass(frozen=True)
class SelectionEvaluation:
    outcomes: tuple[SelectionOutcome, ...]
    metrics: tuple[SelectionMetrics, ...]
    contract_violations: tuple[ContractViolation, ...]


VariantRole = Literal["baseline", "bloated", "distilled"]
Recommendation = Literal["promote", "revise", "retire"]


@dataclass(frozen=True)
class VariantSpec:
    """A local-only skill directory participating in a deterministic ablation."""

    name: str
    role: VariantRole
    root: Path


@dataclass(frozen=True)
class VariantMetrics:
    name: str
    role: VariantRole
    development_success: float
    held_out_success: float
    retries: int
    context_cost: int
    latency_proxy: int
    negative_triggers: int
    safety_violations: int
    evidence_violations: int


@dataclass(frozen=True)
class PromotionDecision:
    candidate: str
    recommendation: Recommendation
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AblationEvaluation:
    variants: tuple[VariantMetrics, ...]
    decision: PromotionDecision


class SkillParseError(ValueError):
    """Raised when a SKILL.md cannot be safely interpreted as a skill card."""


class SkillEvaluationError(ValueError):
    """Raised when deterministic synthetic evaluation fixtures are invalid."""
