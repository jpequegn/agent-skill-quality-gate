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


class SkillParseError(ValueError):
    """Raised when a SKILL.md cannot be safely interpreted as a skill card."""
